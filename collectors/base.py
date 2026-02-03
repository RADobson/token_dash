"""Base collector class for Token Dashboard."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import structlog
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

from .config import settings

logger = structlog.get_logger()


class TokenUsagePoint:
    """Represents a single token usage data point."""
    
    def __init__(
        self,
        provider: str,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost_usd: float = 0.0,
        timestamp: Optional[datetime] = None,
        tags: Optional[Dict[str, str]] = None,
        fields: Optional[Dict[str, Any]] = None
    ):
        self.provider = provider
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens or (input_tokens + output_tokens)
        self.cost_usd = cost_usd
        self.timestamp = timestamp or datetime.now(timezone.utc)
        self.tags = tags or {}
        self.fields = fields or {}
    
    def to_influx_point(self) -> Point:
        """Convert to InfluxDB Point."""
        point = (
            Point("token_usage")
            .tag("provider", self.provider)
            .tag("model", self.model)
            .field("input_tokens", self.input_tokens)
            .field("output_tokens", self.output_tokens)
            .field("total_tokens", self.total_tokens)
            .field("cost_usd", self.cost_usd)
            .time(self.timestamp)
        )
        
        for key, value in self.tags.items():
            point = point.tag(key, value)
        
        for key, value in self.fields.items():
            point = point.field(key, value)
        
        return point


class BaseCollector(ABC):
    """Abstract base class for all collectors."""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.log = logger.bind(collector=self.name)
        self._influx_client: Optional[InfluxDBClient] = None
        self._write_api = None
    
    @property
    def influx_client(self) -> InfluxDBClient:
        """Lazy-load InfluxDB client."""
        if self._influx_client is None:
            self._influx_client = InfluxDBClient(
                url=settings.influxdb_url,
                token=settings.influxdb_token,
                org=settings.influxdb_org
            )
            self._write_api = self._influx_client.write_api(write_options=SYNCHRONOUS)
        return self._influx_client
    
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this collector is properly configured."""
        pass
    
    @abstractmethod
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data and return list of data points."""
        pass
    
    def write_points(self, points: List[TokenUsagePoint]) -> None:
        """Write data points to InfluxDB."""
        if not points:
            self.log.debug("No points to write")
            return
        
        try:
            influx_points = [p.to_influx_point() for p in points]
            self._write_api.write(
                bucket=settings.influxdb_bucket,
                org=settings.influxdb_org,
                record=influx_points
            )
            self.log.info("Wrote points to InfluxDB", count=len(points))
        except Exception as e:
            self.log.error("Failed to write points", error=str(e))
            raise
    
    async def run(self) -> None:
        """Run a single collection cycle."""
        if not self.is_configured():
            self.log.debug("Collector not configured, skipping")
            return
        
        try:
            self.log.info("Starting collection")
            points = await self.collect()
            self.write_points(points)
            self.log.info("Collection complete", points_collected=len(points))
        except Exception as e:
            self.log.error("Collection failed", error=str(e))
    
    def close(self) -> None:
        """Clean up resources."""
        if self._influx_client:
            self._influx_client.close()
