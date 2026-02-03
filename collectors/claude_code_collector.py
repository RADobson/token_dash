"""Claude Code (Claude Max) subscription usage collector.

Scrapes usage data directly from Claude Code CLI's internal JSON files:
- ~/.claude/stats-cache.json - Aggregated usage statistics
- ~/.claude/projects/*/*.jsonl - Per-session conversation logs with token usage
- ~/.claude/history.jsonl - Command history (for context)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
import hashlib

from .base import BaseCollector, TokenUsagePoint


class ClaudeCodeCollector(BaseCollector):
    """
    Collects usage data from Claude Code CLI's internal JSON files.
    
    Data sources:
    1. stats-cache.json - Pre-computed daily stats (quick overview)
    2. projects/*/*.jsonl - Detailed per-message usage (granular data)
    
    The collector tracks processed message UUIDs to avoid duplicate counting
    on subsequent runs.
    """
    
    # Claude Max pricing (approximated - subscription-based so $0 for user)
    # But we track hypothetical costs for comparison
    MODELS_PRICING = {
        "claude-opus-4-5": {"input": 15.00, "output": 75.00, "cache_read": 1.875, "cache_write": 18.75},
        "claude-sonnet-4": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
        "claude-3-opus": {"input": 15.00, "output": 75.00, "cache_read": 1.875, "cache_write": 18.75},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00, "cache_read": 0.08, "cache_write": 1.00},
    }
    
    def __init__(self):
        super().__init__()
        self.claude_dir = Path.home() / ".claude"
        self.stats_cache_path = self.claude_dir / "stats-cache.json"
        self.projects_dir = self.claude_dir / "projects"
        
        # State file to track what we've already processed
        self.state_file = Path.home() / ".claude" / "token_dash_state.json"
        self._processed_uuids: Set[str] = set()
        self._last_stats_hash: Optional[str] = None
        self._load_state()
    
    def _load_state(self) -> None:
        """Load previously processed UUIDs from state file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    self._processed_uuids = set(state.get("processed_uuids", []))
                    self._last_stats_hash = state.get("last_stats_hash")
                    self.log.debug("Loaded state", processed_count=len(self._processed_uuids))
        except Exception as e:
            self.log.warning("Failed to load state", error=str(e))
            self._processed_uuids = set()
    
    def _save_state(self) -> None:
        """Save processed UUIDs to state file."""
        try:
            # Keep only last 10000 UUIDs to prevent unbounded growth
            uuids_to_save = list(self._processed_uuids)[-10000:]
            state = {
                "processed_uuids": uuids_to_save,
                "last_stats_hash": self._last_stats_hash,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            self.log.warning("Failed to save state", error=str(e))
    
    def is_configured(self) -> bool:
        """Check if Claude CLI data directory exists."""
        return self.claude_dir.exists()
    
    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model."""
        model_lower = model.lower()
        
        for known_model, pricing in self.MODELS_PRICING.items():
            if known_model in model_lower or model_lower.startswith(known_model.split("-")[0]):
                return pricing
        
        # Default to opus pricing for unknown models
        self.log.debug("Unknown model, using default pricing", model=model)
        return {"input": 15.00, "output": 75.00, "cache_read": 1.875, "cache_write": 18.75}
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0
    ) -> float:
        """Calculate hypothetical cost in USD (Claude Max users pay $0)."""
        pricing = self.get_model_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * pricing["cache_read"]
        cache_write_cost = (cache_write_tokens / 1_000_000) * pricing["cache_write"]
        
        return round(input_cost + output_cost + cache_read_cost + cache_write_cost, 6)
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from Claude Code internal files."""
        points = []
        
        if not self.is_configured():
            self.log.debug("Claude directory not found")
            return points
        
        # 1. Collect aggregated stats from stats-cache.json
        stats_points = self._collect_from_stats_cache()
        points.extend(stats_points)
        
        # 2. Collect detailed per-message usage from session files
        session_points = self._collect_from_sessions()
        points.extend(session_points)
        
        # Save state for incremental processing
        self._save_state()
        
        return points
    
    def _collect_from_stats_cache(self) -> List[TokenUsagePoint]:
        """Collect aggregated stats from stats-cache.json."""
        points = []
        
        if not self.stats_cache_path.exists():
            self.log.debug("stats-cache.json not found")
            return points
        
        try:
            with open(self.stats_cache_path, "r") as f:
                content = f.read()
                stats = json.loads(content)
            
            # Check if stats have changed
            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash == self._last_stats_hash:
                self.log.debug("stats-cache unchanged, skipping")
                return points
            
            self._last_stats_hash = content_hash
            
            # Extract model usage totals
            model_usage = stats.get("modelUsage", {})
            for model_name, usage in model_usage.items():
                input_tokens = usage.get("inputTokens", 0)
                output_tokens = usage.get("outputTokens", 0)
                cache_read = usage.get("cacheReadInputTokens", 0)
                cache_write = usage.get("cacheCreationInputTokens", 0)
                
                # Calculate hypothetical cost
                cost = self.calculate_cost(
                    model_name, input_tokens, output_tokens,
                    cache_read, cache_write
                )
                
                # Create aggregate point with custom measurement
                points.append(TokenUsagePoint(
                    provider="anthropic",
                    model=self._normalize_model_name(model_name),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=0.0,  # Claude Max is subscription-based
                    timestamp=datetime.now(timezone.utc),
                    tags={
                        "source": "claude-code",
                        "subscription": "claude-max",
                        "data_type": "aggregate"
                    },
                    fields={
                        "cache_read_tokens": cache_read,
                        "cache_write_tokens": cache_write,
                        "hypothetical_cost_usd": cost,
                        "total_sessions": stats.get("totalSessions", 0),
                        "total_messages": stats.get("totalMessages", 0),
                        "web_search_requests": usage.get("webSearchRequests", 0)
                    }
                ))
            
            # Daily activity points
            for daily in stats.get("dailyActivity", []):
                date_str = daily.get("date")
                if date_str:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        points.append(TokenUsagePoint(
                            provider="anthropic",
                            model="claude-code-activity",
                            input_tokens=0,
                            output_tokens=0,
                            cost_usd=0.0,
                            timestamp=date,
                            tags={
                                "source": "claude-code",
                                "data_type": "daily_activity"
                            },
                            fields={
                                "message_count": daily.get("messageCount", 0),
                                "session_count": daily.get("sessionCount", 0),
                                "tool_call_count": daily.get("toolCallCount", 0)
                            }
                        ))
                    except ValueError:
                        continue
            
            self.log.info("Collected stats from stats-cache.json", model_count=len(model_usage))
            
        except json.JSONDecodeError as e:
            self.log.error("Failed to parse stats-cache.json", error=str(e))
        except Exception as e:
            self.log.error("Error reading stats-cache.json", error=str(e))
        
        return points
    
    def _collect_from_sessions(self) -> List[TokenUsagePoint]:
        """Collect detailed per-message usage from session JSONL files."""
        points = []
        
        if not self.projects_dir.exists():
            self.log.debug("projects directory not found")
            return points
        
        new_uuids_count = 0
        
        # Find all session JSONL files
        for jsonl_path in self.projects_dir.rglob("*.jsonl"):
            try:
                session_points, new_count = self._parse_session_file(jsonl_path)
                points.extend(session_points)
                new_uuids_count += new_count
            except Exception as e:
                self.log.debug("Error parsing session file", path=str(jsonl_path), error=str(e))
        
        if new_uuids_count > 0:
            self.log.info("Collected new messages from sessions", new_messages=new_uuids_count)
        
        return points
    
    def _parse_session_file(self, jsonl_path: Path) -> tuple[List[TokenUsagePoint], int]:
        """Parse a single session JSONL file for assistant messages with usage data."""
        points = []
        new_count = 0
        
        with open(jsonl_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                # Only process assistant messages with usage data
                if entry.get("type") != "assistant":
                    continue
                
                uuid = entry.get("uuid")
                if not uuid or uuid in self._processed_uuids:
                    continue
                
                message = entry.get("message", {})
                usage = message.get("usage")
                if not usage:
                    continue
                
                # Extract token counts
                model = message.get("model", "unknown")
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cache_read = usage.get("cache_read_input_tokens", 0)
                cache_write = usage.get("cache_creation_input_tokens", 0)
                
                # Handle nested cache_creation structure
                cache_creation = usage.get("cache_creation", {})
                ephemeral_5m = cache_creation.get("ephemeral_5m_input_tokens", 0)
                ephemeral_1h = cache_creation.get("ephemeral_1h_input_tokens", 0)
                
                # Parse timestamp
                timestamp_str = entry.get("timestamp")
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.now(timezone.utc)
                
                # Calculate hypothetical cost
                cost = self.calculate_cost(
                    model, input_tokens, output_tokens,
                    cache_read, cache_write
                )
                
                # Determine content type
                content = message.get("content", [])
                content_types = set()
                for item in content if isinstance(content, list) else []:
                    if isinstance(item, dict):
                        content_types.add(item.get("type", "unknown"))
                
                has_tool_use = "tool_use" in content_types
                has_thinking = "thinking" in content_types
                
                points.append(TokenUsagePoint(
                    provider="anthropic",
                    model=self._normalize_model_name(model),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=0.0,  # Subscription-based
                    timestamp=timestamp,
                    tags={
                        "source": "claude-code",
                        "subscription": "claude-max",
                        "data_type": "message",
                        "session_id": entry.get("sessionId", "unknown")[:8]
                    },
                    fields={
                        "cache_read_tokens": cache_read,
                        "cache_write_tokens": cache_write,
                        "ephemeral_5m_tokens": ephemeral_5m,
                        "ephemeral_1h_tokens": ephemeral_1h,
                        "hypothetical_cost_usd": cost,
                        "service_tier": usage.get("service_tier", "standard"),
                        "has_tool_use": 1 if has_tool_use else 0,
                        "has_thinking": 1 if has_thinking else 0,
                        "request_id": message.get("id", "")[:20] if message.get("id") else ""
                    }
                ))
                
                self._processed_uuids.add(uuid)
                new_count += 1
        
        return points, new_count
    
    def _normalize_model_name(self, model: str) -> str:
        """Normalize model names for consistent tagging."""
        # Remove date suffixes like -20251101
        import re
        normalized = re.sub(r'-\d{8}$', '', model)
        return normalized.lower()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of Claude Code usage (useful for dashboards)."""
        summary = {
            "configured": self.is_configured(),
            "stats_cache_exists": self.stats_cache_path.exists(),
            "projects_dir_exists": self.projects_dir.exists(),
            "processed_message_count": len(self._processed_uuids)
        }
        
        if self.stats_cache_path.exists():
            try:
                with open(self.stats_cache_path, "r") as f:
                    stats = json.load(f)
                summary["total_sessions"] = stats.get("totalSessions", 0)
                summary["total_messages"] = stats.get("totalMessages", 0)
                summary["first_session_date"] = stats.get("firstSessionDate")
                summary["models_used"] = list(stats.get("modelUsage", {}).keys())
            except:
                pass
        
        return summary
