"""Elasticsearch async backend for log indexing, search, and analytics.

Implements LogStorage using the official elasticsearch-py async client.
"""

import logging
from datetime import datetime
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from log_aggregator.config import Settings
from log_aggregator.exceptions import StorageError
from log_aggregator.models.log_entry import LogEntry, LogFilter, LogStats
from log_aggregator.storage.base import LogStorage

logger = logging.getLogger(__name__)

INDEX_MAPPING: dict[str, Any] = {
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "level": {"type": "keyword"},
            "service": {"type": "keyword"},
            "source": {"type": "keyword"},
            "message": {
                "type": "text",
                "fields": {
                    "keyword": {"type": "keyword", "ignore_above": 512},
                },
            },
            "tags": {"type": "keyword"},
            "metadata": {"type": "object", "dynamic": True},
            "raw": {"type": "text"},
        }
    }
}


class ElasticsearchLogStorage(LogStorage):
    """Async Elasticsearch storage backend."""

    def __init__(self, settings: Settings, client: AsyncElasticsearch | None = None) -> None:
        """Initialize Elasticsearch client and target index configuration."""
        self.index_name = settings.ELASTICSEARCH_INDEX_PREFIX
        if client:
            self.client = client
        else:
            basic_auth: tuple[str, str] | None = None
            if settings.ELASTICSEARCH_USER and settings.ELASTICSEARCH_PASSWORD:
                basic_auth = (settings.ELASTICSEARCH_USER, settings.ELASTICSEARCH_PASSWORD)

            self.client = AsyncElasticsearch(
                hosts=[settings.ELASTICSEARCH_HOSTS],
                basic_auth=basic_auth,
                verify_certs=settings.ELASTICSEARCH_VERIFY_CERTS,
                request_timeout=15,
            )
        self._index_initialized = False

    async def ensure_index(self) -> None:
        """Ensure the target logs index exists with defined schema mappings."""
        if self._index_initialized:
            return
        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                await self.client.indices.create(
                    index=self.index_name,
                    body=INDEX_MAPPING,
                )
                logger.info("Created Elasticsearch index: %s", self.index_name)
            self._index_initialized = True
        except Exception as exc:
            logger.warning("Failed to initialize index '%s': %s", self.index_name, exc)

    async def index_log(self, entry: LogEntry) -> None:
        """Index a single log entry into Elasticsearch."""
        await self.ensure_index()
        try:
            await self.client.index(
                index=self.index_name,
                id=entry.id,
                document=entry.to_dict(),
                refresh="wait_for",
            )
        except Exception as exc:
            raise StorageError(f"Failed to index log: {exc}") from exc

    async def bulk_index_logs(self, entries: list[LogEntry]) -> int:
        """Bulk index a list of log entries."""
        if not entries:
            return 0
        await self.ensure_index()

        actions = [
            {
                "_index": self.index_name,
                "_id": entry.id,
                "_source": entry.to_dict(),
            }
            for entry in entries
        ]

        try:
            success_count, _ = await async_bulk(
                self.client,
                actions,
                refresh="wait_for",
                raise_on_error=False,
            )
            return int(success_count)
        except Exception as exc:
            raise StorageError(f"Failed to bulk index logs: {exc}") from exc

    def _build_search_query(self, filter_query: LogFilter) -> dict[str, Any]:
        """Construct Elasticsearch bool query from domain LogFilter."""
        must: list[dict[str, Any]] = []
        filter_clauses: list[dict[str, Any]] = []

        if filter_query.query:
            must.append(
                {
                    "multi_match": {
                        "query": filter_query.query,
                        "fields": ["message^2", "service", "source"],
                    }
                }
            )

        if filter_query.service:
            filter_clauses.append({"term": {"service": filter_query.service}})
        elif filter_query.services:
            filter_clauses.append({"terms": {"service": filter_query.services}})

        if filter_query.level:
            filter_clauses.append({"term": {"level": filter_query.level.value}})
        elif filter_query.levels:
            filter_clauses.append({"terms": {"level": [lvl.value for lvl in filter_query.levels]}})

        if filter_query.source:
            filter_clauses.append({"term": {"source": filter_query.source}})

        if filter_query.tags:
            filter_clauses.append({"terms": {"tags": filter_query.tags}})

        # Date range filtering
        time_range: dict[str, str] = {}
        if filter_query.start_time:
            time_range["gte"] = filter_query.start_time.isoformat()
        if filter_query.end_time:
            time_range["lte"] = filter_query.end_time.isoformat()
        if time_range:
            filter_clauses.append({"range": {"timestamp": time_range}})

        bool_query: dict[str, Any] = {}
        if must:
            bool_query["must"] = must
        if filter_clauses:
            bool_query["filter"] = filter_clauses

        return {"bool": bool_query} if bool_query else {"match_all": {}}

    async def search_logs(self, filter_query: LogFilter) -> tuple[list[LogEntry], int]:
        """Execute search query against Elasticsearch."""
        await self.ensure_index()
        query = self._build_search_query(filter_query)
        sort_order = "desc" if filter_query.sort_desc else "asc"

        try:
            response = await self.client.search(
                index=self.index_name,
                query=query,
                from_=filter_query.offset,
                size=filter_query.limit,
                sort=[{"timestamp": {"order": sort_order}}],
            )

            hits = response["hits"]["hits"]
            total_raw = response["hits"]["total"]
            total = total_raw["value"] if isinstance(total_raw, dict) else int(total_raw)

            entries = [LogEntry.from_dict(hit["_source"]) for hit in hits]
            return entries, total
        except Exception as exc:
            raise StorageError(f"Elasticsearch search failed: {exc}") from exc

    async def get_log_by_id(self, log_id: str) -> LogEntry | None:
        """Fetch log entry by document ID."""
        await self.ensure_index()
        try:
            response = await self.client.get(index=self.index_name, id=log_id)
            if response["found"]:
                return LogEntry.from_dict(response["_source"])
            return None
        except Exception:
            return None

    async def get_stats(self, filter_query: LogFilter) -> LogStats:
        """Calculate log level distributions, service counts, and time histograms."""
        await self.ensure_index()
        query = self._build_search_query(filter_query)

        aggs: dict[str, Any] = {
            "by_level": {"terms": {"field": "level", "size": 10}},
            "by_service": {"terms": {"field": "service", "size": 50}},
            "time_histogram": {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": "1h",
                    "min_doc_count": 0,
                }
            },
            "top_errors": {
                "filter": {"terms": {"level": ["ERROR", "CRITICAL"]}},
                "aggs": {"error_messages": {"terms": {"field": "message.keyword", "size": 10}}},
            },
        }

        try:
            response = await self.client.search(
                index=self.index_name,
                query=query,
                size=0,
                aggregations=aggs,
            )

            total_raw = response["hits"]["total"]
            total = total_raw["value"] if isinstance(total_raw, dict) else int(total_raw)

            aggregations = response.get("aggregations", {})

            # Parse levels
            by_level: dict[str, int] = {}
            for bucket in aggregations.get("by_level", {}).get("buckets", []):
                by_level[str(bucket["key"])] = int(bucket["doc_count"])

            # Parse services
            by_service: dict[str, int] = {}
            for bucket in aggregations.get("by_service", {}).get("buckets", []):
                by_service[str(bucket["key"])] = int(bucket["doc_count"])

            # Parse histogram
            histogram: list[dict[str, Any]] = []
            for bucket in aggregations.get("time_histogram", {}).get("buckets", []):
                ts_val = bucket.get("key_as_string") or str(bucket.get("key", ""))
                histogram.append(
                    {
                        "timestamp": ts_val,
                        "count": int(bucket["doc_count"]),
                    }
                )

            # Parse top error messages
            top_errors: list[dict[str, Any]] = []
            error_buckets = (
                aggregations.get("top_errors", {}).get("error_messages", {}).get("buckets", [])
            )
            for bucket in error_buckets:
                top_errors.append(
                    {
                        "message": str(bucket["key"]),
                        "count": int(bucket["doc_count"]),
                    }
                )

            return LogStats(
                total_logs=total,
                by_level=by_level,
                by_service=by_service,
                top_errors=top_errors,
                time_histogram=histogram,
            )
        except Exception as exc:
            raise StorageError(f"Elasticsearch aggregation failed: {exc}") from exc

    async def delete_logs_before(self, timestamp: datetime) -> int:
        """Delete log documents before the cutoff timestamp."""
        await self.ensure_index()
        query = {"range": {"timestamp": {"lt": timestamp.isoformat()}}}
        try:
            response = await self.client.delete_by_query(
                index=self.index_name,
                query=query,
                refresh=True,
            )
            return int(response.get("deleted", 0))
        except Exception as exc:
            raise StorageError(f"Elasticsearch retention cleanup failed: {exc}") from exc

    async def ping(self) -> bool:
        """Ping Elasticsearch cluster."""
        try:
            return bool(await self.client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        """Close connection to Elasticsearch."""
        await self.client.close()
