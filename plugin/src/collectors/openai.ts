/**
 * OpenAI Usage Collector
 * 
 * Uses the OpenAI billing/usage API to fetch usage and balance data.
 * Note: Requires an API key with billing access.
 */

import { BaseCollector } from './base.js';
import type { ProviderUsage, CollectorConfig } from '../types.js';

interface OpenAIUsageResponse {
  object: string;
  data: Array<{
    aggregation_timestamp: number;
    n_requests: number;
    operation: string;
    snapshot_id: string;
    n_context_tokens_total: number;
    n_generated_tokens_total: number;
  }>;
  ft_data: unknown[];
  dalle_api_data: unknown[];
  whisper_api_data: unknown[];
  tts_api_data: unknown[];
  assistant_code_interpreter_data: unknown[];
  retrieval_storage_data: unknown[];
}

interface OpenAISubscriptionResponse {
  object: string;
  has_payment_method: boolean;
  canceled: boolean;
  canceled_at: number | null;
  delinquent: boolean | null;
  access_until: number;
  soft_limit: number;
  hard_limit: number;
  system_hard_limit: number;
  soft_limit_usd: number;
  hard_limit_usd: number;
  system_hard_limit_usd: number;
  plan: {
    title: string;
    id: string;
  };
  account_name: string;
  po_number: string | null;
  billing_email: string | null;
  tax_ids: unknown[] | null;
  billing_address: unknown | null;
  business_address: unknown | null;
}

interface OpenAICreditGrantsResponse {
  object: string;
  data: Array<{
    id: string;
    grant_amount: number;
    used_amount: number;
    effective_at: number;
    expires_at: number;
  }>;
}

export class OpenAICollector extends BaseCollector {
  providerId = 'openai';
  providerName = 'OpenAI';
  
  private baseUrl = 'https://api.openai.com';
  
  isConfigured(config: CollectorConfig): boolean {
    return !!config.apiKey;
  }
  
  async fetchUsage(config: CollectorConfig): Promise<ProviderUsage> {
    if (!config.apiKey) {
      throw new Error('OpenAI API key not configured');
    }
    
    const headers = {
      'Authorization': `Bearer ${config.apiKey}`,
    };
    
    // Get date range for today
    const now = new Date();
    const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
    const endDate = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    
    // Fetch usage data
    const usageUrl = `${this.baseUrl}/v1/dashboard/billing/usage?start_date=${this.formatDate(startDate)}&end_date=${this.formatDate(endDate)}`;
    
    let usageData: OpenAIUsageResponse | null = null;
    let subscriptionData: OpenAISubscriptionResponse | null = null;
    let creditsData: OpenAICreditGrantsResponse | null = null;
    
    try {
      usageData = await this.httpGet<OpenAIUsageResponse>(usageUrl, headers);
    } catch (e) {
      // Usage endpoint may not be available for all account types
      console.warn('OpenAI usage endpoint not available:', e);
    }
    
    // Fetch subscription/balance data
    try {
      subscriptionData = await this.httpGet<OpenAISubscriptionResponse>(
        `${this.baseUrl}/v1/dashboard/billing/subscription`,
        headers
      );
    } catch (e) {
      console.warn('OpenAI subscription endpoint not available:', e);
    }
    
    // Fetch credit grants (for prepaid credits)
    try {
      creditsData = await this.httpGet<OpenAICreditGrantsResponse>(
        `${this.baseUrl}/v1/dashboard/billing/credit_grants`,
        headers
      );
    } catch (e) {
      console.warn('OpenAI credit grants endpoint not available:', e);
    }
    
    // Calculate totals
    let inputTokens = 0;
    let outputTokens = 0;
    let totalCost = 0;
    
    if (usageData?.data) {
      for (const entry of usageData.data) {
        inputTokens += entry.n_context_tokens_total || 0;
        outputTokens += entry.n_generated_tokens_total || 0;
      }
      // Note: The usage API returns cost in cents, need to convert
      // This is a rough estimate - actual API returns total_usage in cents
    }
    
    // Calculate remaining balance from credits
    let balance: number | undefined;
    if (creditsData?.data) {
      balance = creditsData.data.reduce((sum, grant) => {
        const remaining = grant.grant_amount - grant.used_amount;
        return sum + remaining;
      }, 0);
    }
    
    return {
      providerId: this.providerId,
      timestamp: now,
      inputTokens,
      outputTokens,
      costUsd: totalCost / 100, // Convert cents to dollars
      balanceUsd: balance,
      creditLimitUsd: subscriptionData?.hard_limit_usd,
      raw: { usageData, subscriptionData, creditsData },
    };
  }
  
  private formatDate(date: Date): string {
    return date.toISOString().split('T')[0];
  }
}
