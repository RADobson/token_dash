/**
 * Token Dashboard - Shared Types
 */

export interface ProviderUsage {
  providerId: string;
  timestamp: Date;
  
  // Token counts
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens?: number;
  cacheWriteTokens?: number;
  
  // Cost in USD
  costUsd: number;
  
  // Balance info (if available from provider)
  balanceUsd?: number;
  creditLimitUsd?: number;
  
  // Raw response for debugging
  raw?: unknown;
}

export interface BurnRate {
  providerId: string;
  
  // Tokens per period
  tokensPerHour: number;
  tokensPerDay: number;
  
  // Cost per period (USD)
  costPerHour: number;
  costPerDay: number;
  
  // Runway estimation
  runwayHours?: number;
  runwayDays?: number;
}

export interface ProviderStatus {
  providerId: string;
  name: string;
  
  // Current state
  isConfigured: boolean;
  isReachable: boolean;
  lastChecked?: Date;
  error?: string;
  
  // Usage data
  currentUsage?: ProviderUsage;
  burnRate?: BurnRate;
}

export interface DashboardSummary {
  timestamp: Date;
  providers: ProviderStatus[];
  
  // Aggregates
  totalBalanceUsd?: number;
  totalDailyCostUsd: number;
  totalRunwayDays?: number;
  
  // Alerts
  alerts: UsageAlert[];
}

export interface UsageAlert {
  providerId: string;
  type: 'low_balance' | 'high_spend' | 'error';
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: Date;
}

export interface CollectorConfig {
  apiKey?: string;
  baseUrl?: string;
  enabled: boolean;
}

export interface TokenDashboardConfig {
  pollIntervalMinutes: number;
  historyRetentionDays: number;
  alertThresholds: Record<string, {
    balanceUsd?: number;
    dailySpendUsd?: number;
  }>;
  enabledProviders: string[];
}
