/**
 * OpenRouter Usage Collector
 * 
 * OpenRouter has a well-documented API for checking credits and usage.
 * Endpoint: GET https://openrouter.ai/api/v1/credits
 */

import { BaseCollector } from './base.js';
import type { ProviderUsage, CollectorConfig } from '../types.js';

interface OpenRouterCreditsResponse {
  data: {
    label: string;
    usage: number;           // Total credits used
    limit: number | null;    // Credit limit (null = unlimited)
    is_free_tier: boolean;
    rate_limit: {
      requests: number;
      interval: string;
    };
  };
}

interface OpenRouterUsageResponse {
  data: Array<{
    id: string;
    model: string;
    streamed: boolean;
    generation_time: number;
    created_at: string;
    tokens_prompt: number;
    tokens_completion: number;
    native_tokens_prompt: number;
    native_tokens_completion: number;
    num_media_prompt: number | null;
    num_media_completion: number | null;
    origin: string;
    total_cost: number;
  }>;
}

export class OpenRouterCollector extends BaseCollector {
  providerId = 'openrouter';
  providerName = 'OpenRouter';
  
  private baseUrl = 'https://openrouter.ai/api/v1';
  
  isConfigured(config: CollectorConfig): boolean {
    return !!config.apiKey;
  }
  
  async fetchUsage(config: CollectorConfig): Promise<ProviderUsage> {
    if (!config.apiKey) {
      throw new Error('OpenRouter API key not configured');
    }
    
    const headers = {
      'Authorization': `Bearer ${config.apiKey}`,
    };
    
    const now = new Date();
    
    // Fetch credits/balance
    const creditsData = await this.httpGet<OpenRouterCreditsResponse>(
      `${this.baseUrl}/credits`,
      headers
    );
    
    // Fetch recent usage (activity endpoint)
    let usageData: OpenRouterUsageResponse | null = null;
    try {
      // OpenRouter's activity endpoint - may require pagination for full history
      usageData = await this.httpGet<OpenRouterUsageResponse>(
        `${this.baseUrl}/activity?limit=100`,
        headers
      );
    } catch (e) {
      console.warn('OpenRouter activity endpoint not available:', e);
    }
    
    // Calculate totals from usage data
    let inputTokens = 0;
    let outputTokens = 0;
    let totalCost = 0;
    
    if (usageData?.data) {
      for (const entry of usageData.data) {
        inputTokens += entry.tokens_prompt || 0;
        outputTokens += entry.tokens_completion || 0;
        totalCost += entry.total_cost || 0;
      }
    }
    
    // Calculate remaining balance
    const balance = creditsData.data.limit !== null
      ? creditsData.data.limit - creditsData.data.usage
      : undefined;
    
    return {
      providerId: this.providerId,
      timestamp: now,
      inputTokens,
      outputTokens,
      costUsd: totalCost,
      balanceUsd: balance,
      creditLimitUsd: creditsData.data.limit ?? undefined,
      raw: { creditsData, usageData },
    };
  }
}
