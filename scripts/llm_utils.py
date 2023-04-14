import time
import openai
from config import Config
cfg = Config()

openai.api_key = cfg.openai_api_key

# Overly simple abstraction until we create something better
def create_chat_completion(messages, model=None, temperature=None, max_tokens=None, openai_key=None)->str:
    """Create a chat completion using the OpenAI API"""
    starttime = time.time()
    if cfg.use_azure:
        response = openai.ChatCompletion.create(
            deployment_id=cfg.openai_deployment_id,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=openai_key,
        )
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=openai_key,
        )

    print(f"CHAT COMPLETION TOOK {time.time() - starttime} SECONDS", model)

    return response.choices[0].message["content"]
