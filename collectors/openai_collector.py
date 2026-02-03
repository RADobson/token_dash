"""OpenAI API usage collector."""

from datetime import datetime, timezone, timedelta
from typing import List, Optional
import httpx

from .base import BaseCollector, TokenUsagePoint
from .config import settings


class OpenAICollector(BaseCollector):
    """Collects usage data from OpenAI API."""
    
    USAGE_URL = "https://api.openai.com/v1/organization/usage"
    MODELS_PRICING = {
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-3.5-turbo-16k": {"input": 3.00, "output": 4.00},
        "text-embedding-ada-002": {"input": 0.10, "output": 0.0},
        "text-embedding-3-small": {"input": 0.02, "output": 0.0},
        "text-embedding-3-large": {"input": 0.13, "output": 0.0},
        "dall-e-3": {"input": 0.0, "output": 0.0},  # Priced per image
        "whisper-1": {"input": 0.0, "output": 0.0},  # Priced per minute
        "tts-1": {"input": 0.0, "output": 0.0},  # Priced per character
    }
    
    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(settings.openai_api_key)
    
    def get_model_pricing(self, model: str) -> dict:
        """Get pricing for a model, with fallback for unknown models."""
        # Try exact match first
        if model in self.MODELS_PRICING:
            return self.MODELS_PRICING[model]
        
        # Try prefix matching for versioned models
        for known_model, pricing in self.MODELS_PRICING.items():
            if model.startswith(known_model):
                return pricing
        
        # Default fallback
        self.log.warning("Unknown model, using default pricing", model=model)
        return {"input": 1.0, "output": 2.0}
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        pricing = self.get_model_pricing(model)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data from OpenAI API."""
        points = []
        
        async with httpx.AsyncClient() as client:
            # Try the usage endpoint
            try:
                # Get usage for today and yesterday
                today = datetime.now(timezone.utc).date()
                yesterday = today - timedelta(days=1)
                
                # OpenAI usage API requires date range
                response = await client.get(
                    f"{self.USAGE_URL}",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    params={
                        "date": today.isoformat()
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    points.extend(self._parse_usage_response(data))
                elif response.status_code == 404:
                    # Try alternative endpoint
                    self.log.info("Usage endpoint not available, trying dashboard API")
                    points.extend(await self._collect_from_dashboard(client))
                else:
                    self.log.warning(
                        "OpenAI API error",
                        status=response.status_code,
                        body=response.text[:500]
                    )
                    
            except httpx.TimeoutException:
                self.log.error("OpenAI API timeout")
            except Exception as e:
                self.log.error("OpenAI collection error", error=str(e))
        
        return points
    
    def _parse_usage_response(self, data: dict) -> List[TokenUsagePoint]:
        """Parse OpenAI usage API response."""
        points = []
        
        # Handle different response formats
        usage_data = data.get("data", []) or data.get("usage", [])
        
        for item in usage_data:
            model = item.get("model", item.get("snapshot_id", "unknown"))
            input_tokens = item.get("n_context_tokens_total", 0) or item.get("prompt_tokens", 0)
            output_tokens = item.get("n_generated_tokens_total", 0) or item.get("completion_tokens", 0)
            
            # Parse timestamp
            timestamp_str = item.get("aggregation_timestamp") or item.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except:
                    timestamp = datetime.now(timezone.utc)
            else:
                timestamp = datetime.now(timezone.utc)
            
            cost = self.calculate_cost(model, input_tokens, output_tokens)
            
            points.append(TokenUsagePoint(
                provider="openai",
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                timestamp=timestamp,
                tags={"source": "api"}
            ))
        
        return points
    
    async def _collect_from_dashboard(self, client: httpx.AsyncClient) -> List[TokenUsagePoint]:
        """Fallback: Try to get usage from dashboard API."""
        # This is a fallback for when the official usage API isn't available
        # In production, you might need to use session tokens from the dashboard
        self.log.debug("Dashboard API collection not implemented yet")
        return []
