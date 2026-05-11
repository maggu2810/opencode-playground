import type { PluginInput, Hooks } from "@opencode-ai/plugin"
import { loadConfig, getConfigPath } from "./config"
import { LiteLLMClient } from "./fetch"
import { transformModels } from "./transform"
import { buildBlacklist } from "./filter"
import { NON_CHAT_CATEGORIES, CATEGORY_LABEL, type Category } from "./categorize"
import { StateManager } from "./state"
import { BudgetTracker } from "./budget"

/**
 * Format provider key into display name
 * Examples: "litellm-prod" → "Litellm Prod", "my-proxy" → "My Proxy"
 */
function formatProviderName(key: string): string {
  return key
    .split('-')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

/**
 * oclitellmac-server plugin
 * 
 * Automatically configures multiple LiteLLM proxy endpoints as OpenCode providers.
 * No manual opencode.json editing required.
 */
export default async function plugin(input: PluginInput): Promise<Hooks> {
  // Logger helper
  const log = (message: string) => {
    input.client.app.log({
      body: {
        service: "oclitellmac-server",
        level: "info",
        message,
      },
    }).catch(() => {})
  }
  
  // Initialize state manager
  const stateManager = new StateManager()
  await stateManager.ensureDirectories()
  
  // Load configuration
  let config
  try {
    config = await loadConfig()
    log(`Loaded configuration from ${getConfigPath()}`)
  } catch (error) {
    log(`Failed to load config: ${error instanceof Error ? error.message : String(error)}`)
    log(`Please create ${getConfigPath()} with your LiteLLM endpoint configuration`)
    return {} // Return empty hooks if config missing
  }
  
  const { budgetPollInterval, fallbackToCache, timeout } = config.options
  
  // Initialize budget tracker
  const budgetTracker = new BudgetTracker(stateManager, budgetPollInterval, log)
  
  // Track clients for budget fetching
  const clientMap = new Map<string, LiteLLMClient>()
  
  return {
    /**
     * Config hook: Inject all providers dynamically
     */
    config: async (opcodeConfig) => {
      log("Config hook: Injecting providers...")
      
      opcodeConfig.provider ??= {}
      let successCount = 0
      let cacheCount = 0
      
      for (const endpoint of config.endpoints) {
        if (!endpoint.enabled) {
          log(`Skipping disabled endpoint: ${endpoint.providerKey}`)
          continue
        }
        
        const client = new LiteLLMClient(endpoint.baseUrl, endpoint.apiKey, timeout)
        clientMap.set(endpoint.providerKey, client)
        
        let models: Record<string, any> = {}
        let categories: Map<string, Category> = new Map()
        let usedCache = false
        
        try {
          log(`Fetching models for ${endpoint.providerKey} from ${endpoint.baseUrl}...`)
          
          const [hubEntries, infoMap] = await Promise.all([
            client.fetchModelHub(),
            client.fetchModelInfo(),
          ])
          
          // Transform using new modular pipeline
          const result = transformModels(hubEntries, infoMap)
          models = result.models
          categories = result.categories
          
          // Cache the fetched data
          await stateManager.saveProviderCache(endpoint.providerKey, {
            providerKey: endpoint.providerKey,
            baseUrl: endpoint.baseUrl,
            fetchedAt: Date.now(),
            models,
            categories: Object.fromEntries(categories),
          })
          
          log(`Loaded ${Object.keys(models).length} models for ${endpoint.providerKey}`)
          successCount++
          
        } catch (error) {
          log(
            `Failed to fetch models for ${endpoint.providerKey}: ${error instanceof Error ? error.message : String(error)}`
          )
          
          // Fallback to cache if enabled
          if (fallbackToCache) {
            const cached = await stateManager.loadProviderCache(endpoint.providerKey)
            if (cached && cached.models) {
              models = cached.models
              // Restore categories from cache
              if (cached.categories) {
                categories = new Map(Object.entries(cached.categories))
              }
              usedCache = true
              cacheCount++
              log(
                `Using cached data for ${endpoint.providerKey} (cached at: ${new Date(cached.fetchedAt).toISOString()})`
              )
            } else {
              log(`No cached data available for ${endpoint.providerKey}`)
              continue // Skip this provider
            }
          } else {
            continue // Skip this provider
          }
        }
        
        // Build blacklist for non-chat models (TODO: make configurable via enabledCategories)
        const enabledCategories = new Set<Category>() // Empty = only chat models enabled
        const blacklist = buildBlacklist(categories, enabledCategories)
        
        // Inject provider into OpenCode config
        const providerConfig: any = {
          npm: "@ai-sdk/openai-compatible",
          name: endpoint.providerName ?? formatProviderName(endpoint.providerKey),
          key: endpoint.apiKey, // Add key field for TUI compatibility
          options: {
            baseURL: `${endpoint.baseUrl.replace(/\/v1\/?$/, "").replace(/\/$/, "")}/v1`,
            apiKey: endpoint.apiKey,
            litellmProxy: true,
          },
          models,
        }
        
        // Add blacklist if non-empty
        if (blacklist.length > 0) {
          providerConfig.blacklist = blacklist.map(([modelId]) => modelId)
          log(`Blacklisted ${blacklist.length} non-chat models for ${endpoint.providerKey}`)
        }
        
        opcodeConfig.provider[endpoint.providerKey] = providerConfig
        
        // Start budget tracking
        budgetTracker.startTracking(endpoint.providerKey, client)
      }
      
      log(
        `Provider injection complete: ${successCount} fresh, ${cacheCount} cached, ${config.endpoints.length - successCount - cacheCount} failed`
      )
    },
    
    /**
     * Chat message hook: Fetch budget after each message
     */
    "chat.message": async (input, output) => {
      // Trigger budget fetch for all active providers
      // Fire-and-forget to avoid blocking message processing
      for (const [providerKey, client] of clientMap) {
        budgetTracker.fetchAndStore(providerKey, client).catch(() => {
          // Errors already logged in fetchAndStore
        })
      }
    },
  }
}
