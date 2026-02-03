/**
 * Moonshot (Kimi) Usage Collector
 * 
 * Moonshot uses an OpenAI-compatible API at api.moonshot.ai (international)
 * or api.moonshot.cn (China). They may have usage/billing endpoints similar
 * to OpenAI, or may require checking their platform console.
 */

import { BaseCollector } from './base.js';
import type { ProviderUsage, CollectorConfig } from '../types.js';

interface MoonshotBalanceResponse {
  // Moonshot's API response structure (TBD - needs research)
  available_balance?: number;
  total_balance?: number;
  used_balance?: number;
  currency?: string;
}

interface MoonshotUsageResponse {
  data?: Array<{
    date: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost?: number;
  }>;
}

export class MoonshotCollector extends BaseCollector {
  providerId = 'moonshot';
  providerName = 'Moonshot (Kimi)';
  
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
    
    // Try OpenAI-compatible billing endpoints first
    let balanceData: MoonshotBalanceResponse | null = null;
    let usageData: MoonshotUsageResponse | null = null;
    
    // Try /v1/users/me/balance (common endpoint pattern)
    try {
      balanceData = await this.httpGet<MoonshotBalanceResponse>(
        `${baseUrl}/users/me/balance`,
        headers
      );
    } catch (e) {
      console.warn('Moonshot balance endpoint not available:', e);
    }
    
    // Try OpenAI-style billing endpoint
    if (!balanceData) {
      try {
        balanceData = await this.httpGet<MoonshotBalanceResponse>(
          `${baseUrl}/dashboard/billing/subscription`,
          headers
        );
      } catch (e) {
        console.warn('Moonshot subscription endpoint not available:', e);
      }
    }
    
    // Try usage endpoint
    try {
      const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
      usageData = await this.httpGet<MoonshotUsageResponse>(
        `${baseUrl}/dashboard/billing/usage?start_date=${this.formatDate(startDate)}&end_date=${this.formatDate(now)}`,
        headers
      );
    } catch (e) {
      console.warn('Moonshot usage endpoint not available:', e);
    }
    
    // Calculate totals from usage data
    let inputTokens = 0;
    let outputTokens = 0;
    let totalCost = 0;
    
    if (usageData?.data) {
      for (const entry of usageData.data) {
        inputTokens += entry.input_tokens || 0;
        outputTokens += entry.output_tokens || 0;
        totalCost += entry.cost || 0;
      }
    }
    
    return {
      providerId: this.providerId,
      timestamp: now,
      inputTokens,
      outputTokens,
      costUsd: totalCost,
      balanceUsd: balanceData?.available_balance,
      raw: { balanceData, usageData },
    };
  }
  
  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }
}
