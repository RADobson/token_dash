# Token Dashboard

Real-time AI API token usage and balance tracking across all providers — integrated directly into OpenClaw's Mission Control.

## Why This Exists

Bot owners currently need to log into 5+ different provider consoles to check balances and usage. This plugin brings all that data into one place within OpenClaw:

- 💰 **See all balances at a glance** — no more console hopping
- 📊 **Track burn rate** — know how fast you're spending
- ⚠️ **Low balance alerts** — get notified before you run out
- 📈 **Usage history** — understand your patterns over time
- 🚀 **Claude Code integration** — track your local Claude Code usage

## Supported Providers

| Provider | Balance | Usage | Source | Status |
|----------|---------|-------|--------|--------|
| OpenAI | ✅ | ✅ | API | Tested |
| Anthropic | ✅ | ✅ | API | Tested |
| OpenRouter | ✅ | ✅ | API | Tested |
| Claude Code | 🚀 | ✅ | Local stats | New! |
| Moonshot (Kimi) | 🔄 | 🔄 | API | In Progress |

## Features

### Grafana Dashboard

The standalone dashboard (via Docker Compose) includes:

- **Overview Panel**: Total tokens, estimated cost, input/output breakdown
- **Time Series**: Token usage over time by provider
- **Cost Analysis**: Weekly/monthly costs, burn rate projections
- **Provider Breakdown**: Pie charts showing usage by provider and model
- **Claude Code Specific**: Cache usage tracking, model breakdown
- **Detailed Tables**: Per-model usage statistics

### Collectors

| Collector | Description |
|-----------|-------------|
| `OpenAICollector` | Tracks OpenAI API usage (GPT-4, GPT-3.5, etc.) |
| `AnthropicCollector` | Tracks Anthropic API usage (Claude models) |
| `OpenClawCollector` | Collects usage from OpenClaw sessions |
| `ClaudeCodeCollector` | **NEW**: Reads from Claude Code local stats cache |
| `CodexCollector` | Tracks OpenAI Codex CLI usage |

## Installation

### From npm (recommended for OpenClaw users)

```bash
openclaw plugins install @dobsondev/token-dashboard
```

### From source (standalone with Grafana)

```bash
# Clone this repo
git clone https://github.com/RADobson/token_dash
cd token_dash

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Access Grafana at http://localhost:3456
```

## Usage

### Chat Commands (OpenClaw Plugin)

```
/tokens        # Show current usage and balances
/burn          # Quick burn rate summary
```

### CLI Commands

```bash
openclaw tokens status     # Show current usage
openclaw tokens providers  # List configured providers
```

### Standalone Collectors

```bash
cd collectors

# Install dependencies
pip install -r requirements.txt

# Run collectors
python -m collectors.main

# Or use Docker
docker-compose up -d
```

## Claude Code Integration

The Claude Code collector automatically reads from your local Claude Code installation:

**Features:**
- Reads from `~/.claude/stats-cache.json`
- Tracks usage by model (Opus, Sonnet, Haiku)
- Calculates cache savings (prompt caching reduces costs by ~90%)
- No additional configuration needed

**Requirements:**
- Claude Code CLI installed and used at least once
- Read access to `~/.claude/stats-cache.json`

**Data Collected:**
```json
{
  "model": "claude-opus-4-5-20251101",
  "input_tokens": 1000,
  "output_tokens": 500,
  "cache_read_tokens": 10000,
  "cache_savings_usd": 0.09
}
```

## Configuration

### OpenClaw Plugin

Add to your OpenClaw config:

```json5
{
  "plugins": {
    "entries": {
      "token-dashboard": {
        "enabled": true,
        "config": {
          "pollIntervalMinutes": 15,
          "historyRetentionDays": 90,
          "alertThresholds": {
            "openai": { "balanceUsd": 10 },
            "anthropic": { "balanceUsd": 5 }
          }
        }
      }
    }
  }
}
```

### Environment Variables (Standalone)

Create a `.env` file:

