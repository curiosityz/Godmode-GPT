from autogpt.llm.base import ChatModelInfo, EmbeddingModelInfo

OPEN_AI_CHAT_MODELS = {
    "gpt-3.5-turbo": ChatModelInfo(
        name="gpt-3.5-turbo",
        prompt_token_cost=0.002,
        completion_token_cost=0.002,
        max_tokens=4096,
    ),
    "gpt-4": ChatModelInfo(
        name="gpt-4",
        prompt_token_cost=0.03,
        completion_token_cost=0.06,
        max_tokens=8192,
    ),
    "gpt-4-32k": ChatModelInfo(
        name="gpt-4-32k",
        prompt_token_cost=0.06,
        completion_token_cost=0.12,
        max_tokens=32768,
    ),
}

OPEN_AI_EMBEDDING_MODELS = {
    "text-embedding-ada-002": EmbeddingModelInfo(
        name="text-embedding-ada-002",
        prompt_token_cost=0.0004,
        completion_token_cost=0.0,
        max_tokens=8191,
        embedding_dimensions=1536,
    ),
}

GOOGLE_CHAT_MODELS = {
    "chat-bison-001": ChatModelInfo(
        name="chat-bison-001",
        prompt_token_cost=0.002,
        completion_token_cost=0.002,
        max_tokens=4096,
    ),
}

GOOGLE_EMBEDDING_MODELS = {
    "text-embedding-gecko-001": EmbeddingModelInfo(
        name="text-embedding-gecko-001",
        prompt_token_cost=0.0004,
        completion_token_cost=0.0,
        max_tokens=8191,
        embedding_dimensions=1536,
    ),
}

OPEN_AI_MODELS = {
    **OPEN_AI_CHAT_MODELS,
    **OPEN_AI_EMBEDDING_MODELS,
    **GOOGLE_CHAT_MODELS,
    **GOOGLE_EMBEDDING_MODELS,
}
