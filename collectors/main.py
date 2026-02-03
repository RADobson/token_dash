"""Main collector orchestrator for Token Dashboard."""

import asyncio
import signal
import sys
from datetime import datetime, timezone
import structlog

from .config import settings
from .openai_collector import OpenAICollector
from .anthropic_collector import AnthropicCollector
from .openclaw_collector import OpenClawCollector
from .claude_code_collector import ClaudeCodeCollector
from .codex_collector import CodexCollector

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(colors=True)
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


class CollectorOrchestrator:
    """Orchestrates all data collectors."""
    
    def __init__(self):
        self.collectors = [
            OpenAICollector(),
            AnthropicCollector(),
            OpenClawCollector(),
            ClaudeCodeCollector(),
            CodexCollector(),
        ]
        self.running = True
        self.log = logger.bind(component="orchestrator")
    
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        def handle_shutdown(signum, frame):
            self.log.info("Shutdown signal received", signal=signum)
            self.running = False
        
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
    
    async def run_collection_cycle(self):
        """Run a single collection cycle for all collectors."""
        self.log.info("Starting collection cycle")
        start_time = datetime.now(timezone.utc)
        
        # Run all collectors concurrently
        tasks = [collector.run() for collector in self.collectors]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for collector, result in zip(self.collectors, results):
            if isinstance(result, Exception):
                self.log.error(
                    "Collector failed",
                    collector=collector.name,
                    error=str(result)
                )
        
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        self.log.info("Collection cycle complete", elapsed_seconds=round(elapsed, 2))
    
    async def run(self):
        """Main run loop."""
        self._setup_signal_handlers()
        
        self.log.info(
            "Token Dashboard Collector starting",
            interval_seconds=settings.collect_interval,
            collectors=[c.name for c in self.collectors]
        )
        
        # Log which collectors are configured
        for collector in self.collectors:
            configured = collector.is_configured()
            self.log.info(
                "Collector status",
                collector=collector.name,
                configured=configured
            )
        
        while self.running:
            try:
                await self.run_collection_cycle()
                
                # Wait for next collection interval
                self.log.debug(
                    "Waiting for next collection",
                    seconds=settings.collect_interval
                )
                
                # Use small sleep intervals to allow for graceful shutdown
                for _ in range(settings.collect_interval):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                    
            except Exception as e:
                self.log.error("Error in main loop", error=str(e))
                await asyncio.sleep(10)  # Brief pause before retry
        
        # Cleanup
        self.log.info("Shutting down collectors")
        for collector in self.collectors:
            try:
                collector.close()
            except:
                pass
        
        self.log.info("Shutdown complete")


def main():
    """Entry point."""
    orchestrator = CollectorOrchestrator()
    
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
