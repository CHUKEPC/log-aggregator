"""Base parser abstraction for processing raw log text.

Defines the contract for parsing raw lines into structured domain LogEntry objects.
"""

from abc import ABC, abstractmethod

from log_aggregator.models.log_entry import LogEntry


class BaseLogParser(ABC):
    """Abstract base class for all log format parsers."""

    @abstractmethod
    def can_parse(self, raw: str) -> bool:
        """Determine if this parser can handle the provided raw string.

        Args:
            raw: Unparsed log line.

        Returns:
            True if this format matches, False otherwise.
        """

    @abstractmethod
    def parse(
        self,
        raw: str,
        default_service: str = "default",
        source: str = "raw",
    ) -> LogEntry:
        """Parse raw string into structured LogEntry.

        Args:
            raw: Unparsed log line.
            default_service: Fallback service name if not present in log.
            source: Identifier for origin host or ingest channel.

        Returns:
            Structured LogEntry instance.

        Raises:
            LogParsingError: If line cannot be parsed according to format.
        """
