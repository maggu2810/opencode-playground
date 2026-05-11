/** @jsxImportSource @opentui/solid */

/**
 * Format a number as USD currency
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

/**
 * Format a percentage
 */
export function formatPercent(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

/**
 * Generate a text-based progress bar
 * @param value - Current value
 * @param max - Maximum value
 * @param width - Bar width in characters (default: 20)
 * @returns Progress bar string like "████████░░░░░░░░░░░░"
 */
export function formatProgressBar(value: number, max: number, width: number = 20): string {
  const safeValue = Number.isFinite(value) ? Math.max(0, value) : 0
  const safeMax = Number.isFinite(max) && max > 0 ? max : 1
  const percent = Math.min(1, safeValue / safeMax)
  const filled = Math.round(percent * width)
  const empty = width - filled

  return '█'.repeat(filled) + '░'.repeat(empty)
}

/**
 * Format ISO date string to readable date (YYYY-MM-DD)
 */
export function formatDate(isoString: string): string {
  try {
    return isoString.slice(0, 10)
  } catch {
    return 'unknown'
  }
}

/**
 * Format ISO date string to relative time (e.g., "in 3 days", "2 hours ago")
 */
export function formatRelativeTime(isoString: string | number): string {
  try {
    const date = typeof isoString === 'number' ? new Date(isoString) : new Date(isoString)
    const now = Date.now()
    const diff = date.getTime() - now
    const absDiff = Math.abs(diff)

    const seconds = Math.floor(absDiff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    const future = diff > 0

    if (days > 0) {
      return future ? `in ${days}d` : `${days}d ago`
    } else if (hours > 0) {
      return future ? `in ${hours}h` : `${hours}h ago`
    } else if (minutes > 0) {
      return future ? `in ${minutes}m` : `${minutes}m ago`
    } else {
      return future ? 'soon' : 'just now'
    }
  } catch {
    return 'unknown'
  }
}
