# oclitellmac Plugins - Installation & Testing Guide

## ✅ Configuration Fixes Complete

Both plugins have been fixed and are ready for installation:

### Changes Applied

**TUI Plugin (`oclitellmac-tui`):**
- ✅ Added `exports["./tui"]` for proper TUI detection
- ✅ Moved `@opentui/*` and `solid-js` to `peerDependencies`
- ✅ Added missing peer dependencies (`@opentui/core`, `@opentui/keymap`)
- ✅ Dependencies installed successfully

**Server Plugin (`oclitellmac-server`):**
- ✅ Removed unused `@opencode-ai/sdk` dependency
- ✅ Dependencies installed successfully
- ✅ Created `config-example.json` as configuration template

---

## 📋 Installation Steps

### Step 1: Configure LiteLLM Endpoints

Create the configuration file at `~/.config/oclitellmac/server.json`:

```bash
# Create config directory
mkdir -p ~/.config/oclitellmac

# Copy example config
cp plugins/oclitellmac-server/config-example.json ~/.config/oclitellmac/server.json

# Edit with your actual endpoint details
vim ~/.config/oclitellmac/server.json
```

**Minimal Configuration Example:**
```json
{
  "endpoints": [
    {
      "providerKey": "litellm-prod",
      "baseURL": "https://your-litellm-proxy.com",
      "apiKey": "sk-your-actual-key-here"
    }
  ],
  "options": {
    "fallbackToCache": true,
    "timeout": 10000,
    "budgetPollInterval": 60000
  }
}
```

**Important Notes:**
- Replace `baseURL` with your actual LiteLLM proxy URL (without `/v1` path)
- Replace `apiKey` with your actual API key
- Keys are stored in **plain text** - ensure restrictive permissions:
  ```bash
  chmod 600 ~/.config/oclitellmac/server.json
  ```

---

### Step 2: Install Server Plugin

```bash
# From the opencode-playground directory
opencode plugin add ./plugins/oclitellmac-server

# Or use absolute path
opencode plugin add /home/de23a4/workspace/kion/de23a4/genai/repos/opencode-playground/plugins/oclitellmac-server

# For global installation (available in all projects)
opencode plugin add ./plugins/oclitellmac-server --global
```

**Verify Installation:**
```bash
# Check that plugin is registered
cat ~/.config/opencode/opencode.jsonc | grep oclitellmac
# OR (for project-local install)
cat ./opencode.jsonc | grep oclitellmac
```

Expected output:
```json
{
  "plugin": [
    "file:///home/de23a4/workspace/kion/de23a4/genai/repos/opencode-playground/plugins/oclitellmac-server"
  ]
}
```

---

### Step 3: Install TUI Plugin

```bash
# From the opencode-playground directory
opencode plugin add ./plugins/oclitellmac-tui

# Or use absolute path
opencode plugin add /home/de23a4/workspace/kion/de23a4/genai/repos/opencode-playground/plugins/oclitellmac-tui

# For global installation
opencode plugin add ./plugins/oclitellmac-tui --global
```

**Verify Installation:**
```bash
# Check that TUI plugin is registered
cat ~/.config/opencode/tui.json | grep oclitellmac
```

Expected output:
```json
{
  "plugin": [
    "file:///home/de23a4/workspace/kion/de23a4/genai/repos/opencode-playground/plugins/oclitellmac-tui"
  ]
}
```

**Critical:** If the plugin appears in `opencode.jsonc` instead of `tui.json`, the `exports["./tui"]` fix didn't work. Verify `plugins/oclitellmac-tui/package.json` has the correct structure.

---

### Step 4: Start OpenCode

```bash
# Navigate to any project directory
cd ~/your-project

# Start OpenCode
opencode
```

**Watch for Startup Logs:**

You should see messages like:
```
[oclitellmac] Loaded configuration from /home/de23a4/.config/oclitellmac/server.json
[oclitellmac] Configured provider: litellm-prod (12 models)
[oclitellmac] Budget tracking started (poll interval: 60000ms)
```

