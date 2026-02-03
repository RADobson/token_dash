# Token Dashboard 🎯

**Track all your AI API token usage in one beautiful Grafana dashboard.**

![Status](https://img.shields.io/badge/status-beta-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- 📊 **Unified Dashboard** - All your AI spending in one place
- 🤖 **Multi-Provider Support**
  - OpenAI API (GPT-4, GPT-3.5, embeddings, etc.)
  - Anthropic API (Claude models)
  - Claude Max subscription usage
  - ChatGPT Plus subscription usage
  - OpenClaw session statistics
- 💰 **Cost Tracking** - Real-time cost estimates with configurable pricing
- 📈 **Historical Trends** - Daily, weekly, monthly usage patterns
- 🔔 **Alerting** - Get notified when approaching limits
- 🐳 **Docker-Ready** - One command deployment

## Quick Start

### Prerequisites
- Docker & Docker Compose
- API keys for OpenAI and/or Anthropic (optional - for API tracking)
- Claude Code and/or Codex CLI (optional - for subscription tracking)

### 1. Clone & Configure

```bash
git clone https://github.com/RADobson/token_dash.git
cd token_dash
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Access Dashboard

Open [http://localhost:3000](http://localhost:3000) in your browser.
- **Username:** admin
- **Password:** admin (change on first login)

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for usage tracking | No |
| `ANTHROPIC_API_KEY` | Anthropic API key for usage tracking | No |
| `INFLUXDB_TOKEN` | InfluxDB authentication token | Auto-generated |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password | No (default: admin) |
| `COLLECT_INTERVAL` | Data collection interval in seconds | No (default: 300) |

### Data Sources

#### 1. OpenAI API Usage
Tracks usage via OpenAI's billing/usage API endpoint.

#### 2. Anthropic API Usage  
Tracks usage via Anthropic's usage API endpoint.

#### 3. Claude Code Subscription (Claude Max)
Parses output from `claude usage` command to track subscription usage against limits.

#### 4. Codex CLI (ChatGPT Plus)
Parses output from `codex usage` command to track subscription usage.

#### 5. OpenClaw Sessions
Tracks token usage from OpenClaw agent sessions via the Gateway API.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Token Dashboard                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │  Collectors  │──▶│   InfluxDB   │──▶│   Grafana   │ │
│  │   (Python)   │   │ (Time-series)│   │ (Dashboard) │ │
│  └──────────────┘   └──────────────┘   └─────────────┘ │
│         │                                               │
│         ├── openai_collector.py                        │
│         ├── anthropic_collector.py                     │
│         ├── claude_code_collector.py                   │
│         ├── codex_collector.py                         │
│         └── openclaw_collector.py                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Dashboard Panels

### Overview
- Total tokens used (all providers)
- Estimated total cost
- Active API keys
- Collection status

### By Provider
- OpenAI usage breakdown by model
- Anthropic usage breakdown by model
- Subscription usage vs limits

### Trends
- Daily/weekly/monthly usage charts
- Cost trends over time
- Projection to end of billing cycle

### Alerts
- Approaching rate limits
- Unusual usage spikes
- API errors

## Development

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run collectors manually
python collectors/openai_collector.py
```

### Adding New Providers

1. Create a new collector in `collectors/`
2. Implement the `Collector` base class
3. Add to `docker-compose.yml`
4. Create Grafana dashboard panel

## Roadmap

- [x] Project structure
- [x] Docker Compose setup
- [x] InfluxDB integration
- [x] Grafana provisioning
- [ ] OpenAI collector
- [ ] Anthropic collector
- [ ] Claude Code subscription collector
- [ ] Codex subscription collector
- [ ] OpenClaw collector
- [ ] Pre-built dashboards
- [ ] Alert rules
- [ ] Cost estimation
- [ ] Multi-organization support

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

Built with ❤️ by [Dobson Development](https://dobsondevelopment.com.au)
