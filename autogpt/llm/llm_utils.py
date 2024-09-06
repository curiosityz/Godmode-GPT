from __future__ import annotations

import functools
import time
from itertools import islice
from typing import List, Optional

import numpy as np
import tiktoken
from colorama import Fore, Style
from google.generativeai import chat as google_chat
from google.api_core.exceptions import GoogleAPIError, RetryError

from autogpt.config import Config
from autogpt.llm.api_manager import ApiManager
from autogpt.llm.base import Message
from autogpt.logs import logger


def retry_google_api(
    num_retries: int = 10,
    backoff_base: float = 2.0,
    warn_user: bool = True,
):
    """Retry a Google API call.

    Args:
        num_retries int: Number of retries. Defaults to 10.
        backoff_base float: Base for exponential backoff. Defaults to 2.
        warn_user bool: Whether to warn the user. Defaults to True.
    """
    retry_limit_msg = f"{Fore.RED}Error: " f"Reached rate limit, passing...{Fore.RESET}"
    api_key_error_msg = (
        f"Please double check that you have setup a "
        f"{Fore.CYAN + Style.BRIGHT}PAID{Style.RESET_ALL} Google API Account. You can "
        f"read more here: {Fore.CYAN}https://cloud.google.com/docs/authentication{Fore.RESET}"
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

                except RetryError:
                    if attempt == num_attempts:
                        raise

                    logger.debug(retry_limit_msg)
                    if not user_warned:
                        logger.double_check(api_key_error_msg)
                        user_warned = True

                except GoogleAPIError as e:
                    if (e.code != 502) or (attempt == num_attempts):
                        raise

                backoff = backoff_base ** (attempt + 2)
                logger.debug(backoff_msg.format(backoff=backoff))
                time.sleep(backoff)

        return _wrapped

    return _wrapper


def call_ai_function(
    function: str, args: list, description: str, cfg: Config, model: str | None = None
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
        {"role": "user", "content": args},
    ]

    return create_chat_completion(cfg=cfg,model=model, messages=messages, temperature=0)


# Overly simple abstraction until we create something better
# simple retry mechanism when getting a rate error or a bad gateway
def create_chat_completion(
    messages: List[Message],  # type: ignore
    cfg: Config,
    model: Optional[str] = None,
    temperature: float = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Create a chat completion using the Google Generative AI SDK / Gemini API

    Args:
        messages (List[Message]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.

    Returns:
        str: The response from the chat completion
    """
    if temperature is None:
        temperature = cfg.temperature

    num_retries = 10
    warned_user = False
    logger.debug(
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
    api_manager = ApiManager()
    response = None
    try:
        response = api_manager.create_chat_completion(
            cfg=cfg,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except RetryError:
        logger.debug(
            f"{Fore.RED}Error: ", f"Reached rate limit, passing...{Fore.RESET}"
        )
        if not warned_user:
            logger.double_check(
                f"Please double check that you have setup a {Fore.CYAN + Style.BRIGHT}PAID{Style.RESETALL} Google API Account. "
                + f"You can read more here: {Fore.CYAN}https://cloud.google.com/docs/authentication{Fore.RESET}"
            )
            warned_user = True
    except GoogleAPIError as e:
        if e.code != 502:
            raise
        if attempt == num_retries - 1:
            raise
        
    if response is None:
        return "Google API error"

    resp = response.candidates[0].message["content"]
    for plugin in cfg.plugins:
        if not plugin.can_handle_on_response():
            continue
        resp = plugin.on_response(resp)
    return resp


def batched(iterable, n):
    """Batch data into tuples of length n. The last batch may be shorter."""
    # batched('ABCDEFG', 3) --> ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def chunked_tokens(text, tokenizer_name, chunk_length):
    tokenizer = tiktoken.get_encoding(tokenizer_name)
    tokens = tokenizer.encode(text)
    chunks_iterator = batched(tokens, chunk_length)
    yield from chunks_iterator


def get_ada_embedding(text: str, cfg: Config) -> List[float]:
    """Get an embedding from the ada model.

    Args:
        text (str): The text to embed.

    Returns:
        List[float]: The embedding.
    """
    model = cfg.embedding_model
    text = text.replace("\n", " ")

    embedding = create_embedding(text, cfg, model=model)
    return embedding


def create_embedding(
    text: str,
    cfg: Config,
    model: str,
) -> List[float]:
    """Create an embedding using the Google Generative AI SDK / Gemini API

    Args:
        text (str): The text to embed.
        model (str): The model to use for embedding.

    Returns:
        List[float]: The embedding.
    """
    chunk_embeddings = []
    chunk_lengths = []
    for chunk in chunked_tokens(
        text,
        tokenizer_name=cfg.embedding_tokenizer,
        chunk_length=cfg.embedding_token_limit,
    ):
        embedding = google_chat.Embedding.create(
            input=[chunk],
            model=model,
            api_key=cfg.google_api_key,
        )
        api_manager = ApiManager()
        api_manager.update_cost(
            prompt_tokens=embedding.usage.prompt_tokens,
            completion_tokens=0,
            model=model,
        )
        chunk_embeddings.append(embedding["data"][0]["embedding"])
        chunk_lengths.append(len(chunk))

    # do weighted avg
    chunk_embeddings = np.average(chunk_embeddings, axis=0, weights=chunk_lengths)
    chunk_embeddings = chunk_embeddings / np.linalg.norm(
        chunk_embeddings
    )  # normalize the length to one
    chunk_embeddings = chunk_embeddings.tolist()
    return chunk_embeddings
