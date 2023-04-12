import json
import random

import openai
import commands as cmd
from main import construct_prompt, print_assistant_thoughts
import utils
from memory import get_memory
import data
import chat
from colorama import Fore, Style
from spinner import Spinner
import time
import speak
from config import Config
from json_parser import fix_and_parse_json
from ai_config import AIConfig
import traceback
import yaml
import argparse
import logging

cfg = Config()

full_message_history = []

START = "###start###"

def interact_with_ai(ai_config, memory, command_name, arguments, assistant_reply):
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
            result = f"Command {command_name} returned: {cmd.execute_command(command_name, arguments)}"

        # Check if there's a result from the command append it to the message
        # history
        if result is not None:
            output = chat.create_chat_message("system", result)
        else:
            output = chat.create_chat_message("system", "Unable to execute command")

        full_message_history.append(output)
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
        prompt, user_input, full_message_history, memory, 4000
    )

    thoughts = print_assistant_thoughts(assistant_reply)

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

    return command_name, arguments, thoughts, output, assistant_reply


# make an api using flask

from flask import Flask, request

app = Flask(__name__)


@app.after_request
def after_request(response):
    white_origin = ["http://localhost:3000"]
    # if request.headers['Origin'] in white_origin:
    if True:
        response.headers["Access-Control-Allow-Origin"] = request.headers["Origin"]
        response.headers["Access-Control-Allow-Methods"] = "PUT,GET,POST,DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response


@app.route("/api", methods=["POST"])
def simple_api():
    request_data = request.get_json()

    command_name = request_data["command"]
    arguments = request_data["arguments"]
    assistant_reply = request_data.get("assistant_reply", "")
    openai_key = request_data.get("openai_key", None)
    ai_name = request_data["ai_name"]
    ai_description = request_data["ai_description"]
    ai_goals = request_data["ai_goals"]

    # openai.api_key = openai_key

    cfg.pinecone_namespace = request_data["agent_id"]
    memory = get_memory(cfg)

    if openai_key != "" and openai_key is not None:
        cfg.openai_api_key = openai_key

    conf = AIConfig(
        ai_name=ai_name,
        ai_role=ai_description,
        ai_goals=ai_goals,
    )
    try:
        command_name, arguments, thoughts, output, assistant_reply = interact_with_ai(
            conf,
            memory,
            command_name,
            arguments,
            assistant_reply,
        )
    except Exception as e:
        print(e)

    return json.dumps(
        {
            "command": command_name,
            "arguments": arguments,
            "thoughts": thoughts,
            "output": output,
            "assistant_reply": assistant_reply,
        }
    )


app.run(port=5000)
