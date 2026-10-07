# Open Issues

Open items for the playground repo (outside the oclitellmac plugin, which tracks its own in `plugins/oclitellmac/docs/KNOWN-ISSUES.md`). Remove an entry when it is fixed.

## config-generator output loses data under OpenCode v2

**Status**: open, needs investigation and a decision.

The Python `tools/config-generator` writes the legacy `opencode.jsonc` provider shape. OpenCode v2 still reads that shape, but its normalizer (`repos/opencode/packages/core/src/config/normalize.ts`) omits some legacy keys with an "omitted unsupported legacy setting" diagnostic:

- Provider keys `id`, `whitelist` and `blacklist`.
- Model keys `release_date`, `attachment`, `reasoning`, `temperature` and `experimental`.

Consequences, not yet tested in a running OpenCode:

- The generator hides non-chat models through the provider `blacklist`. In v2 the blacklist is ignored, so those models probably all appear in the model picker.
- The capability flags the generator writes (`attachment`, `reasoning`, `temperature`) are dropped.

Options to evaluate:

- Emit only chat models by default and add non-chat models only when their category is enabled.
- Emit the native v2 config shape instead of the legacy one.

For the plugin-side equivalent (non-chat models registered with `enabled: false`), when comparing the two, [read here](../plugins/oclitellmac/server/ARCHITECTURE.md).

## `repos/opencode-litellm@yuseferi` can be checked out at the wrong commit

**Status**: open, housekeeping.

On at least one machine the submodule was checked out at an older release than the pin recorded in the source map, which would downgrade the pin if committed. After cloning or pulling, run `git submodule update --init` and check `git status` before committing submodule pointers. For the pinned versions, when checking what each submodule should be at, [read here](litellm-integration/source-map.md).
