/**
 * Anthropic Usage Collector
 * 
 * Fetches usage data from Anthropic's API.
 * Note: Anthropic's usage API may require admin keys.
 */

import { BaseCollector } from './base.js';
import type { ProviderUsage, CollectorConfig } from '../types.js';

interface AnthropicUsageResponse {
  data: Array<{
    date: string;
    workspace_id: string;
    input_tokens: number;
    output_tokens: number;
    cache_creation_input_tokens: number;
    cache_read_input_tokens: number;
    cost_usd: number;
  }>;
}

export class AnthropicCollector extends BaseCollector {
  providerId = 'anthropic';
  providerName = 'Anthropic';
  
  private baseUrl = 'https://api.anthropic.com';
  
  isConfigured(config: CollectorConfig): boolean {
    return !!config.apiKey;
  }
  
  async fetchUsage(config: CollectorConfig): Promise<ProviderUsage> {
    if (!config.apiKey) {
      throw new Error('Anthropic API key not configured');
    }
    
    const headers = {
      'x-api-key': config.apiKey,
      'anthropic-version': '2023-06-01',
    };
    
    const now = new Date();
    
    // Try to fetch usage data
    // Note: The exact endpoint may vary - Anthropic's admin API is not fully documented
    let usageData: AnthropicUsageResponse | null = null;
    
    try {
      // This is the documented usage endpoint for workspaces
      const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
      const endDate = now;
      
      usageData = await this.httpGet<AnthropicUsageResponse>(
        `${this.baseUrl}/v1/usage?start_date=${this.formatDate(startDate)}&end_date=${this.formatDate(endDate)}`,
        headers
      );
    } catch (e) {
      // Usage endpoint requires admin access
      console.warn('Anthropic usage endpoint not available (may require admin key):', e);
    }
    
    // Calculate totals
    let inputTokens = 0;
    let outputTokens = 0;
    let cacheReadTokens = 0;
    let cacheWriteTokens = 0;
    let totalCost = 0;
    
    if (usageData?.data) {
      for (const entry of usageData.data) {
        inputTokens += entry.input_tokens || 0;
        outputTokens += entry.output_tokens || 0;
        cacheReadTokens += entry.cache_read_input_tokens || 0;
        cacheWriteTokens += entry.cache_creation_input_tokens || 0;
        totalCost += entry.cost_usd || 0;
      }
    }
    
    return {
      providerId: this.providerId,
      timestamp: now,
      inputTokens,
      outputTokens,
      cacheReadTokens,
      cacheWriteTokens,
      costUsd: totalCost,
      raw: usageData,
    };
  }
  
  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }
}
