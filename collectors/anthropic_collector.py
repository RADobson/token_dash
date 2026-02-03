"""Anthropic API usage collector."""

from datetime import datetime, timezone
from typing import List
import httpx

from .base import BaseCollector, TokenUsagePoint
from .config import settings


class AnthropicCollector(BaseCollector):
    """Collects usage data from Anthropic API."""
    
    # Anthropic doesn't have a public usage API yet
    # We'll track usage by parsing response headers or using admin API if available
    
    MODELS_PRICING = {
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
        "claude-opus-4": {"input": 15.00, "output": 75.00},
        "claude-sonnet-4": {"input": 3.00, "output": 15.00},
        "claude-2.1": {"input": 8.00, "output": 24.00},
        "claude-2.0": {"input": 8.00, "output": 24.00},
        "claude-instant-1.2": {"input": 0.80, "output": 2.40},
    }
    
    def is_configured(self) -> bool:
        """Check if Anthropic API key is configured."""
        return bool(settings.anthropic_api_key)
    
    def get_model_pricing(self, model: str) -> dict:
        """Get pricing for a model."""
        # Normalize model name
        model_lower = model.lower()
        
        for known_model, pricing in self.MODELS_PRICING.items():
            if known_model in model_lower or model_lower in known_model:
                return pricing
        
        # Default fallback
        self.log.warning("Unknown Anthropic model", model=model)
        return {"input": 3.00, "output": 15.00}  # Default to Sonnet pricing
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        pricing = self.get_model_pricing(model)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from Anthropic."""
        points = []
        
        # Anthropic doesn't have a public usage API
        # Options:
        # 1. Track usage locally by intercepting API calls
        # 2. Use admin/billing API (requires special access)
        # 3. Parse usage from Console/Dashboard (web scraping)
        
        # For now, we'll check if there's a usage endpoint
        async with httpx.AsyncClient() as client:
            try:
                # Try the admin API (beta)
                response = await client.get(
                    "https://api.anthropic.com/v1/usage",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2024-01-01",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    points.extend(self._parse_usage_response(data))
                elif response.status_code == 404:
                    self.log.debug("Anthropic usage API not available")
                else:
                    self.log.debug(
                        "Anthropic API response",
                        status=response.status_code
                    )
                    
            except httpx.TimeoutException:
                self.log.error("Anthropic API timeout")
            except Exception as e:
                self.log.debug("Anthropic collection skipped", reason=str(e))
        
        return points
    
    def _parse_usage_response(self, data: dict) -> List[TokenUsagePoint]:
        """Parse Anthropic usage API response."""
        points = []
        
        # Parse based on actual API response structure
        # This is speculative until we have actual API access
        usage_data = data.get("usage", []) or data.get("data", [])
        
        for item in usage_data:
            model = item.get("model", "claude-3-sonnet")
            input_tokens = item.get("input_tokens", 0)
            output_tokens = item.get("output_tokens", 0)
            
            timestamp_str = item.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            cost = self.calculate_cost(model, input_tokens, output_tokens)
            
            points.append(TokenUsagePoint(
                provider="anthropic",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                timestamp=timestamp,
                tags={"source": "api"}
            ))
        
        return points