**If you see errors:**
- `Failed to load config` → Check `~/.config/oclitellmac/server.json` exists and is valid JSON
- `Failed to fetch models` → Check `baseURL` and `apiKey` are correct
- `ECONNREFUSED` → LiteLLM proxy is not reachable
- `401 Unauthorized` → API key is invalid

---

## 🧪 Testing Checklist

### Test 1: Provider Discovery ✅

**Objective:** Verify providers are auto-configured from LiteLLM proxy

**Steps:**
1. Start OpenCode (see logs above)
2. Press `Ctrl+P` (or your model picker keybind)
3. Look for models with your provider name prefix

**Expected Result:**
- Models appear in picker
- Provider name is formatted (e.g., `litellm-prod` → `"LiteLLM Prod"`)
- Model count matches your LiteLLM proxy's model list

**Screenshot Opportunity:** Model picker showing auto-discovered models

---

### Test 2: Model Selection & Chat ✅

**Objective:** Verify selected models work correctly

**Steps:**
1. Select a model from auto-configured provider
2. Type a test message: "Hello, this is a test"
3. Press Enter to send

**Expected Result:**
- Message sends successfully
- Response arrives from LiteLLM proxy
- No errors in terminal

**Troubleshooting:**
- If response fails, check terminal for error messages
- Verify API key has permission to use the selected model
- Check LiteLLM proxy logs for request details

---

### Test 3: TUI Budget Display ✅

**Objective:** Verify sidebar shows budget information

**Steps:**
1. In OpenCode session view, look at right sidebar
2. Find "Key Info" section (should be near top)
3. Verify one card per configured endpoint

**Expected Display (per provider card):**
```
┌─ LiteLLM Prod ──────────────────────────┐
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░ 25%  │
│ Spent: $12.50 / $50.00                  │
│ Remaining: $37.50                       │
│ Resets: in 23 days                      │
└─────────────────────────────────────────┘
```

**Color Coding:**
- 🟢 **Green bar** (0-74% used) - Safe usage level
- 🟡 **Yellow bar** (75-89% used) - Warning level
- 🔴 **Red bar** (90-100% used) - Critical level

**If sidebar is empty:**
- Check that TUI plugin is installed (in `tui.json`, not `opencode.jsonc`)
- Verify budget data files exist: `~/.local/state/oclitellmac/key-info/<providerKey>.json`
- Check terminal for TUI plugin errors

---

### Test 4: Budget Updates (After Message) ✅

**Objective:** Verify budget updates after sending messages

**Steps:**
1. Note current spend amount in sidebar
2. Send a message using auto-configured model
3. Wait 2-3 seconds for message completion
4. Check if spend amount increased

**Expected Result:**
- Spend increases by cost of message
- Progress bar updates
- Percentage recalculates
- Changes happen automatically (no refresh needed)

**Note:** Budget updates have two triggers:
- **Immediate:** After each message via `chat.message` hook
- **Periodic:** Every 60 seconds via polling

---

### Test 5: File Watcher (Manual Test) ✅

**Objective:** Verify sidebar updates when budget files change

**Steps:**
1. Locate budget file: `~/.local/state/oclitellmac/key-info/<providerKey>.json`
2. Note current spend value in sidebar
3. Edit file manually and change `spend` value
4. Save file
5. Watch sidebar (should update within ~5 seconds)

**Expected Result:**
- Sidebar updates automatically
- No need to restart OpenCode
- File watcher detected change

**Troubleshooting:**
- If updates are delayed >5 seconds, file watcher might not be working
- Polling fallback should still update within 5 seconds
- Check terminal for file watcher errors

---

### Test 6: Cached Data Fallback ✅

**Objective:** Verify plugin works when LiteLLM proxy is unreachable

**Steps:**
1. Ensure plugin has successfully fetched data at least once
2. Stop LiteLLM proxy (or disconnect network)
3. Restart OpenCode