```bash
# InfluxDB (required)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=tokendash-super-secret-token
INFLUXDB_ORG=tokendash
INFLUXDB_BUCKET=tokens

# API Keys (optional - collectors skip if not set)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# OpenClaw Gateway (optional)
OPENCLAW_GATEWAY_URL=http://localhost:18789
OPENCLAW_GATEWAY_TOKEN=your-token

# Collection interval (seconds)
COLLECT_INTERVAL=300
```

## Grafana Dashboard

### Access

- URL: http://localhost:3456
- Default credentials: `admin` / `admin`

### Dashboard Sections

1. **Overview** - Quick stats for the last 24 hours
2. **Detailed Breakdown** - Charts by provider and model
3. **Claude Code Specific** - Cache usage and model breakdown
4. **Cost Analysis** - Weekly/monthly costs and projections

### Importing Dashboard

The dashboard is automatically provisioned. To import manually:

1. Go to Grafana → Dashboards → Import
2. Upload `grafana/dashboards/token_usage.json`

## API Keys

The plugin uses API keys from your existing OpenClaw config or environment:

| Provider | Variable | Notes |
|----------|----------|-------|
| OpenAI | `OPENAI_API_KEY` | Organization usage API |
| Anthropic | `ANTHROPIC_API_KEY` | Admin API (beta) |
| OpenRouter | `OPENROUTER_API_KEY` | Usage endpoint |
| Claude Code | None | Reads local stats file |

## RPC Methods

For programmatic access:

```typescript
// Get current status
const status = await gateway.call('token-dashboard.status');

// Get cached data (faster, may be stale)
const cached = await gateway.call('token-dashboard.cached');

// List providers
const providers = await gateway.call('token-dashboard.providers');
```

## Development

### Project Structure

```
token_dash/
├── collectors/           # Python collectors
│   ├── base.py          # Base collector class
│   ├── main.py          # Orchestrator
│   ├── claude_code_collector.py  # NEW: Claude Code integration
│   └── ...
├── grafana/
│   └── dashboards/
│       └── token_usage.json  # Dashboard config
├── plugin/              # OpenClaw plugin (TypeScript)
├── docker-compose.yml   # Standalone setup
└── README.md
```

### Adding a New Collector

1. Create collector in `collectors/`:

```python
from .base import BaseCollector, TokenUsagePoint

class MyCollector(BaseCollector):
    def is_configured(self) -> bool:
        return True
    
    async def collect(self) -> List[TokenUsagePoint]:
        # Collection logic
        return [TokenUsagePoint(...)]
```

2. Register in `collectors/main.py`

See [collectors/README.md](collectors/README.md) for detailed documentation.

## Troubleshooting

### Claude Code stats not appearing

1. Check if stats file exists:
   ```bash
   cat ~/.claude/stats-cache.json
   ```

2. Ensure Claude Code has been used recently

3. Check collector logs:
   ```bash
   docker-compose logs collector
   ```

### No data in Grafana

1. Verify InfluxDB is running:
   ```bash
   curl http://localhost:8086/ping
   ```

2. Check collectors are writing data:
   ```bash
   docker-compose logs -f collector
   ```

3. Verify time range in Grafana (default is last 24h)

## Roadmap

- [x] OpenAI collector
- [x] Anthropic collector
- [x] OpenRouter collector
- [x] **Claude Code collector** (NEW!)
- [ ] Moonshot/Kimi collector
- [ ] Google AI/Vertex collector
- [ ] Web UI dashboard in Mission Control
- [ ] Historical charts with forecasting
- [ ] Budget caps and alerts
- [ ] Multi-user support

## Changelog

### 2025-02-03
- **Added**: Claude Code usage scraping via `stats-cache.json`
- **Improved**: Enhanced Grafana dashboard with new panels
- **Improved**: Better documentation for collectors
- **Added**: Cache usage tracking for Claude Code

## License

MIT — Dobson Development

## Contributing

Pull requests welcome! Please ensure:
- Code follows existing style
- Tests pass (if applicable)
- Documentation is updated
