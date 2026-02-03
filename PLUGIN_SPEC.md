# OpenClaw Token Dashboard Plugin Spec

## Vision
A native OpenClaw plugin that gives bot owners real-time visibility into their AI API usage and balances across all providers — without leaving the Gateway dashboard.

## Why This Matters
- Bot owners currently need to log into 5+ provider consoles to check balances
- No unified view of burn rate across providers
- No forecasting of when credits will run out
- OpenClaw already tracks per-session usage, but not account-level balances

## Architecture

### Plugin Structure
```
token-dashboard/
├── openclaw.plugin.json       # Plugin manifest
├── index.ts                   # Main plugin entry
├── src/
│   ├── collectors/
│   │   ├── base.ts            # Collector interface
│   │   ├── openai.ts          # OpenAI usage API
│   │   ├── anthropic.ts       # Anthropic usage API
│   │   ├── moonshot.ts        # Moonshot/Kimi usage
│   │   ├── openrouter.ts      # OpenRouter usage API
│   │   ├── google.ts          # Google AI/Vertex usage
│   │   └── openclaw.ts        # Local OpenClaw session stats
│   ├── aggregator.ts          # Combines all collector data
│   ├── storage.ts             # Time-series storage (SQLite?)
│   ├── forecaster.ts          # Burn rate / runway calculations
│   └── types.ts               # Shared types
├── hooks/
│   └── usage-alert/           # Alert when balance low
└── skills/
    └── token-dashboard/       # CLI skill for checking usage
```

### Gateway Integration

**RPC Methods:**
- `token-dashboard.status` — Current balances + burn rates
- `token-dashboard.history` — Historical usage data
- `token-dashboard.providers` — List configured providers
- `token-dashboard.alerts` — Get/set balance alert thresholds

**CLI Commands:**
- `openclaw tokens` — Show current balances
- `openclaw tokens history` — Show usage over time
- `openclaw tokens alerts` — Configure low-balance alerts

**Auto-Reply Commands:**
- `/tokens` — Quick balance check in chat
- `/burn` — Current burn rate summary

### Provider API Research

| Provider | Usage API | Balance API | Auth |
|----------|-----------|-------------|------|
| OpenAI | ✅ `/v1/dashboard/billing/usage` | ✅ `/v1/dashboard/billing/subscription` | API Key |
| Anthropic | ✅ `/v1/usage` | ✅ Console API | API Key |
| Moonshot | 🔍 TBD (OpenAI-compat, check `/v1/usage`) | 🔍 TBD | API Key |
| OpenRouter | ✅ `/api/v1/credits` | ✅ Same endpoint | API Key |
| Google | 🔍 Cloud Billing API | 🔍 Cloud Billing API | Service Account |
| Local OpenClaw | ✅ Gateway RPC | N/A | Internal |

### Data Model

```typescript
interface ProviderUsage {
  providerId: string;
  timestamp: Date;
  
  // Token usage
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens?: number;
  cacheWriteTokens?: number;
  
  // Cost (USD)
  cost: number;
  
  // Balance (if available)
  balance?: number;
  creditLimit?: number;
}

interface BurnRate {
  providerId: string;
  hourly: number;
  daily: number;
  weekly: number;
  runwayHours?: number;  // Time until balance hits 0
}
```

### Configuration

```json5
{
  "plugins": {
    "entries": {
      "token-dashboard": {
        "enabled": true,
        "config": {
          "pollIntervalMinutes": 15,
          "alertThresholds": {
            "openai": { "balanceUsd": 10 },
            "anthropic": { "balanceUsd": 5 },
            "moonshot": { "balanceUsd": 5 }
          },
          "historyRetentionDays": 90
        }
      }
    }
  }
}
```

## Phase 1: MVP
1. [x] Research provider APIs
2. [ ] Scaffold plugin structure
3. [ ] Implement OpenAI collector
4. [ ] Implement Anthropic collector
5. [ ] Implement Moonshot collector
6. [ ] Implement OpenClaw local stats aggregation
7. [ ] Add `/tokens` chat command
8. [ ] Add `openclaw tokens` CLI command

## Phase 2: Dashboard
1. [ ] Add web UI component to Gateway dashboard
2. [ ] Historical charts (daily/weekly/monthly)
3. [ ] Burn rate visualization
4. [ ] Runway forecasting

## Phase 3: Alerts
1. [ ] Low balance alerts via configured channels
2. [ ] Spike detection (unusual usage patterns)
3. [ ] Budget caps (optional hard limits)

## Notes
- Should work with API keys already configured in OpenClaw
- Don't store raw API keys — use OpenClaw's existing credential system
- Consider privacy: usage data stays local by default
