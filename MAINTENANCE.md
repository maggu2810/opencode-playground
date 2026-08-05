# Plugins oclitellmac
I would like to update the oclitellm plugin (plugins/oclitellmac/).

While oclitellmac has been created we inspected the opencode code base (repos/opencode) and other litellm integration plugins (e.g. repos/opencode-litellm@BlakeHastings, repos/opencode-litellm@yuseferi).

Ensure the documentation for the plugin development contains alwys the commit ids of the third party repos (see above) we used.

Plan:

- Update repos/opencode to the latest released version (so, git tag). Using the latest released version as reference makes absoulte sense, because we can state that our plugin needs at least this version to work reliable
- Update the third party litellm plugins to the latest HEAD, so we can compare what has all been implemented there already
- Check what has been changed and update our oclitellmac plugin to include all new features (see what other plugins has been improved, what opencode has been changed for model configuration, litellm, ...) what other provides and what with the recent opencode version can be done.
- Additionally ensure that tools/config-generator to generate the opencode.jsonc contains all improvements we apply to oclitellmac