**Expected Result:**
- Providers still load from cached data
- Terminal shows: `[oclitellmac] Using cached data for: litellm-prod`
- Models appear in picker (from cache)
- Budget display shows last known values

**Purpose:** Ensures plugin doesn't break OpenCode if endpoint is temporarily down

---

### Test 7: Multiple Endpoints ✅

**Objective:** Verify support for multiple LiteLLM proxies

**Steps:**
1. Add second endpoint to `~/.config/oclitellmac/server.json`:
   ```json
   {
     "endpoints": [
       {
         "providerKey": "litellm-prod",
         "baseURL": "https://prod.example.com",
         "apiKey": "sk-prod-key"
       },
       {
         "providerKey": "litellm-staging",
         "baseURL": "https://staging.example.com",
         "apiKey": "sk-staging-key"
       }
     ]
   }
   ```
2. Restart OpenCode

**Expected Result:**
- Two providers appear in model picker
- Two budget cards in sidebar
- Each provider has distinct name ("LiteLLM Prod", "LiteLLM Staging")
- Models are correctly attributed to their provider

---

### Test 8: Error Handling ✅

**Objective:** Verify graceful failure when configuration is invalid

**Steps:**
1. Rename config file: `mv ~/.config/oclitellmac/server.json ~/.config/oclitellmac/server.json.bak`
2. Start OpenCode

