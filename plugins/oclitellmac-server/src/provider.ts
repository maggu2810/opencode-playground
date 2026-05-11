import type { ModelHubEntry, ModelInfoEntry } from "./fetcher"

/**
 * Build a complete model configuration from LiteLLM data
 * 
 * Adapts the approach from tools/config-generator/src/generate.py
 */
export function buildModel(
  hub: ModelHubEntry,
  info: ModelInfoEntry["model_info"] | undefined,
  providerKey: string
): any {
  const modelId = hub.model_group
  
  // Map capabilities
  const toolCall = !!(
    hub.supports_function_calling ||
    hub.supports_parallel_function_calling ||
    info?.supports_function_calling
  )
  const attachment = !!(hub.supports_vision || info?.supports_vision)
  const reasoning = !!(hub.supports_reasoning || info?.supports_reasoning)
  
  // Map modalities
  const inputModalities: string[] = ["text"]
  const outputModalities: string[] = ["text"]
  
  if (attachment) inputModalities.push("image")
  if (info?.supports_audio_input) inputModalities.push("audio")
  if (info?.supports_pdf_input) inputModalities.push("pdf")
  if (info?.supports_audio_output) outputModalities.push("audio")
  
  // Map cost (use first available value)
  const inputCost = info?.input_cost_per_token ?? hub.input_cost_per_token ?? 0
  const outputCost = info?.output_cost_per_token ?? hub.output_cost_per_token ?? 0
  
  const cost: any = { input: inputCost, output: outputCost }
  
  // Cache costs (optional, from /v1/model/info only)
  const cacheRead = info?.cache_read_input_token_cost ?? hub.cache_read_input_token_cost
  const cacheWrite = info?.cache_creation_input_token_cost ?? hub.cache_creation_input_token_cost
  
  if (cacheRead !== undefined || cacheWrite !== undefined) {
    cost.cache = {
      read: cacheRead ?? 0,
      write: cacheWrite ?? 0,
    }
  }
  
  // Extended context costs (check both field names)
  const inputOver = 
    info?.input_cost_per_token_above_128k_tokens ??
    hub.input_cost_per_token_above_200k_tokens ??
    hub.input_cost_per_token_above_128k_tokens
  const outputOver = 
    info?.output_cost_per_token_above_128k_tokens ??
    hub.output_cost_per_token_above_200k_tokens ??
    hub.output_cost_per_token_above_128k_tokens
  
  if (inputOver !== undefined && outputOver !== undefined) {
    cost.context_over_200k = {
      input: inputOver,
      output: outputOver,
    }
  }
  
  // Map limits
  const maxContext = info?.max_input_tokens ?? hub.max_input_tokens
  const maxOutput = info?.max_output_tokens ?? hub.max_output_tokens
  
  // Build model config
  const model: any = {
    id: modelId,
    name: modelId,
  }
  
  // Only add capability flags if true (keep config clean)
  if (toolCall) model.tool_call = true
  if (attachment) model.attachment = true
  if (reasoning) model.reasoning = true
  model.temperature = true // All chat models support temperature
  
  // Modalities
  model.modalities = {
    input: inputModalities,
    output: outputModalities,
  }
  
  // Cost (always present, even if zero)
  model.cost = cost
  
  // Limits (only if both context and output are available)
  if (maxContext && maxOutput) {
    model.limit = {
      context: maxContext,
      input: maxContext,
      output: maxOutput,
    }
  }
  
  return model
}

/**
 * Build models map from LiteLLM endpoints
 */
export function buildModels(
  hubEntries: ModelHubEntry[],
  infoMap: Record<string, ModelInfoEntry["model_info"]>,
  providerKey: string
): Record<string, any> {
  const models: Record<string, any> = {}
  
  for (const hubEntry of hubEntries) {
    const modelId = hubEntry.model_group
    if (!modelId) continue
    
    const info = infoMap[modelId]
    models[modelId] = buildModel(hubEntry, info, providerKey)
  }
  
  return models
}
