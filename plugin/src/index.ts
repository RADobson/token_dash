/**
 * OpenClaw Token Dashboard Plugin
 * 
 * Real-time AI API token usage and balance tracking across all providers.
 * Integrates with OpenClaw's Mission Control for unified visibility.
 */

import type { PluginApi } from 'openclaw';
import {
  OpenAICollector,
  AnthropicCollector,
  MoonshotCollector,
  OpenRouterCollector,
  type Collector,
} from './collectors/index.js';
import type {
  TokenDashboardConfig,
  DashboardSummary,
  ProviderStatus,
  UsageAlert,
  CollectorConfig,
} from './types.js';

// Initialize collectors
const collectors: Record<string, Collector> = {
  openai: new OpenAICollector(),
  anthropic: new AnthropicCollector(),
  moonshot: new MoonshotCollector(),
  openrouter: new OpenRouterCollector(),
};

// Store for caching usage data
let lastFetch: DashboardSummary | null = null;
let pollInterval: NodeJS.Timeout | null = null;

/**
 * Get API keys from OpenClaw config
 */
function getCollectorConfig(api: PluginApi, providerId: string): CollectorConfig {
  const config = api.config;
  
  // Map provider IDs to their env var names
  const envVarMap: Record<string, string> = {
    openai: 'OPENAI_API_KEY',
    anthropic: 'ANTHROPIC_API_KEY',
    moonshot: 'MOONSHOT_API_KEY',
    openrouter: 'OPENROUTER_API_KEY',
  };
  
  const envVar = envVarMap[providerId];
  const apiKey = envVar ? (config.env?.[envVar] || process.env[envVar]) : undefined;
  
  // Get base URL from provider config if available
  const baseUrl = config.models?.providers?.[providerId]?.baseUrl;
  
  return {
    apiKey,
    baseUrl,
    enabled: !!apiKey,
  };
}

/**
 * Fetch usage from all configured providers
 */
async function fetchAllUsage(api: PluginApi): Promise<DashboardSummary> {
  const pluginConfig = api.config.plugins?.entries?.['token-dashboard']?.config as TokenDashboardConfig | undefined;
  const enabledProviders = pluginConfig?.enabledProviders || Object.keys(collectors);
  
  const providerStatuses: ProviderStatus[] = [];
  const alerts: UsageAlert[] = [];
  
  let totalBalance: number | undefined;
  let totalDailyCost = 0;
  
  for (const [providerId, collector] of Object.entries(collectors)) {
    if (!enabledProviders.includes(providerId)) {
      continue;
    }
    
    const collectorConfig = getCollectorConfig(api, providerId);
    const status: ProviderStatus = {
      providerId,
      name: collector.providerName,
      isConfigured: collector.isConfigured(collectorConfig),
      isReachable: false,
      lastChecked: new Date(),
    };
    
    if (!status.isConfigured) {
      providerStatuses.push(status);
      continue;
    }
    
    try {
      const usage = await collector.fetchUsage(collectorConfig);
      status.isReachable = true;
      status.currentUsage = usage;
      
      // Aggregate balance if available
      if (usage.balanceUsd !== undefined) {
        totalBalance = (totalBalance ?? 0) + usage.balanceUsd;
      }
      
      // Check alert thresholds
      const thresholds = pluginConfig?.alertThresholds?.[providerId];
      if (thresholds?.balanceUsd !== undefined && usage.balanceUsd !== undefined) {
        if (usage.balanceUsd < thresholds.balanceUsd) {
          alerts.push({
            providerId,
            type: 'low_balance',
            message: `${collector.providerName} balance ($${usage.balanceUsd.toFixed(2)}) is below threshold ($${thresholds.balanceUsd})`,
            severity: usage.balanceUsd < thresholds.balanceUsd / 2 ? 'critical' : 'warning',
            timestamp: new Date(),
          });
        }
      }
    } catch (e) {
      status.error = e instanceof Error ? e.message : String(e);
      alerts.push({
        providerId,
        type: 'error',
        message: `Failed to fetch ${collector.providerName} usage: ${status.error}`,
        severity: 'warning',
        timestamp: new Date(),
      });
    }
    
    providerStatuses.push(status);
  }
  
  const summary: DashboardSummary = {
    timestamp: new Date(),
    providers: providerStatuses,
    totalBalanceUsd: totalBalance,
    totalDailyCostUsd: totalDailyCost,
    alerts,
  };
  
  lastFetch = summary;
  return summary;
}

/**
 * Format summary as text for chat display
 */
function formatSummary(summary: DashboardSummary): string {
  const lines: string[] = ['📊 **Token Dashboard**\n'];
  
  if (summary.totalBalanceUsd !== undefined) {
    lines.push(`💰 **Total Balance:** $${summary.totalBalanceUsd.toFixed(2)}\n`);
  }
  
  lines.push('**Providers:**');
  
  for (const provider of summary.providers) {
    const icon = provider.isReachable ? '✅' : provider.isConfigured ? '⚠️' : '⬜';
    let line = `${icon} **${provider.name}**`;
    
    if (!provider.isConfigured) {
      line += ' (not configured)';
    } else if (provider.error) {
      line += ` — Error: ${provider.error}`;
    } else if (provider.currentUsage) {
      const usage = provider.currentUsage;
      const parts: string[] = [];
      
      if (usage.balanceUsd !== undefined) {
        parts.push(`Balance: $${usage.balanceUsd.toFixed(2)}`);
      }
      if (usage.inputTokens || usage.outputTokens) {
        parts.push(`Tokens: ${(usage.inputTokens + usage.outputTokens).toLocaleString()}`);
      }
      if (usage.costUsd) {
        parts.push(`Cost: $${usage.costUsd.toFixed(4)}`);
      }
      
      if (parts.length > 0) {
        line += ` — ${parts.join(' | ')}`;
      }
    }
    
    lines.push(line);
  }
  
  if (summary.alerts.length > 0) {
    lines.push('\n⚠️ **Alerts:**');
    for (const alert of summary.alerts) {
      const icon = alert.severity === 'critical' ? '🔴' : alert.severity === 'warning' ? '🟡' : 'ℹ️';
      lines.push(`${icon} ${alert.message}`);
    }
  }
  
  lines.push(`\n_Last updated: ${summary.timestamp.toISOString()}_`);
  
  return lines.join('\n');
}