**Expected Result:**
- OpenCode starts normally (doesn't crash)
- Terminal shows: `[oclitellmac] Failed to load config: ...`
- Terminal shows: `[oclitellmac] Please create ~/.config/oclitellmac/server.json ...`
- No auto-configured providers (plugin disabled gracefully)

**Restore:**
```bash
mv ~/.config/oclitellmac/server.json.bak ~/.config/oclitellmac/server.json
```

---

## 🐛 Troubleshooting

### Issue: TUI Plugin Not Loading

**Symptoms:**
- No "Key Info" section in sidebar
- Plugin appears in `opencode.jsonc` instead of `tui.json`

**Fix:**
1. Check package.json has correct exports:
   ```bash
   cat plugins/oclitellmac-tui/package.json | grep -A2 '"exports"'
   ```
   Should show:
   ```json
   "exports": {
     "./tui": {
       "import": "./src/index.tsx"
     }
   }
   ```

2. Reinstall plugin:
   ```bash
   opencode plugin remove oclitellmac-tui
   opencode plugin add ./plugins/oclitellmac-tui
   ```

---

### Issue: JSX Transform Failures

**Symptoms:**
- TUI plugin crashes on load
- Errors mentioning "JSX" or "transform" in terminal

**Fix:**
1. Verify peer dependencies are NOT in `dependencies`:
   ```bash
   cat plugins/oclitellmac-tui/package.json | grep -A10 '"dependencies"'
   ```
   Should NOT contain `@opentui/*` or `solid-js`

2. Remove and reinstall plugin:
   ```bash
   cd plugins/oclitellmac-tui
   rm -rf node_modules package-lock.json
   npm install
   opencode plugin remove oclitellmac-tui
   opencode plugin add ./plugins/oclitellmac-tui
   ```

---

### Issue: No Models Appearing

**Symptoms:**
- Server plugin loads
- No models in model picker

**Diagnosis:**
1. Check terminal logs for errors
2. Verify LiteLLM proxy is reachable:
   ```bash
   curl -H "Authorization: Bearer sk-your-key" \
        https://your-proxy.com/v1/models
   ```

3. Check cached data:
   ```bash
   cat ~/.local/state/oclitellmac/providers/<providerKey>.json
   ```

**Common Causes:**
- Invalid `baseURL` (check for typos, ensure no `/v1` suffix)
- Invalid `apiKey` (check key has model list permission)
- Network connectivity issues
- LiteLLM proxy is down

---

### Issue: Budget Not Updating

**Symptoms:**
- Sidebar shows budget, but values never change
- Budget appears stuck

**Diagnosis:**
1. Check if budget files are being written:
   ```bash
   ls -lh ~/.local/state/oclitellmac/key-info/
   ```

2. Check file timestamps (should update every ~60s):
   ```bash
   watch -n 5 'ls -lh ~/.local/state/oclitellmac/key-info/'
   ```

3. Check terminal for budget tracker errors

4. Manually trigger budget fetch by sending a message

**Common Causes:**
- API key doesn't have budget info permission
- LiteLLM proxy doesn't support `/key/info` endpoint
- File permission issues (check directory is writable)

---

### Issue: File Watcher Not Working

**Symptoms:**
- Manual file edits don't trigger sidebar updates
- Must restart OpenCode to see changes

**Diagnosis:**
1. Check for file watcher errors in terminal
2. Verify polling fallback is working (should update within 5 seconds)

**Workaround:**
The 5-second polling fallback should handle this gracefully. If updates are too slow, reduce polling interval in TUI plugin code (`src/watcher.ts:POLL_INTERVAL`).

---

## 📊 Expected File Structure After Installation

```
~/.config/oclitellmac/
└── server.json                          # User configuration

~/.local/state/oclitellmac/
├── providers/
│   ├── litellm-prod.json               # Cached provider/model data
│   └── litellm-staging.json
└── key-info/
    ├── litellm-prod.json               # Budget tracking data
    └── litellm-staging.json

~/.config/opencode/
├── opencode.jsonc                       # Server plugin registration
└── tui.json                            # TUI plugin registration
```

---

## 🎯 Success Criteria Checklist

**Installation Phase:**
- [ ] Both plugins install without errors
- [ ] Server plugin appears in `opencode.jsonc`
- [ ] TUI plugin appears in `tui.json`
- [ ] No critical npm errors (peer dependency warnings are OK)

**Runtime Phase:**
- [ ] Server plugin logs configuration loading
- [ ] Providers appear in model picker with formatted names
- [ ] Models can be selected and used for chat
- [ ] TUI sidebar displays "Key Info" section
- [ ] Budget cards show correct data structure
- [ ] Progress bars render with correct colors
- [ ] Budget updates after messages
- [ ] Budget updates periodically (~60s)
- [ ] File watcher responds to manual file changes
- [ ] Cached data fallback works when endpoint unreachable
- [ ] Multiple endpoints are supported
- [ ] No runtime errors in terminal

---

## 🚀 Next Steps

1. **Install both plugins** following steps above
2. **Complete testing checklist** (Tests 1-8)
3. **Report any issues** you encounter
4. **Provide feedback** on:
   - Installation process clarity
   - Plugin performance
   - Budget display usefulness
   - Missing features
   - Documentation gaps

---

## 📝 Development Notes

**Making Changes:**

After editing plugin code:
1. No build step required (TypeScript/TSX loaded directly by Bun)
2. Restart OpenCode to reload plugins
3. Check terminal for any plugin load errors

**Useful Commands:**
```bash
# View server plugin logs
opencode # then watch terminal output with [oclitellmac] prefix

# View TUI plugin registration
cat ~/.config/opencode/tui.json

# View server plugin registration
cat ~/.config/opencode/opencode.jsonc

# Clear cached data (force fresh fetch)
rm -rf ~/.local/state/oclitellmac/

# Remove plugins
opencode plugin remove oclitellmac-server
opencode plugin remove oclitellmac-tui
```

---

## 📚 References

- **Plugin Implementation:** `plugins/IMPLEMENTATION_COMPLETE.md`
- **Field Coverage:** `docs/litellm-integration/field-coverage-comparison.md`
- **Server Plugin:** `plugins/oclitellmac-server/README.md`
- **TUI Plugin:** `plugins/oclitellmac-tui/README.md`
- **OpenCode Docs:** https://opencode.ai/docs
- **LiteLLM Docs:** https://docs.litellm.ai/

---

**Happy Testing! 🎉**
