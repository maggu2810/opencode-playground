/** @jsxImportSource @opentui/solid */
import { createMemo } from "solid-js"
import type { TuiPluginModule, TuiSlotContext } from "@opencode-ai/plugin"
import type { Provider, Model } from "@opencode-ai/sdk/v2"

type ProviderDisplayInfo = {
  id: string
  name: string
  source: string
  hasApiKey: boolean
  envVars: string[]
  modelCount: number
  models: Array<{
    id: string
    name: string
    status: string
    capabilities: {
      reasoning: boolean
      toolcall: boolean
      inputTypes: string[]
      outputTypes: string[]
    }
    limits: { context?: number; output?: number }
    cost: { input: number; output: number }
  }>
  options: Record<string, unknown>
}

function formatCapabilityList(capabilities: ProviderDisplayInfo["models"][0]["capabilities"]): string[] {
  const result: string[] = []
  if (capabilities.reasoning) result.push("reasoning")
  if (capabilities.toolcall) result.push("tool_calls")
  if (capabilities.inputTypes.length > 0) result.push(...capabilities.inputTypes)
  if (capabilities.outputTypes.length > 0) result.push(...capabilities.outputTypes)
  return result
}

function transformProvider(provider: Provider): ProviderDisplayInfo {
  const models = Object.values(provider.models)
  return {
    id: provider.id,
    name: provider.name,
    source: provider.source,
    hasApiKey: !!provider.key,
    envVars: provider.env,
    modelCount: Object.keys(provider.models).length,
    models: models.map((m: Model) => ({
      id: m.id,
      name: m.name,
      status: m.status,
      capabilities: {
        reasoning: m.capabilities.reasoning,
        toolcall: m.capabilities.toolcall,
        inputTypes: Object.entries(m.capabilities.input)
          .filter(([, v]) => v)
          .map(([k]) => k),
        outputTypes: Object.entries(m.capabilities.output)
          .filter(([, v]) => v)
          .map(([k]) => k),
      },
      limits: { context: m.limit?.context, output: m.limit?.output },
      cost: { input: m.cost?.input ?? 0, output: m.cost?.output ?? 0 },
    })),
    options: provider.options,
  }
}

function ProviderCard(props: { ctx: TuiSlotContext; provider: ProviderDisplayInfo }) {
  const p = props.provider
  const theme = () => props.ctx.theme.current

  return (
    <box
      flexDirection="column"
      gap={1}
      padding={1}
      marginBottom={1}
      borderStyle="round"
      borderColor={theme().border}
    >
      <text fg={theme().text}>
        <b>{p.name}</b>
      </text>
      <text fg={theme().textMuted}>ID: {p.id}</text>
      <text fg={theme().textMuted}>Source: {p.source}</text>
      <text fg={theme().textMuted}>API Key: {p.hasApiKey ? "Configured" : "Not configured"}</text>
      <text fg={theme().textMuted}>Models: {p.modelCount}</text>

      {p.envVars.length > 0 && (
        <box flexDirection="column" gap={0} marginTop={1}>
          <text fg={theme().textMuted}>Env Vars:</text>
          {p.envVars.map((env) => (
            <text fg={theme().textMuted} marginLeft={2}>
              {env}
            </text>
          ))}
        </box>
      )}

      {p.models.length > 0 && (
        <box flexDirection="column" gap={0} marginTop={1}>
          <text fg={theme().text}>
            <b>Available Models:</b>
          </text>
          {p.models.map((model) => (
            <box flexDirection="column" gap={0} marginTop={1} marginLeft={2}>
              <text fg={theme().text}>
                <b>{model.name}</b>
              </text>
              <text fg={theme().textMuted}>ID: {model.id}</text>
              <text fg={theme().textMuted}>Status: {model.status}</text>
              <text fg={theme().textMuted}>
                Capabilities: {formatCapabilityList(model.capabilities).join(", ") || "none"}
              </text>
              {model.limits.context && (
                <text fg={theme().textMuted}>
                  Context: {model.limits.context.toLocaleString()} tokens
                </text>
              )}
              {model.limits.output && (
                <text fg={theme().textMuted}>
                  Output limit: {model.limits.output.toLocaleString()} tokens
                </text>
              )}
              {(model.cost.input > 0 || model.cost.output > 0) && (
                <text fg={theme().textMuted}>
                  Cost: ${model.cost.input}/1M in, ${model.cost.output}/1M out
                </text>
              )}
            </box>
          ))}
        </box>
      )}

      {Object.keys(p.options).length > 0 && (
        <box flexDirection="column" gap={0} marginTop={1}>
          <text fg={theme().text}>
            <b>Options:</b>
          </text>
          <text fg={theme().textMuted}>{JSON.stringify(p.options)}</text>
        </box>
      )}
    </box>
  )
}

export const plugin: TuiPluginModule = {
  id: "tui-playground-v1",
  tui: async (api, _options, _meta) => {
    const dispose = api.slots.register({
      id: "tui-playground-v1-sidebar",
      order: 100,
      slots: {
        sidebar_content: (ctx, _props) => {
          const providers = createMemo(() =>
            api.state.provider.map(transformProvider)
          )

          return (
            <box flexDirection="column" gap={1}>
              <text fg={ctx.theme.current.text}>
                <b size={2}>Provider Info</b>
              </text>

              {providers().length === 0 ? (
                <text fg={ctx.theme.current.textMuted}>No providers configured</text>
              ) : (
                providers().map((p) => (
                  <ProviderCard ctx={ctx} provider={p} />
                ))
              )}
            </box>
          )
        },
      },
    })

    api.lifecycle.onDispose(dispose)
  },
}

export default plugin