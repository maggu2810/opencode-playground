import { readdir, readFile } from 'fs/promises'
import { homedir } from 'os'
import path from 'path'
import type { KeyInfoFile, ProviderBudget, BudgetData } from './types'

/**
 * Budget data loader - reads budget files from ~/.local/state/oclitellmac/key-info/
 */
export class BudgetLoader {
  private stateDir: string

  constructor() {
    this.stateDir = path.join(homedir(), '.local', 'state', 'oclitellmac')
  }

  /**
   * Get the state directory path
   */
  getStateDir(): string {
    return this.stateDir
  }

  /**
   * Load all budget files from key-info directory
   */
  async loadAll(): Promise<BudgetData> {
    const keyInfoDir = path.join(this.stateDir, 'key-info')
    const budgets: BudgetData = {}

    try {
      const files = await readdir(keyInfoDir)

      for (const file of files) {
        if (!file.endsWith('.json')) continue

        const providerKey = file.replace('.json', '')
        const budget = await this.loadOne(providerKey)

        if (budget) {
          budgets[providerKey] = budget
        }
      }
    } catch (error) {
      // Directory doesn't exist yet or is inaccessible - return empty
    }

    return budgets
  }

  /**
   * Load budget data for a single provider
   */
  async loadOne(providerKey: string): Promise<ProviderBudget | null> {
    const filePath = path.join(this.stateDir, 'key-info', `${providerKey}.json`)

    try {
      const content = await readFile(filePath, 'utf-8')
      const data = JSON.parse(content) as KeyInfoFile

      // Validate required fields
      if (
        !data.keyInfo ||
        typeof data.keyInfo.spend !== 'number' ||
        typeof data.keyInfo.max_budget !== 'number'
      ) {
        return null
      }

      // Transform to normalized format
      return {
        providerKey: data.providerKey,
        providerName: this.formatProviderName(data.providerKey),
        keyAlias: data.keyInfo.key_alias,
        spend: data.keyInfo.spend,
        limit: data.keyInfo.max_budget,
        remaining: data.keyInfo.max_budget - data.keyInfo.spend,
        percentUsed: (data.keyInfo.spend / data.keyInfo.max_budget) * 100,
        duration: data.keyInfo.budget_duration,
        resetAt: data.keyInfo.budget_reset_at,
        expiresAt: data.keyInfo.expires,
        lastFetched: data.fetchedAt,
      }
    } catch (error) {
      // File doesn't exist, invalid JSON, or missing fields
      return null
    }
  }

  /**
   * Format provider key to display name
   * e.g., "litellm-prod" -> "LiteLLM Prod"
   */
  private formatProviderName(key: string): string {
    return key
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  }
}
