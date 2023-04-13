import time
import openai
from config import Config
cfg = Config()

openai.api_key = cfg.openai_api_key


# Overly simple abstraction until we create something better
def create_chat_completion(messages, model=None, temperature=cfg.temperature, max_tokens=None)->str:
    """Create a chat completion using the OpenAI API"""
    starttime = time.time()
    if cfg.use_azure:
        response = openai.ChatCompletion.create(
            deployment_id=cfg.get_azure_deployment_id_for_model(model),
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

    print(f"CHAT COMPLETION TOOK {time.time() - starttime} SECONDS")

    return response.choices[0].message["content"]
