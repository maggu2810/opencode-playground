# oclitellmac-tui

**OpenCode LiteLLM Auto-Config TUI** - Display budget information from multiple LiteLLM proxies in the OpenCode sidebar.

## Features

- 📊 **Real-time budget display** - Shows spend, limit, and remaining budget
- 🔄 **File-based updates** - Reads cached data from `oclitellmac-server`
- ⚡ **Instant updates** - File watcher detects changes immediately (< 100ms)
- 🎨 **Color-coded alerts** - Green (healthy), yellow (warning), red (danger)
- 📦 **Multiple providers** - Displays all configured LiteLLM endpoints
- 🚫 **No API calls** - Zero network overhead, reads local files only

## Prerequisites

**Required**: `oclitellmac-server` plugin must be installed and running.

The server plugin writes budget data to `~/.local/state/oclitellmac/key-info/`, which this TUI plugin reads and displays.

## Installation

```bash
opencode plugin add /path/to/oclitellmac-tui
```

## How It Works

1. **oclitellmac-server** fetches budget data from LiteLLM `/key/info` endpoints
2. Server writes data to `~/.local/state/oclitellmac/key-info/<provider>.json`
3. **oclitellmac-tui** watches the directory for file changes
4. When files change, TUI updates the sidebar display instantly
5. No polling, no API calls - pure file-based reactivity

## Sidebar Display

The plugin adds a "Key Info" section to the OpenCode sidebar showing:

```
Key Info

┌─────────────────────────┐
│ LiteLLM Prod            │
│ ████████████░░░░░░░░    │
│ $45.67 / $100.00        │
│ 45.7% used              │
│ $54.33 remaining        │
│ Resets in 15d (monthly) │
│ user-prod-key           │
└─────────────────────────┘

┌─────────────────────────┐
│ LiteLLM Dev             │
│ ███░░░░░░░░░░░░░░░░░    │
│ $12.34 / $50.00         │
│ 24.7% used              │
│ $37.66 remaining        │
│ Resets in 20d (monthly) │
│ user-dev-key            │
└─────────────────────────┘

Updated 2s ago
```

## Budget Data Format

The plugin reads JSON files with this structure:

```json
{
  "providerKey": "litellm-prod",
  "fetchedAt": 1736647260000,
  "keyInfo": {
    "key_alias": "user-prod-key",
    "spend": 45.67,
    "max_budget": 100.00,
    "budget_duration": "monthly",
    "budget_reset_at": "2026-02-01T00:00:00Z",
    "expires": "2027-01-01T00:00:00Z"
  }
}
```

## Color Coding

Budget usage is color-coded for quick visual status:

- 🟢 **Green** (< 75% used) - Healthy, plenty of budget remaining
- 🟡 **Yellow** (75-90% used) - Warning, approaching limit
- 🔴 **Red** (> 90% used) - Danger zone, budget nearly exhausted

## File Watching

The plugin uses native `fs.watch()` for instant updates with automatic fallback to 5-second polling if file watching is unavailable on your platform.

**Benefits**:
- ⚡ Updates appear within 100ms of budget data change
- 💤 Zero CPU usage when idle (no polling overhead)
- 🔄 Automatic fallback ensures compatibility

## Troubleshooting

### "No budget data available"

**Cause**: `oclitellmac-server` plugin not installed or hasn't written data yet.

**Solution**: 
1. Install `oclitellmac-server` plugin
2. Configure `~/.config/oclitellmac/server.json`
3. Restart OpenCode
4. Wait 60 seconds for initial budget fetch

### Budget not updating

**Cause**: File watcher not detecting changes or files not being written.

**Solution**:
1. Check `oclitellmac-server` is running: Look for `[oclitellmac]` logs
2. Verify files exist: `ls ~/.local/state/oclitellmac/key-info/`
3. Check file timestamps: `ls -lh ~/.local/state/oclitellmac/key-info/`
4. Restart OpenCode to reset file watcher

### Provider names show as "Litellm Prod" instead of full name

**Behavior**: Provider keys are auto-formatted: `"litellm-prod"` → `"Litellm Prod"`

**This is expected**: The TUI plugin only reads budget files, not the full provider config.

## Plugin Architecture

### File Structure

```
src/
├── index.tsx              # Main plugin entry
├── types.ts               # Type definitions
├── loader.ts              # File reading & parsing
├── watcher.ts             # File watching (fs.watch + polling fallback)
├── components/
│   ├── KeyInfoPanel.tsx   # Main panel component
│   └── ProviderCard.tsx   # Individual provider card
└── utils/
    └── format.ts          # Formatting utilities
```

### Data Flow

```
~/.local/state/oclitellmac/key-info/*.json
              ↓
      fs.watch() detects change
              ↓
      BudgetLoader.loadAll()
              ↓
      Parse & normalize data
              ↓
      Update Solid.js signal
              ↓
      Re-render KeyInfoPanel
```

## Configuration

No configuration required! The plugin automatically:
- Detects the state directory: `~/.local/state/oclitellmac/`
- Watches for file changes
- Displays all providers found in `key-info/` directory

## Performance

- **Memory**: < 5 MB (minimal overhead)
- **CPU**: Near zero when idle (file watcher is event-based)
- **Disk I/O**: Only reads files when they change
- **Network**: Zero (no API calls)

## Companion Plugin

**oclitellmac-server** - Server plugin that fetches budget data from LiteLLM endpoints and writes to files. Install this first!

## License

MIT
