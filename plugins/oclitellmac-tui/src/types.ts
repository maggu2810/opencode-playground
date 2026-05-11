/** @jsxImportSource @opentui/solid */

/**
 * Raw structure from ~/.local/state/oclitellmac/key-info/<provider>.json
 * 
 * This matches the LiteLLM /key/info endpoint response structure.
 */
export interface KeyInfoFile {
  providerKey: string
  fetchedAt: number
  keyInfo: {
    key_alias: string
    spend: number
    max_budget: number
    budget_duration: string
    budget_reset_at: string
    expires: string
  }
}

/**
 * Normalized budget data for UI display
 */
export interface ProviderBudget {
  providerKey: string
  providerName: string
  keyAlias: string
  spend: number
  limit: number
  remaining: number
  percentUsed: number
  duration: string
  resetAt: string
  expiresAt: string
  lastFetched: number
}

/**
 * All providers budget data (keyed by provider key)
 */
export type BudgetData = Record<string, ProviderBudget>
