import json
import random
from typing import Tuple
import commands as cmd
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

# import argparse
import logging

cfg = Config()


def configure_logging():
    logging.basicConfig(
        filename="log.txt",
        filemode="a",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
    return logging.getLogger("AutoGPT")


def check_openai_api_key():
    """Check if the OpenAI API key is set in config.py or as an environment variable."""
    if not cfg.openai_api_key:
        print(
            Fore.RED
            + "Please set your OpenAI API key in config.py or as an environment variable."
        )
        print("You can get your key from https://beta.openai.com/account/api-keys")
        exit(1)


def print_to_console(
    a,
    title,
    title_color,
    content,
    speak_text=False,
    min_typing_speed=0.05,
    max_typing_speed=0.01,
):
    """Prints text to the console with a typing effect"""
    a += (title_color or '') + (title or '') + " " + (Style.RESET_ALL or '') + (content or '') + "\n"
    return a
    global cfg
    global logger
    if speak_text and cfg.speak_mode:
        speak.say_text(f"{title}. {content}")
    if content:
        logger.info(title + ": " + content)
        if isinstance(content, list):
            content = " ".join(content)
        print(content)
        # words = content.split()
        # for i, word in enumerate(words):
        #     print(word, end="", flush=True)
        #     if i < len(words) - 1:
        #         print(" ", end="", flush=True)
        #     typing_speed = random.uniform(min_typing_speed, max_typing_speed)
        #     time.sleep(typing_speed)
        #     # type faster after each word
        #     min_typing_speed = min_typing_speed * 0.95
        #     max_typing_speed = max_typing_speed * 0.95
    print()


def print_assistant_thoughts(assistant_reply) -> Tuple[str, str]:
    """Prints the assistant's thoughts to the console"""
    global ai_name
    global cfg
    godmode_log = ""
    try:
        # Parse and print Assistant response
        assistant_reply_json = fix_and_parse_json(assistant_reply)

        # Check if assistant_reply_json is a string and attempt to parse it into a JSON object
        if isinstance(assistant_reply_json, str):
            try:
                assistant_reply_json = json.loads(assistant_reply_json)
            except json.JSONDecodeError as e:
                godmode_log = print_to_console(
                    godmode_log, "Error: Invalid JSON\n", Fore.RED, assistant_reply
                )
                assistant_reply_json = {}

        assistant_thoughts_reasoning = None
        assistant_thoughts_plan = None
        assistant_thoughts_speak = None
        assistant_thoughts_criticism = None
        assistant_thoughts_relevant_goal = None
        assistant_thoughts = assistant_reply_json.get("thoughts", {})
        assistant_thoughts_text = assistant_thoughts.get("text")

        if assistant_thoughts:
            assistant_thoughts_reasoning = assistant_thoughts.get("reasoning")
            assistant_thoughts_plan = assistant_thoughts.get("plan")
            assistant_thoughts_criticism = assistant_thoughts.get("criticism")
            assistant_thoughts_speak = assistant_thoughts.get("speak")
            assistant_thoughts_relevant_goal = assistant_thoughts.get("relevant_goal")

        godmode_log = print_to_console(
            godmode_log, f"{ai_name.upper()} THOUGHTS:", Fore.YELLOW, assistant_thoughts_text
        )
        godmode_log = print_to_console(godmode_log, "REASONING:", Fore.YELLOW, assistant_thoughts_reasoning)

        if assistant_thoughts_plan:
            godmode_log = print_to_console(godmode_log, "PLAN:", Fore.YELLOW, "")
            # If it's a list, join it into a string
            if isinstance(assistant_thoughts_plan, list):
                assistant_thoughts_plan = "\n".join(assistant_thoughts_plan)
            elif isinstance(assistant_thoughts_plan, dict):
                assistant_thoughts_plan = str(assistant_thoughts_plan)

            # Split the input_string using the newline character and dashes
            lines = assistant_thoughts_plan.split("\n")
            for line in lines:
                line = line.lstrip("- ")
                godmode_log = print_to_console(godmode_log, "- ", Fore.GREEN, line.strip())

        godmode_log = print_to_console(godmode_log, "CRITICISM:", Fore.YELLOW, assistant_thoughts_criticism)
        # Speak the assistant's thoughts
        if cfg.speak_mode and assistant_thoughts_speak:
            speak.say_text(assistant_thoughts_speak)

        return godmode_log, {
            "thoughts": assistant_thoughts_text,
            "reasoning": assistant_thoughts_reasoning,
            "plan": assistant_thoughts_plan,
            "criticism": assistant_thoughts_criticism,
            "speak": assistant_thoughts_speak,
            "relevant_goal": assistant_thoughts_relevant_goal,
        }

    except json.decoder.JSONDecodeError:
        godmode_log = print_to_console(godmode_log, "Error: Invalid JSON\n", Fore.RED, assistant_reply)

    # All other errors, return "Error: + error message"
    except Exception as e:
        call_stack = traceback.format_exc()
        godmode_log = print_to_console(godmode_log, "Error: \n", Fore.RED, call_stack)
    
    return godmode_log, None


def load_variables(config_file="config.yaml"):
    """Load variables from yaml file if it exists, otherwise prompt the user for input"""
    try:
        with open(config_file) as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
        ai_name = config.get("ai_name")
        ai_role = config.get("ai_role")
        ai_goals = config.get("ai_goals")
    except FileNotFoundError:
        ai_name = ""
        ai_role = ""
        ai_goals = []

    # Prompt the user for input if config file is missing or empty values
    if not ai_name:
        ai_name = utils.clean_input("Name your AI: ")
        if ai_name == "":
            ai_name = "Entrepreneur-GPT"

    if not ai_role:
        ai_role = utils.clean_input(f"{ai_name} is: ")
        if ai_role == "":
            ai_role = "an AI designed to autonomously develop and run businesses with the sole goal of increasing your net worth."

    if not ai_goals:
        print("Enter up to 5 goals for your AI: ")
        print(
            "For example: \nIncrease net worth, Grow Twitter Account, Develop and manage multiple businesses autonomously'"
        )
        print("Enter nothing to load defaults, enter nothing when finished.")
        ai_goals = []
        for i in range(5):
            ai_goal = utils.clean_input(f"Goal {i+1}: ")
            if ai_goal == "":
                break
            ai_goals.append(ai_goal)
        if len(ai_goals) == 0:
            ai_goals = [
                "Increase net worth",
                "Grow Twitter Account",
                "Develop and manage multiple businesses autonomously",
            ]

    # Save variables to yaml file
    config = {"ai_name": ai_name, "ai_role": ai_role, "ai_goals": ai_goals}
    with open(config_file, "w") as file:
        documents = yaml.dump(config, file)

    prompt = data.load_prompt()
    prompt_start = """Your decisions must always be made independently without seeking user assistance. Play to your strengths as a LLM and pursue simple strategies with no legal complications."""

    # Construct full prompt
    full_prompt = f"You are {ai_name}, {ai_role}\n{prompt_start}\n\nGOALS:\n\n"
    for i, goal in enumerate(ai_goals):
        full_prompt += f"{i+1}. {goal}\n"

    full_prompt += f"\n\n{prompt}"
    return full_prompt


def construct_prompt(config: AIConfig = AIConfig.load()):
    """Construct the prompt for the AI to respond to"""
    #     if config.ai_name:
    #         print_to_console(
    #             f"Welcome back! ",
    #             Fore.GREEN,
    #             f"Would you like me to return to being {config.ai_name}?",
    #             speak_text=True)
    #         should_continue = utils.clean_input(f"""Continue with the last settings?
    # Name:  {config.ai_name}
    # Role:  {config.ai_role}
    # Goals: {config.ai_goals}
    # Continue (y/n): """)
    #         if should_continue.lower() == "n":
    #             config = AIConfig()

    # if not config.ai_name:
    #     config = prompt_user()
    #     config.save()

    # Get rid of this global:
    global ai_name
    ai_name = config.ai_name

    full_prompt = config.construct_full_prompt()
    return full_prompt

def parse_arguments():
    return
    # """Parses the arguments passed to the script"""
    # global cfg
    # cfg.set_continuous_mode(False)
    # cfg.set_speak_mode(False)

    # parser = argparse.ArgumentParser(description="Process arguments.")
    # parser.add_argument(
    #     "--continuous", action="store_true", help="Enable Continuous Mode"
    # )
    # parser.add_argument("--speak", action="store_true", help="Enable Speak Mode")
    # parser.add_argument("--debug", action="store_true", help="Enable Debug Mode")
    # parser.add_argument(
    #     "--gpt3only", action="store_true", help="Enable GPT3.5 Only Mode"
    # )
    # args = parser.parse_args()

    # if args.continuous:
    #     print_to_console("Continuous Mode: ", Fore.RED, "ENABLED")
    #     print_to_console(
    #         "WARNING: ",
    #         Fore.RED,
    #         "Continuous mode is not recommended. It is potentially dangerous and may cause your AI to run forever or carry out actions you would not usually authorise. Use at your own risk.",
    #     )
    #     cfg.set_continuous_mode(True)

    # if args.speak:
    #     print_to_console("Speak Mode: ", Fore.GREEN, "ENABLED")
    #     cfg.set_speak_mode(True)

    # if args.gpt3only:
    #     print_to_console("GPT3.5 Only Mode: ", Fore.GREEN, "ENABLED")
    #     cfg.set_smart_llm_model(cfg.fast_llm_model)


# TODO: fill in llm values here
check_openai_api_key()
cfg = Config()
logger = configure_logging()
parse_arguments()
ai_name = ""
prompt = construct_prompt()
# print(prompt)
# Initialize variables
full_message_history = []
result = None
next_action_count = 0
# Make a constant:
user_input = (
    "Determine which next command to use, and respond using the format specified above:"
)

# Initialize memory and make sure it is empty.
# this is particularly important for indexing and referencing pinecone memory
memory = get_memory(cfg)
print("Using memory of type: " + memory.__class__.__name__)
