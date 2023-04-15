from functools import wraps
import json
import time
import traceback
import commands as cmd
from main import construct_prompt, print_assistant_thoughts
from memory import get_memory
import chat
from config import Config
from ai_config import AIConfig
import os
from google.cloud import storage
from openai.error import OpenAIError
import firebase_admin
from firebase_admin import auth as firebase_auth

bucket_name = "godmode-ai"

bucket = storage.Client().bucket(bucket_name)


def upload_file(text: str, session_id: str):
    timestamp = time.time()
    blob = bucket.blob(f"godmode-logs/{session_id}/{int(timestamp * 1000)}.txt")
    blob.upload_from_string(
        text,
        content_type="text/plain",
    )


from llm_utils import create_chat_completion

cfg = Config()

START = "###start###"


def interact_with_ai(
    ai_config,
    memory,
    command_name,
    arguments,
    assistant_reply,
    agent_id,
    message_history=[],
    openai_key=None,
):
    prompt = construct_prompt(ai_config)

    user_input = (
        arguments if command_name == "human_feedback" else "GENERATE NEXT COMMAND JSON"
    )
    output = None
    result = None

    if command_name != START:
        # Execute command
        if command_name.lower().startswith("error"):
            result = f"Command {command_name} threw the following error: " + arguments
        elif command_name == "human_feedback":
            result = f"Human feedback: {arguments}"
        else:
            result = f"Command {command_name} returned: {cmd.execute_command(command_name, arguments, memory, agent_id, openai_key)}"

        # Check if there's a result from the command append it to the message
        # history
        if result is not None:
            output = chat.create_chat_message("system", result)
        else:
            output = chat.create_chat_message("system", "Unable to execute command")

        message_history.append(output)
    else:
        user_input = "Determine which next command to use, and respond using the format specified above:"

    memory_to_add = (
        f"Assistant Reply: {assistant_reply} "
        f"\nResult: {result} "
        f"\nHuman Feedback: {user_input} "
    )

    memory.add(memory_to_add)

    # Send message to AI, get response
    assistant_reply = chat.chat_with_ai(
        prompt, user_input, message_history, memory, 4000, openai_key=openai_key
    )

    godmode_log, thoughts = print_assistant_thoughts(assistant_reply, openai_key)

    ai_info = f"You are {ai_config.ai_name}, {ai_config.ai_role}\nGOALS:\n\n"
    for i, goal in enumerate(ai_config.ai_goals):
        ai_info += f"{i+1}. {goal}\n"

    upload_file(ai_info + "\n\n" + memory_to_add + "\n\n" + godmode_log, agent_id)

    # speak = thoughts["speak"]

    # memory_to_add = f"Assistant Reply: {assistant_reply} " \
    #                 f"\nResult: {result} " \
    #                 f"\nHuman Feedback: {user_input} "

    # memory (pinecone or whatever it called or just local files)
    # full message hist (amazon smth)
    # user input (nothing)
    # prompt (nothing)

    # Get command name and arguments
    try:
        command_name, arguments = cmd.get_command(assistant_reply)
    except Exception as e:
        print(e)

    task = None
    try:
        task = create_chat_completion(
            [
                chat.create_chat_message(
                    "system",
                    "You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2021-09\nCurrent date: 2023-03-26",
                ),
                chat.create_chat_message(
                    "user",
                    'Describe this action as succinctly as possible in one short sentence:\n\n```\nCOMMAND: browse_website\nARGS: {\n  "url": "https://www.amazon.com/",\n  "question": "What are the current top products in the Smart Home Device category?"\n}\n```',
                ),
                chat.create_chat_message(
                    "assistant", "Find top Smart Home Device products on Amazon.com."
                ),
                chat.create_chat_message(
                    "user",
                    f"Describe this action as succinctly as possible in one short sentence:\n\n```\nCOMMAND: {command_name}\nARGS: {arguments}\n```",
                ),
            ],
            model="gpt-3.5-turbo",
            temperature=0.2,
            openai_key=openai_key,
        )
    except Exception as e:
        print(e)

    return (
        command_name,
        arguments,
        thoughts,
        message_history,
        assistant_reply,
        result,
        task,
    )


# make an api using flask

from flask import Flask, jsonify, request


class LogRequestDurationMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request_start_time = time.time()
        response = self.app(environ, start_response)
        request_duration = time.time() - request_start_time
        app.logger.info(f"Request duration: {request_duration}")
        return response


from flask_limiter import Limiter

app = Flask(__name__)


def get_remote_address() -> str:
    return (
        request.environ.get("HTTP_X_FORWARDED_FOR")
        or request.environ.get("REMOTE_ADDR")
        or request.remote_addr
    )


if cfg.redis_host is None:
    limiter = Limiter(app=app, key_func=get_remote_address)
else:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=f"redis://{cfg.redis_host}:{cfg.redis_port}",
    )

app.wsgi_app = LogRequestDurationMiddleware(app.wsgi_app)


@app.after_request
def after_request(response):
    ip = get_remote_address()
    # check if request has user
    if hasattr(request, "user"):
        print(f"{request.method} {request.path} {response.status_code}: IP {ip} from user {request.user}")
    else:
        print(f"{request.method} {request.path} {response.status_code}: IP {ip} with no user")
    white_origin = ["http://localhost:3000"]
    # if request.headers['Origin'] in white_origin:
    if True:
        response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
        response.headers["Access-Control-Allow-Methods"] = "PUT,GET,POST,DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response


@app.route("/health", methods=["GET"])
def health():
    return "OK"


def make_rate_limit(rate: str):
    def get_rate_limit():
        request_data = request.get_json()
        if (
            request_data.get("openai_key", None) is not None
            and len(request_data.get("openai_key", "")) > 0
        ):
            return "1000 per day;600 per hour;100 per minute"

        return rate

    return get_rate_limit


firebase_admin.initialize_app()


def verify_firebase_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            request_data = request.get_json()
            if (
                request_data.get("openai_key", None) is not None
                and len(request_data.get("openai_key", "")) > 0
            ):
                return f(*args, **kwargs)
        except Exception as e:
            print(e)

        id_token = request.headers.get("Authorization")
        if not id_token:
            return (
                jsonify(
                    {
                        "error": "Unauthorized",
                        "message": "Please login or set an API key to continue",
                    }
                ),
                401,
            )

        try:
            # Remove 'Bearer ' from the token if it's present
            if id_token.startswith("Bearer "):
                id_token = id_token[7:]
            decoded_token = firebase_auth.verify_id_token(id_token)
            request.user = decoded_token
        except ValueError as e:
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401
        except Exception as e:
            return jsonify({"error": "Unauthorized", "message": str(e)}), 401

        return f(*args, **kwargs)

    return wrapper


@app.route("/api-goal-subgoals", methods=["POST"])
@limiter.limit(make_rate_limit("100 per day;60 per hour;15 per minute"))
@verify_firebase_token
def subgoals():
    request_data = request.get_json()

    goal = request_data["goal"]
    openai_key = request_data.get("openai_key", None)

    subgoals = []
    try:
        subgoals = create_chat_completion(
            [
                chat.create_chat_message(
                    "system",
                    "You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2021-09\nCurrent date: 2023-03-26",
                ),
                chat.create_chat_message(
                    "user",
                    f'Make a list of 3 subtasks to the overall goal of: "{goal}".\n'
                    + "\n"
                    + "ONLY answer this message with a numbered list of short, standalone subtasks. write nothing else. Make sure to make the subtask descriptions as brief as possible.",
                ),
            ],
            model="gpt-3.5-turbo",
            temperature=0.2,
            max_tokens=150,
            openai_key=openai_key,
        )
    except Exception as e:
        if isinstance(e, OpenAIError):
            return e.error, 503

    return json.dumps(
        {
            "subgoals": subgoals,
        }
    )


@app.route("/api", methods=["POST"])
@limiter.limit(make_rate_limit("500 per day;200 per hour;8 per minute"))
@verify_firebase_token
def simple_api():
    try:
        request_data = request.get_json()

        command_name = request_data["command"]
        arguments = request_data["arguments"]
        assistant_reply = request_data.get("assistant_reply", "")
        openai_key = request_data.get("openai_key", None)
        ai_name = request_data["ai_name"]
        ai_description = request_data["ai_description"]
        ai_goals = request_data["ai_goals"]
        message_history = request_data.get("message_history", [])

        agent_id = request_data["agent_id"]
        memory = get_memory(cfg, agent_id)

        conf = AIConfig(
            ai_name=ai_name,
            ai_role=ai_description,
            ai_goals=ai_goals,
        )
        (
            command_name,
            arguments,
            thoughts,
            message_history,
            assistant_reply,
            result,
            task,
        ) = interact_with_ai(
            conf,
            memory,
            command_name,
            arguments,
            assistant_reply,
            agent_id,
            message_history,
            openai_key=openai_key,
        )
    except Exception as e:
        if isinstance(e, OpenAIError):
            return e.error, 503

        # dump stacktrace to console
        print("simple_api error", e)
        traceback.print_exc()
        raise e

    return json.dumps(
        {
            "command": command_name,
            "arguments": arguments,
            "thoughts": thoughts,
            "message_history": message_history,
            "assistant_reply": assistant_reply,
            "result": result,
            "task": task,
        }
    )


port = os.environ.get("PORT") or 5100
host = os.environ.get("HOST") or None

if __name__ == "__main__":
    print("Starting API on port", port, "and host", host)
    app.run(debug=True, port=port, host=host)
