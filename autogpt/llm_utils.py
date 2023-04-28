from __future__ import annotations

import functools
import time
from typing import List, Optional

import openai
from colorama import Fore, Style
from openai.error import APIError, RateLimitError, Timeout

from autogpt.api_manager import ApiManager
from autogpt.config import Config
from autogpt.logs import logger
from autogpt.types.openai import Message


def retry_openai_api(
    num_retries: int = 10,
    backoff_base: float = 2.0,
    warn_user: bool = True,
):
    """Retry an OpenAI API call.

    Args:
        num_retries int: Number of retries. Defaults to 10.
        backoff_base float: Base for exponential backoff. Defaults to 2.
        warn_user bool: Whether to warn the user. Defaults to True.
    """
    retry_limit_msg = f"{Fore.RED}Error: " f"Reached rate limit, passing...{Fore.RESET}"
    api_key_error_msg = (
        f"Please double check that you have setup a "
        f"{Fore.CYAN + Style.BRIGHT}PAID{Style.RESET_ALL} OpenAI API Account. You can "
        f"read more here: {Fore.CYAN}https://significant-gravitas.github.io/Auto-GPT/setup/#getting-an-api-key{Fore.RESET}"
    )
    backoff_msg = (
        f"{Fore.RED}Error: API Bad gateway. Waiting {{backoff}} seconds...{Fore.RESET}"
    )

    def _wrapper(func):
        @functools.wraps(func)
        def _wrapped(*args, **kwargs):
            user_warned = not warn_user
            num_attempts = num_retries + 1  # +1 for the first attempt
            for attempt in range(1, num_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except RateLimitError:
                    if attempt == num_attempts:
                        raise

                    logger.debug(retry_limit_msg)
                    if not user_warned:
                        logger.double_check(api_key_error_msg)
                        user_warned = True

                except APIError as e:
                    if (e.http_status != 502) or (attempt == num_attempts):
                        raise

                backoff = backoff_base ** (attempt + 2)
                logger.debug(backoff_msg.format(backoff=backoff))
                time.sleep(backoff)

        return _wrapped

    return _wrapper


def call_ai_function(
    function: str, args: List[str], description: str, cfg: object, model: str | None = None
) -> str:
    """Call an AI function

    This is a magic function that can do anything with no-code. See
    https://github.com/Torantulino/AI-Functions for more info.

    Args:
        function (str): The function to call
        args (list): The arguments to pass to the function
        description (str): The description of the function
        model (str, optional): The model to use. Defaults to None.

    Returns:
        str: The response from the function
    """
    cfg = Config()
    if model is None:
        model = cfg.smart_llm_model
    # For each arg, if any are None, convert to "None":
    args = [str(arg) if arg is not None else "None" for arg in args]
    # parse args to comma separated string
    args: str = ", ".join(args)
    messages: List[Message] = [
        {
            "role": "system",
            "content": f"You are now the following python function: ```# {description}"
            f"\n{function}```\n\nOnly respond with your `return` value.",
        },
        {"role": "user", "content": sargs},
    ]

    return create_chat_completion(model=model, messages=messages, temperature=0, cfg=cfg)


# Overly simple abstraction until we create something better
# simple retry mechanism when getting a rate error or a bad gateway
def create_chat_completion(
    messages: List[Message],  # type: ignore
    cfg,
    model: Optional[str] = "gpt-3.5-turbo",
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Create a chat completion using the OpenAI API

    Args:
        messages (List[Message]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.

    Returns:
        str: The response from the chat completion
    """
    if model is None:
        model = cfg.fast_llm_model
    t0 = time.time()
    if temperature is None:
        temperature = cfg.temperature
    response = None
    num_retries = 1
    if cfg.debug_mode:
        print(
            f"{Fore.GREEN}Creating chat completion with model {model}, temperature {temperature}, max_tokens {max_tokens}{Fore.RESET}"
        )
    for plugin in cfg.plugins:
        if plugin.can_handle_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            message = plugin.handle_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if message is not None:
                return message
    # api_manager = ApiManager()
    response = None
    try:
        if cfg.use_azure:
            response = openai.ChatCompletion.create(
                deployment_id=cfg.get_azure_deployment_id_for_model(model), # type: ignore
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=cfg.openai_api_key,
            )
    except RateLimitError as e:
        print("RATE LIMIT ERROR", e)
        if cfg.debug_mode:
            print(
                Fore.RED + "Error: ",
                f"Reached rate limit, passing..." + Fore.RESET,
            )
        raise e
    except APIError as e:
        print("API ERROR", e)
        raise e
    
    if response is None:
        raise RuntimeError(f"Failed to get response from model {model}")
    
    print(f"CHAT COMPLETION TOOK {time.time() - t0} SECONDS", model)

    resp = response.choices[0].message["content"] # type: ignore
    
    for plugin in cfg.plugins:
        if not plugin.can_handle_on_response():
            continue
        resp = plugin.on_response(resp)
    return resp


def create_embedding_with_ada(text: str, cfg: Config) -> Optional[List]:
    """Create a embedding with text-ada-002 using the OpenAI SDK"""
    try:
        return openai.Embedding.create(
            input=[text], # type: ignore
            model="text-embedding-ada-002",
            api_key=cfg.openai_api_key,
        )["data"][0]["embedding"]
    except RateLimitError as e:
        print("RATE LIMIT ERROR", e)
        raise e
    except APIError as e:
        print("API ERROR", e)
        raise e

# def get_ada_embedding(text: str) -> List[float]:
#     """Get an embedding from the ada model.

#     Args:
#         text (str): The text to embed.

#     Returns:
#         List[float]: The embedding.
#     """
#     cfg = Config()
#     model = "text-embedding-ada-002"
#     text = text.replace("\n", " ")

#     if cfg.use_azure:
#         kwargs = {"engine": cfg.get_azure_deployment_id_for_model(model)}
#     else:
#         kwargs = {"model": model}

#     embedding = create_embedding(text, **kwargs)
#     api_manager = ApiManager()
#     api_manager.update_cost(
#         prompt_tokens=embedding.usage.prompt_tokens,
#         completion_tokens=0,
#         model=model,
#     )
#     return embedding["data"][0]["embedding"]


# @retry_openai_api()
# def create_embedding(
#     text: str,
#     *_,
#     **kwargs,
# ) -> openai.Embedding:
#     """Create an embedding using the OpenAI API

#     Args:
#         text (str): The text to embed.
#         kwargs: Other arguments to pass to the OpenAI API embedding creation call.

#     Returns:
#         openai.Embedding: The embedding object.
#     """
#     cfg = Config()
#     return openai.Embedding.create(
#         input=[text],
#         api_key=cfg.openai_api_key,
#         **kwargs,
#     )
