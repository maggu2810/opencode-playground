# oclitellmac-server

**OpenCode LiteLLM Auto-Config** - Automatically configure multiple LiteLLM proxy endpoints as OpenCode providers.

## Features

- 🚀 **Zero-config provider setup** - No manual `opencode.json` editing
- 🔗 **Multiple endpoints** - Configure multiple LiteLLM proxies at once
- 🔑 **Automatic authentication** - API keys stored in plugin config
- 📊 **Model discovery** - Fetches models from LiteLLM `/public/model_hub` and `/v1/model/info`
- 💾 **Smart caching** - Falls back to cached data if endpoints are unreachable
- 💰 **Budget tracking** - Monitors usage via `/key/info` endpoint
- 🔒 **File locking** - Prevents concurrent write collisions

## Installation

```bash
opencode plugin add /path/to/oclitellmac-server
```

## Configuration

Create `~/.config/oclitellmac/server.json`:

```json
{
  "endpoints": [
    {
      "baseUrl": "https://litellm-prod.example.com",
      "apiKey": "sk-prod-...",
      "providerName": "LiteLLM Production",
      "providerKey": "litellm-prod",
      "enabled": true
    },
    {
      "baseUrl": "https://litellm-dev.example.com",
      "apiKey": "sk-dev-...",
      "providerName": "LiteLLM Development",
      "providerKey": "litellm-dev",
      "enabled": false
    }
  ],
  "options": {
    "timeout": 30,
    "budgetPollInterval": 60,
    "fallbackToCache": true
  }
}
```

### Configuration Fields

#### Endpoint Configuration

- **`baseUrl`** (string, required): LiteLLM proxy base URL (without `/v1`)
- **`apiKey`** (string, required): Bearer token for API authentication
- **`providerName`** (string, required): Display name in OpenCode UI
- **`providerKey`** (string, required): Unique provider identifier
- **`enabled`** (boolean, optional, default: `true`): Whether to load this endpoint

#### Options

- **`timeout`** (number, optional, default: `30`): HTTP request timeout in seconds
- **`budgetPollInterval`** (number, optional, default: `60`): How often to poll `/key/info` in seconds
- **`fallbackToCache`** (boolean, optional, default: `true`): Use cached data if endpoint unreachable

## State Storage

The plugin stores cached data in `~/.local/state/oclitellmac/`:

```
~/.local/state/oclitellmac/
├── providers/          # Cached provider & model data
│   ├── litellm-prod.json
│   └── litellm-dev.json
└── key-info/           # Budget/usage data (for TUI display)
    ├── litellm-prod.json
    └── litellm-dev.json
```

## How It Works

1. **On OpenCode startup**, the plugin:
   - Loads configuration from `~/.config/oclitellmac/server.json`
   - Fetches models from each enabled endpoint
   - Caches results to `~/.local/state/oclitellmac/providers/`
   - Injects providers into OpenCode (no `opencode.json` needed)
   - Starts budget tracking (polls `/key/info` every 60 seconds)

2. **After each chat message**, the plugin:
   - Triggers an immediate budget data refresh
   - Stores results in `~/.local/state/oclitellmac/key-info/`

3. **If an endpoint is unreachable**:
   - Falls back to cached provider data (if enabled)
   - Logs warning message
   - Provider remains available with cached models

## Budget Tracking

Budget data from `/key/info` is stored in JSON format:

```json
{
  "providerKey": "litellm-prod",
  "fetchedAt": 1736647260000,
  "keyInfo": {
    "key_alias": "user-prod-key",
    "spend": 45.67,
    "max_budget": 100.00,
    "budget_remaining": 54.33,
    "budget_reset_at": "2026-02-01T00:00:00Z"
  }
}
```

This data can be consumed by the `oclitellmac-tui` plugin for visual display.

## Troubleshooting

### Plugin not loading providers

1. Check configuration file exists: `~/.config/oclitellmac/server.json`
2. Verify JSON syntax is valid
3. Check OpenCode logs for error messages: `[oclitellmac]` prefix

### Endpoint unreachable

- Plugin will fall back to cached data if `fallbackToCache: true`
- Check `~/.local/state/oclitellmac/providers/` for cached data
- Verify endpoint URL and API key are correct

### Models not appearing

- Ensure endpoint is enabled: `"enabled": true`
- Check that LiteLLM proxy is accessible
- Restart OpenCode after configuration changes

## Companion Plugin

**oclitellmac-tui** - TUI plugin that displays budget data in the OpenCode sidebar (separate plugin, coming soon)

## License

MIT
