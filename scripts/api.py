import json
import random
import commands as cmd
from main import construct_prompt
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

def interact_with_ai(memory, command_name, arguments):
    prompt = construct_prompt()

    user_input = arguments if command_name == "human_feedback" else "GENERATE NEXT COMMAND JSON"
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
            output = chat.create_chat_message(
                    "system", "Unable to execute command")

        full_message_history.append(output)

    # Send message to AI, get response
    assistant_reply = chat.chat_with_ai(
        prompt,
        user_input,
        full_message_history,
        memory,
        4000)

    memory_to_add = f"Assistant Reply: {assistant_reply} " \
                    f"\nResult: {result} " \
                    f"\nHuman Feedback: {user_input} "

    memory.add(memory_to_add)

    # memory (pinecone or whatever it called or just local files)
    # full message hist (amazon smth)
    # user input (nothing)
    # prompt (nothing)

    # Get command name and arguments
    try:
        command_name, arguments = cmd.get_command(assistant_reply)
    except Exception as e:
        print(e)

    return command_name, arguments, assistant_reply, output

def simple_api():
    memory = get_memory(cfg)
    while True:
        command_name, arguments, assistant_reply, output = interact_with_ai(memory, START, "")

a,b,c,e = interact_with_ai(get_memory(cfg), "google", {
    "input": "gpt startups ideas"
})
print("command",a)
print("arguments",b)
print("assistant_reply",c)
print("output",e)

