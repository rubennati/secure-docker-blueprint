#!/bin/sh
set -e

# paperless-gpt reads every credential from the environment and has no _FILE
# variant, so the values are exported here from Docker Secrets and the image's
# own entrypoint runs after them.
#
# POSIX quirk: `export VAR=$(cmd)` hides cmd's exit status — export is a special
# builtin whose own status (always 0) is what `set -e` sees. Each value goes
# through an intermediate variable so a missing secret aborts the start instead
# of silently exporting an empty string.

# --- Paperless-ngx API token (required) ---
_paperless_api_token="$(cat /run/secrets/PAPERLESS_API_TOKEN)"
export PAPERLESS_API_TOKEN="$_paperless_api_token"
unset _paperless_api_token

# --- Model provider key (optional) ---
# Empty for a local model server that needs no key; set for a hosted provider.
# The variable name follows LLM_PROVIDER: OPENAI_API_KEY covers every
# OpenAI-compatible endpoint, including apps/litellm.
if [ -s /run/secrets/LLM_API_KEY ]; then
    _llm_api_key="$(cat /run/secrets/LLM_API_KEY)"
    export OPENAI_API_KEY="$_llm_api_key"
    unset _llm_api_key
fi

exec "$@"