/**
 * Plugin registration
 */
export default function register(api: PluginApi) {
  const logger = api.logger;
  
  logger.info('Token Dashboard plugin loading...');
  
  // Register /tokens chat command
  api.registerCommand({
    name: 'tokens',
    description: 'Show AI API token usage and balances across all providers',
    handler: async () => {
      try {
        const summary = await fetchAllUsage(api);
        return { text: formatSummary(summary) };
      } catch (e) {
        return { text: `❌ Error fetching token usage: ${e instanceof Error ? e.message : String(e)}` };
      }
    },
  });
  
  // Register /burn chat command (quick summary)
  api.registerCommand({
    name: 'burn',
    description: 'Show current burn rate summary',
    handler: async () => {
      const summary = lastFetch || await fetchAllUsage(api);
      
      const configured = summary.providers.filter(p => p.isConfigured);
      if (configured.length === 0) {
        return { text: '⬜ No providers configured. Set API keys in your OpenClaw config.' };
      }
      
      let text = '🔥 **Burn Rate Summary**\n\n';
      
      if (summary.totalBalanceUsd !== undefined) {
        text += `💰 Total Balance: **$${summary.totalBalanceUsd.toFixed(2)}**\n`;
      }
      
      const critical = summary.alerts.filter(a => a.severity === 'critical');
      if (critical.length > 0) {
        text += `\n🚨 ${critical.length} critical alert(s)!\n`;
      }
      
      return { text };
    },
  });
  
  // Register Gateway RPC methods
  api.registerGatewayMethod('token-dashboard.status', async ({ respond }) => {
    try {
      const summary = await fetchAllUsage(api);
      respond(true, summary);
    } catch (e) {
      respond(false, { error: e instanceof Error ? e.message : String(e) });
    }
  });
  
  api.registerGatewayMethod('token-dashboard.cached', ({ respond }) => {
    if (lastFetch) {
      respond(true, lastFetch);
    } else {
      respond(false, { error: 'No cached data available. Run /tokens first.' });
    }
  });
  
  api.registerGatewayMethod('token-dashboard.providers', ({ respond }) => {
    const providers = Object.entries(collectors).map(([id, collector]) => ({
      id,
      name: collector.providerName,
      isConfigured: collector.isConfigured(getCollectorConfig(api, id)),
    }));
    respond(true, { providers });
  });
  
  // Register CLI command
  api.registerCli(
    ({ program }) => {
      const tokensCmd = program
        .command('tokens')
        .description('Show AI API token usage and balances');
      
      tokensCmd
        .command('status')
        .description('Show current token usage across all providers')
        .action(async () => {
          try {
            const summary = await fetchAllUsage(api);
            console.log(formatSummary(summary));
          } catch (e) {
            console.error('Error:', e instanceof Error ? e.message : String(e));
            process.exit(1);
          }
        });
      
      tokensCmd
        .command('providers')
        .description('List configured providers')
        .action(() => {
          console.log('Configured providers:\n');
          for (const [id, collector] of Object.entries(collectors)) {
            const config = getCollectorConfig(api, id);
            const status = config.enabled ? '✅' : '⬜';
            console.log(`${status} ${collector.providerName} (${id})`);
          }
        });
    },
    { commands: ['tokens'] }
  );
  
  // Register background service for polling
  api.registerService({
    id: 'token-dashboard-poller',
    start: () => {
      const pluginConfig = api.config.plugins?.entries?.['token-dashboard']?.config as TokenDashboardConfig | undefined;
      const intervalMinutes = pluginConfig?.pollIntervalMinutes || 15;
      
      logger.info(`Token Dashboard poller starting (interval: ${intervalMinutes}m)`);
      
      // Initial fetch
      fetchAllUsage(api).catch(e => {
        logger.warn('Initial token fetch failed:', e);
      });
      
      // Set up polling
      pollInterval = setInterval(() => {
        fetchAllUsage(api).catch(e => {
          logger.warn('Token fetch failed:', e);
        });
      }, intervalMinutes * 60 * 1000);
    },
    stop: () => {
      if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
      }
      logger.info('Token Dashboard poller stopped');
    },
  });
  
  // Register agent tool
  api.registerTool({
    name: 'token_usage',
    description: 'Get current AI API token usage and balances across all providers',
    parameters: {
      type: 'object',
      properties: {
        provider: {
          type: 'string',
          description: 'Specific provider to check (optional, default: all)',
          enum: ['openai', 'anthropic', 'moonshot', 'openrouter'],
        },
        refresh: {
          type: 'boolean',
          description: 'Force refresh from APIs (default: use cached data)',
        },
      },
    },
    handler: async ({ provider, refresh }) => {
      if (refresh || !lastFetch) {
        await fetchAllUsage(api);
      }
      
      if (provider && lastFetch) {
        const providerStatus = lastFetch.providers.find(p => p.providerId === provider);
        if (!providerStatus) {
          return { error: `Provider '${provider}' not found` };
        }
        return providerStatus;
      }
      
      return lastFetch;
    },
  });
  
  logger.info('Token Dashboard plugin loaded successfully');
}

// Export plugin metadata
export const id = 'token-dashboard';
export const name = 'Token Dashboard';
