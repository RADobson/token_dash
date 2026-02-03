# Token Dashboard Collectors

This directory contains Python collectors that gather AI API token usage data and store it in InfluxDB for visualization in Grafana.

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Collectors    │────▶│  InfluxDB    │────▶│   Grafana   │
│  (Python/async) │     │  (Time-series)│     │ (Dashboard) │
└─────────────────┘     └──────────────┘     └─────────────┘
```

## Available Collectors

| Collector | Description | Data Source | Configuration |
|-----------|-------------|-------------|---------------|
| `OpenAICollector` | OpenAI API usage | OpenAI Usage API | `OPENAI_API_KEY` |
| `AnthropicCollector` | Anthropic API usage | Anthropic API | `ANTHROPIC_API_KEY` |
| `OpenClawCollector` | OpenClaw session usage | OpenClaw Gateway | `OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN` |
| `ClaudeCodeCollector` | Claude Code CLI usage | `~/.claude/stats-cache.json` | None (reads local file) |
| `CodexCollector` | OpenAI Codex CLI usage | Codex CLI (if available) | None |

## Quick Start

### 1. Install Dependencies

```bash
cd collectors
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# InfluxDB settings
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=tokendash-super-secret-token
INFLUXDB_ORG=tokendash
INFLUXDB_BUCKET=tokens

# API Keys (optional - collectors will skip if not configured)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# OpenClaw Gateway (optional)
OPENCLAW_GATEWAY_URL=http://localhost:18789
OPENCLAW_GATEWAY_TOKEN=your-token
```

### 3. Run Collectors

```bash
# Run once
python -m collectors.main

# Or use the run script
python run_collectors.py
```

## Collector Details

### Claude Code Collector

The Claude Code collector reads from the local Claude Code stats cache file.

**Data Collected:**
- Token usage by model (Opus, Sonnet, Haiku)
- Cache read/write tokens
- Estimated cost calculations
- Daily activity metrics

**Stats Cache Location:**
- macOS/Linux: `~/.claude/stats-cache.json`
- Windows: `%USERPROFILE%\.claude\stats-cache.json`

**File Format:**
```json
{
  "version": 2,
  "modelUsage": {
    "claude-opus-4-5-20251101": {
      "inputTokens": 1000,
      "outputTokens": 500,
      "cacheReadInputTokens": 10000,
      "cacheCreationInputTokens": 5000,
      "costUSD": 0.05
    }
  }
}
```

### OpenAI Collector

Collects usage from OpenAI's organization usage API.

**Pricing Models Supported:**
- GPT-4 series (including GPT-4o)
- GPT-3.5 Turbo
- Embedding models
- Image and audio models

### OpenClaw Collector

Connects to the OpenClaw Gateway to collect session-level usage data.

**Data Collected:**
- Per-session token usage
- Model information
- Cost tracking
- Cache token metrics

## Development

### Adding a New Collector

1. Create a new file in `collectors/`:

```python
# collectors/my_collector.py
from .base import BaseCollector, TokenUsagePoint

class MyCollector(BaseCollector):
    def is_configured(self) -> bool:
        """Check if required configuration is present."""
        return True  # Or check for API keys, etc.
    
    async def collect(self) -> List[TokenUsagePoint]:
        """Collect usage data and return list of points."""
        points = []
        # Your collection logic here
        return points
```

2. Register in `main.py`:

```python
from .my_collector import MyCollector

# In CollectorOrchestrator.__init__
self.collectors = [
    # ... existing collectors
    MyCollector(),
]
```

### TokenUsagePoint Schema

Each collector returns `TokenUsagePoint` objects:

```python
TokenUsagePoint(
    provider="openai",           # Provider name (lowercase)
    model="gpt-4",               # Model identifier
    input_tokens=1000,           # Input/prompt tokens
    output_tokens=500,           # Output/completion tokens
    total_tokens=1500,           # Auto-calculated if not provided
    cost_usd=0.05,               # Estimated cost in USD
    timestamp=datetime.now(),    # When the usage occurred
    tags={                       # Additional string tags
        "source": "api",
        "session": "abc123"
    },
    fields={                     # Additional numeric fields
        "cache_read_tokens": 1000,
        "cache_savings_usd": 0.01
    }
)
```

### InfluxDB Schema

Data is stored with the following schema:

**Measurement:** `token_usage`

**Tags:**
- `provider` - API provider (openai, anthropic, etc.)
- `model` - Model name
- `source` - Data source (api, claude-code, openclaw, etc.)
- Additional custom tags from collectors

**Fields:**
- `input_tokens` - Number of input tokens
- `output_tokens` - Number of output tokens
- `total_tokens` - Total tokens used
- `cost_usd` - Estimated cost in USD
- Custom fields from collectors (cache tokens, etc.)

## Troubleshooting

### Claude Code stats not appearing

1. Check if the stats file exists:
   ```bash
   ls -la ~/.claude/stats-cache.json
   ```

2. Check file permissions - the collector needs read access

3. Verify Claude Code has been used recently (stats are updated periodically)

### InfluxDB connection errors

1. Verify InfluxDB is running:
   ```bash
   curl http://localhost:8086/ping
   ```

2. Check credentials in your `.env` file

3. Verify the bucket exists:
   ```bash
   influx bucket list --org tokendash
   ```

### API rate limits

Collectors respect API rate limits by:
- Running at configurable intervals (default: 5 minutes)
- Caching data where possible
- Gracefully handling errors

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `INFLUXDB_URL` | `http://localhost:8086` | InfluxDB URL |
| `INFLUXDB_TOKEN` | `tokendash-super-secret-token` | InfluxDB auth token |
| `INFLUXDB_ORG` | `tokendash` | InfluxDB organization |
| `INFLUXDB_BUCKET` | `tokens` | InfluxDB bucket name |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `OPENCLAW_GATEWAY_URL` | - | OpenClaw Gateway URL |
| `OPENCLAW_GATEWAY_TOKEN` | - | OpenClaw Gateway token |
| `COLLECT_INTERVAL` | `300` | Collection interval in seconds |

## Docker Usage

When running in Docker (via docker-compose):

```bash
# Start all services
docker-compose up -d

# View collector logs
docker-compose logs -f collector

# Restart collector after code changes
docker-compose restart collector
```

The collector container mounts the local `~/.claude` directory to read stats for the Claude Code collector.

## License

MIT - Dobson Development
