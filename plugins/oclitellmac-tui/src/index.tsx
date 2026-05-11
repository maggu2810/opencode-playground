/** @jsxImportSource @opentui/solid */
import type { TuiPlugin, TuiPluginModule } from '@opencode-ai/plugin/tui'
import { createSignal } from 'solid-js'
import type { BudgetData } from './types'
import { BudgetLoader } from './loader'
import { BudgetWatcher } from './watcher'
import { KeyInfoPanel } from './components/KeyInfoPanel'

const PLUGIN_ID = 'oclitellmac.tui'
const SIDEBAR_ORDER = 125 // After context (100), before files (500)
const POLL_INTERVAL_MS = 5000 // 5 second fallback polling

/**
 * oclitellmac-tui plugin
 * 
 * Displays LiteLLM budget information in the OpenCode sidebar by reading
 * cached data from ~/.local/state/oclitellmac/key-info/
 * 
 * Uses file watching for real-time updates when oclitellmac-server writes
 * new budget data.
 */
const tui: TuiPlugin = async (api) => {
  const loader = new BudgetLoader()

  // Reactive state
  const [budgetData, setBudgetData] = createSignal<BudgetData>({})

  /**
   * Refresh all budget data from files
   */
  async function refreshBudgets() {
    const data = await loader.loadAll()
    setBudgetData(data)
  }

  // Initial load
  await refreshBudgets()

  // Start file watcher for real-time updates
  const watcher = new BudgetWatcher(
    loader.getStateDir(),
    () => {
      // File changed - reload budget data
      refreshBudgets().catch((error) => {
        console.error('[oclitellmac-tui] Failed to refresh budgets:', error)
      })
    },
    POLL_INTERVAL_MS,
  )
  watcher.start()

  // Register sidebar slot
  api.slots.register({
    order: SIDEBAR_ORDER,
    slots: {
      sidebar_content(_ctx, props) {
        return (
          <KeyInfoPanel api={api} sessionId={props.session_id} budgetData={budgetData()} />
        )
      },
    },
  })

  // Cleanup on plugin dispose
  api.lifecycle.onDispose(() => {
    watcher.stop()
  })
}

const plugin: TuiPluginModule & { id: string } = {
  id: PLUGIN_ID,
  tui,
}

export default plugin
