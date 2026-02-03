/**
 * Base Collector Interface
 */

import type { ProviderUsage, CollectorConfig } from '../types.js';

export interface Collector {
  providerId: string;
  providerName: string;
  
  /**
   * Check if this collector is configured (has required credentials)
   */
  isConfigured(config: CollectorConfig): boolean;
  
  /**
   * Fetch current usage and balance from the provider
   */
  fetchUsage(config: CollectorConfig): Promise<ProviderUsage>;
  
  /**
   * Optional: Test connectivity to the provider
   */
  testConnection?(config: CollectorConfig): Promise<boolean>;
}

export abstract class BaseCollector implements Collector {
  abstract providerId: string;
  abstract providerName: string;
  
  abstract isConfigured(config: CollectorConfig): boolean;
  abstract fetchUsage(config: CollectorConfig): Promise<ProviderUsage>;
  
  async testConnection(config: CollectorConfig): Promise<boolean> {
    try {
      await this.fetchUsage(config);
      return true;
    } catch {
      return false;
    }
  }
  
  protected async httpGet<T>(url: string, headers: Record<string, string>): Promise<T> {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return response.json() as Promise<T>;
  }
}
