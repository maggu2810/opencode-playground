/** @jsxImportSource @opentui/solid */
import type { TuiPluginApi } from '@opencode-ai/plugin/tui'
import { Show, For } from 'solid-js'
import type { BudgetData } from '../types'
import { ProviderCard } from './ProviderCard'
import { formatRelativeTime } from '../utils/format'

interface KeyInfoPanelProps {
  api: TuiPluginApi
  sessionId: string
  budgetData: BudgetData
}

/**
 * Main Key Info panel component
 * 
 * Displays budget information for all configured LiteLLM providers.
 */
export function KeyInfoPanel(props: KeyInfoPanelProps) {
  const theme = () => props.api.theme.current
  const budgets = () => Object.values(props.budgetData)
  const lastUpdated = () => {
    const timestamps = budgets().map((b) => b.lastFetched)
    return timestamps.length > 0 ? Math.max(...timestamps) : 0
  }

  return (
    <box flexDirection="column" gap={1}>
      {/* Header */}
      <text fg={theme().text}>
        <b>Key Info</b>
      </text>

      {/* No data state */}
      <Show when={budgets().length === 0}>
        <text fg={theme().textMuted}>No budget data available</text>
        <text fg={theme().textMuted}>Waiting for oclitellmac-server...</text>
      </Show>

      {/* Provider cards */}
      <For each={budgets()}>
        {(budget) => <ProviderCard budget={budget} theme={theme()} />}
      </For>

      {/* Last updated indicator */}
      <Show when={budgets().length > 0 && lastUpdated() > 0}>
        <text fg={theme().textMuted}>Updated {formatRelativeTime(lastUpdated())}</text>
      </Show>
    </box>
  )
}
