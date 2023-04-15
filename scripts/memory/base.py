"""Base class for memory providers."""
import abc
from config import AbstractSingleton
import openai


def get_ada_embedding(text, openai_key: str):
    text = text.replace("\n", " ")
    return openai.Embedding.create(
        input=[text],
        model="text-embedding-ada-002",
        api_key=openai_key,
    )["data"][0]["embedding"]


class MemoryProviderSingleton(AbstractSingleton):
    @abc.abstractmethod
    def add(self, data, openai_key):
        pass

    @abc.abstractmethod
    def get(self, data, openai_key):
        pass

    @abc.abstractmethod
    def clear(self):
        pass

    @abc.abstractmethod
    def get_relevant(self, data, openai_key, num_relevant=5):
        pass

    @abc.abstractmethod
    def get_stats(self):
        pass
