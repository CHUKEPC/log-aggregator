"""Storage backends package."""

from log_aggregator.storage.base import LogStorage
from log_aggregator.storage.elasticsearch import ElasticsearchLogStorage
from log_aggregator.storage.memory import InMemoryLogStorage

__all__ = [
    "ElasticsearchLogStorage",
    "InMemoryLogStorage",
    "LogStorage",
]
