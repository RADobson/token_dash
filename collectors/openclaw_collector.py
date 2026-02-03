"""OpenClaw session usage collector."""

from datetime import datetime, timezone
from typing import List
import httpx

from .base import BaseCollector, TokenUsagePoint
from .config import settings


class OpenClawCollector(BaseCollector):
    """Collects usage data from OpenClaw Gateway sessions."""
    
    def is_configured(self) -> bool:
        """Check if OpenClaw Gateway is configured."""
        return bool(settings.openclaw_gateway_url and settings.openclaw_gateway_token)
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from OpenClaw Gateway."""
        points = []
        
        if not self.is_configured():
            return points
        
        async with httpx.AsyncClient() as client:
            try:
                # Get session list with usage stats
                response = await client.post(
                    f"{settings.openclaw_gateway_url}/api/sessions/list",
                    headers={
                        "Authorization": f"Bearer {settings.openclaw_gateway_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "limit": 50,
                        "messageLimit": 0,
                        "activeMinutes": 1440  # Last 24 hours
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    sessions = data.get("sessions", [])
                    
                    for session in sessions:
                        session_points = self._parse_session(session)
                        points.extend(session_points)
                else:
                    self.log.warning(
                        "OpenClaw API error",
                        status=response.status_code,
                        body=response.text[:200]
                    )
                    
            except httpx.TimeoutException:
                self.log.error("OpenClaw Gateway timeout")
            except httpx.ConnectError:
                self.log.debug("OpenClaw Gateway not reachable")
            except Exception as e:
                self.log.error("OpenClaw collection error", error=str(e))
        
        return points
    
    def _parse_session(self, session: dict) -> List[TokenUsagePoint]:
        """Parse a single OpenClaw session."""
        points = []
        
        usage = session.get("usage", {})
        if not usage:
            return points
        
        # Extract session info
        session_key = session.get("key", "unknown")
        model = session.get("model", "unknown")
        
        # Parse model to get provider
        provider = "unknown"
        if "/" in model:
            provider = model.split("/")[0]
        
        # Get token counts
        input_tokens = usage.get("inputTokens", 0) or usage.get("in", 0)
        output_tokens = usage.get("outputTokens", 0) or usage.get("out", 0)
        cache_read = usage.get("cacheReadInputTokens", 0) or usage.get("cacheRead", 0)
        cache_write = usage.get("cacheCreationInputTokens", 0) or usage.get("cacheWrite", 0)
        
        # Get cost if available
        cost = usage.get("cost", 0) or usage.get("costUsd", 0) or 0
        
        # Parse timestamp
        updated_at = session.get("updatedAt") or session.get("lastActivity")
        if updated_at:
            try:
                if isinstance(updated_at, (int, float)):
                    timestamp = datetime.fromtimestamp(updated_at / 1000, tz=timezone.utc)
                else:
                    timestamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except:
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)
        
        points.append(TokenUsagePoint(
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=float(cost),
            timestamp=timestamp,
            tags={
                "source": "openclaw",
                "session": session_key[:16] if len(session_key) > 16 else session_key
            },
            fields={
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write
            }
        ))
        
        return points
