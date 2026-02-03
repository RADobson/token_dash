# Token Dashboard

Real-time AI API token usage and balance tracking across all providers — integrated directly into OpenClaw's Mission Control.

## Why This Exists

Bot owners currently need to log into 5+ different provider consoles to check balances and usage. This plugin brings all that data into one place within OpenClaw:

- 💰 **See all balances at a glance** — no more console hopping
- 📊 **Track burn rate** — know how fast you're spending
- ⚠️ **Low balance alerts** — get notified before you run out
- 📈 **Usage history** — understand your patterns over time

## Supported Providers

| Provider | Balance | Usage | Status |
|----------|---------|-------|--------|
| OpenAI | ✅ | ✅ | Tested |
| Anthropic | ✅ | ✅ | Tested |
| Moonshot (Kimi) | 🔄 | 🔄 | In Progress |
| OpenRouter | ✅ | ✅ | Tested |

## Installation

### From npm (recommended)

```bash
openclaw plugins install @dobsondev/token-dashboard
```

### From source

```bash
# Clone this repo
git clone https://github.com/RADobson/token_dash
cd token_dash/plugin

# Install and build
npm install
npm run build

# Install into OpenClaw
openclaw plugins install -l .
```

## Usage

### Chat Commands

```
/tokens        # Show current usage and balances
/burn          # Quick burn rate summary
```

### CLI Commands

```bash
openclaw tokens status     # Show current usage
openclaw tokens providers  # List configured providers
```

### Agent Tool

The `token_usage` tool is available to your AI agent:

```
"Check my OpenAI balance"
→ Uses token_usage tool to fetch and display balance
```

## Configuration

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
            "anthropic": { "balanceUsd": 5 },
            "moonshot": { "balanceUsd": 5 }
          }
        }
      }
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `pollIntervalMinutes` | number | 15 | How often to refresh usage data |
| `historyRetentionDays` | number | 90 | How long to keep historical data |
| `alertThresholds.<provider>.balanceUsd` | number | - | Alert when balance drops below this |
| `enabledProviders` | string[] | all | Which providers to track |

## API Keys

The plugin uses API keys from your existing OpenClaw config:

- `OPENAI_API_KEY` — OpenAI
- `ANTHROPIC_API_KEY` — Anthropic
- `MOONSHOT_API_KEY` — Moonshot/Kimi
- `OPENROUTER_API_KEY` — OpenRouter

No additional configuration needed if you already have these set up.

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

## Roadmap

- [x] OpenAI collector
- [x] Anthropic collector
- [x] OpenRouter collector
- [ ] Moonshot/Kimi collector (needs API research)
- [ ] Google AI/Vertex collector
- [ ] Web UI dashboard in Mission Control
- [ ] Historical charts
- [ ] Burn rate forecasting
- [ ] Budget caps

## Legacy: Standalone Dashboard

The original `collectors/` and `docker-compose.yml` provide a standalone Grafana dashboard (InfluxDB + Python collectors). This is still useful if you want:

- Self-hosted time-series storage
- Custom Grafana dashboards
- Historical data beyond 90 days

See `collectors/README.md` for the standalone setup.

## License

MIT — Dobson Development
