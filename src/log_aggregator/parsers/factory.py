"""Parser factory and auto-detection module.

Provides automatic format detection and parser registry mapping.
"""

from log_aggregator.models.log_entry import LogEntry, LogFormat
from log_aggregator.parsers.apache_parser import ApacheLogParser
from log_aggregator.parsers.base import BaseLogParser
from log_aggregator.parsers.json_parser import JsonLogParser
from log_aggregator.parsers.nginx_parser import NginxLogParser
from log_aggregator.parsers.regex_parser import RegexLogParser
from log_aggregator.parsers.syslog_parser import SyslogParser

# Default detection order: JSON is unambiguous, followed by Syslog, Nginx/Apache, then Regex
DETECTION_PARSERS: list[BaseLogParser] = [
    JsonLogParser(),
    SyslogParser(),
    NginxLogParser(),
    ApacheLogParser(),
    RegexLogParser(),
]

PARSER_REGISTRY: dict[LogFormat, BaseLogParser] = {
    LogFormat.JSON: JsonLogParser(),
    LogFormat.SYSLOG: SyslogParser(),
    LogFormat.NGINX: NginxLogParser(),
    LogFormat.APACHE: ApacheLogParser(),
    LogFormat.REGEX: RegexLogParser(),
    LogFormat.CUSTOM: RegexLogParser(),
}


def get_parser(log_format: LogFormat) -> BaseLogParser:
    """Retrieve dedicated parser instance for a given format.

    Args:
        log_format: Specified LogFormat enum value.

    Returns:
        Configured BaseLogParser instance.
    """
    return PARSER_REGISTRY.get(log_format, RegexLogParser())


def auto_detect_parser(raw: str) -> BaseLogParser:
    """Determine the best-fitting parser by inspecting raw line content.

    Args:
        raw: Unparsed log line.

    Returns:
        First matching BaseLogParser or default RegexLogParser fallback.
    """
    for parser in DETECTION_PARSERS:
        if parser.can_parse(raw):
            return parser
    return RegexLogParser()


def parse_raw_line(
    raw: str,
    explicit_format: LogFormat | None = None,
    default_service: str = "default",
    source: str = "raw",
) -> LogEntry:
    """Parse a single raw log line using explicit or auto-detected format.

    Args:
        raw: Log line string.
        explicit_format: Optional explicit format enum.
        default_service: Service fallback.
        source: Originating source identifier.

    Returns:
        Structured LogEntry.
    """
    parser = get_parser(explicit_format) if explicit_format else auto_detect_parser(raw)
    return parser.parse(raw=raw, default_service=default_service, source=source)
