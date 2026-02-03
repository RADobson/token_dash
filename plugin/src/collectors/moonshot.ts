/**
 * Moonshot (Kimi) Usage Collector
 * 
 * Moonshot uses an OpenAI-compatible API at api.moonshot.ai (international)
 * or api.moonshot.cn (China).
 * 
 * Verified endpoints:
 * - GET /v1/users/me/balance → returns available_balance, voucher_balance, cash_balance
 * - No usage/history endpoint available via API (must use console)
 */

import { BaseCollector } from './base.js';
import type { ProviderUsage, CollectorConfig } from '../types.js';

interface MoonshotBalanceResponse {
  code: number;
  status: boolean;
  data: {
    available_balance: number;  // Total available (voucher + cash)
    voucher_balance: number;    // Promotional credits
    cash_balance: number;       // Paid credits
  };
}

export class MoonshotCollector extends BaseCollector {
  providerId = 'moonshot';
  providerName = 'Moonshot (Kimi K2.5)';
  
  private baseUrls = {
    international: 'https://api.moonshot.ai/v1',
    china: 'https://api.moonshot.cn/v1',
  };
  
  isConfigured(config: CollectorConfig): boolean {
    return !!config.apiKey;
  }
  
  async fetchUsage(config: CollectorConfig): Promise<ProviderUsage> {
    if (!config.apiKey) {
      throw new Error('Moonshot API key not configured');
    }
    
    // Determine which endpoint to use
    const baseUrl = config.baseUrl || this.baseUrls.international;
    
    const headers = {
      'Authorization': `Bearer ${config.apiKey}`,
    };
    
    const now = new Date();
    
    // Fetch balance from verified endpoint
    const response = await this.httpGet<MoonshotBalanceResponse>(
      `${baseUrl}/users/me/balance`,
      headers
    );
    
    if (!response.status || response.code !== 0) {
      throw new Error(`Moonshot API error: ${JSON.stringify(response)}`);
    }
    
    const { available_balance, voucher_balance, cash_balance } = response.data;
    
    return {
      providerId: this.providerId,
      timestamp: now,
      // No usage history available via API
      inputTokens: 0,
      outputTokens: 0,
      costUsd: 0,
      // Balance info
      balanceUsd: available_balance,
      raw: {
        available_balance,
        voucher_balance,
        cash_balance,
      },
    };
  }
}
