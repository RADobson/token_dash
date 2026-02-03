"""Configuration management for Token Dashboard collectors."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # InfluxDB settings
    influxdb_url: str = Field(default="http://localhost:8086")
    influxdb_token: str = Field(default="tokendash-super-secret-token")
    influxdb_org: str = Field(default="tokendash")
    influxdb_bucket: str = Field(default="tokens")
    
    # API Keys
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    
    # OpenClaw settings
    openclaw_gateway_url: Optional[str] = Field(default=None)
    openclaw_gateway_token: Optional[str] = Field(default=None)
    
    # Collection settings
    collect_interval: int = Field(default=300, description="Collection interval in seconds")
    
    # Pricing (USD per 1M tokens) - can be overridden via env
    openai_gpt4_input_price: float = Field(default=2.50)
    openai_gpt4_output_price: float = Field(default=10.00)
    openai_gpt4_turbo_input_price: float = Field(default=10.00)
    openai_gpt4_turbo_output_price: float = Field(default=30.00)
    openai_gpt35_input_price: float = Field(default=0.50)
    openai_gpt35_output_price: float = Field(default=1.50)
    
    anthropic_claude_opus_input_price: float = Field(default=15.00)
    anthropic_claude_opus_output_price: float = Field(default=75.00)
    anthropic_claude_sonnet_input_price: float = Field(default=3.00)
    anthropic_claude_sonnet_output_price: float = Field(default=15.00)
    anthropic_claude_haiku_input_price: float = Field(default=0.25)
    anthropic_claude_haiku_output_price: float = Field(default=1.25)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
