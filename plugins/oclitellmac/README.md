# oclitellmac

OpenCode LiteLLM Auto-Config - Automatic multi-proxy configuration with budget tracking.

This plugin combines both server and TUI functionality in a single package for easier installation.

## Installation

```bash
opencode plugin add /path/to/oclitellmac
```

## Configuration

Add both plugins to your `opencode.json`:

```json
{
  "plugin": [
    "oclitellmac/server",
    "oclitellmac/tui"
  ]
}
```

## Structure

- **`server/`** - Server plugin that configures LiteLLM endpoints and tracks budgets
- **`tui/`** - TUI plugin that displays budget information in the sidebar

## Documentation

- Server plugin: See `server/README.md`
- TUI plugin: See `tui/README.md`

## Features

### Server Plugin
- Automatic provider configuration from multiple LiteLLM endpoints
- Budget tracking with periodic polling
- Category-based model filtering (chat, embedding, TTS, etc.)
- Cached data fallback when endpoints are unreachable

### TUI Plugin
- Real-time budget display in OpenCode sidebar
- Per-provider budget breakdown
- File watcher for immediate updates
- Absolute timestamp display (timezone-aware)

## Configuration Files

- **Server config**: `~/.config/oclitellmac/server.json`
- **State directory**: `~/.local/state/oclitellmac/`
  - `key-info/` - Budget data files
  - `providers/` - Cached provider configurations

## Requirements

- OpenCode with plugin support
- LiteLLM proxy endpoint(s)
- Node.js (for development)

## License

MIT
