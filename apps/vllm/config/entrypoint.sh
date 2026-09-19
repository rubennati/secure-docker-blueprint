#!/bin/sh
set -e

# vLLM reads its API key (and a Hugging Face token, for gated models) from
# environment variables, not files — there is no _FILE variant. Read the
# secrets here and export them before handing off to `vllm serve`.
_key="$(cat /run/secrets/VLLM_API_KEY)"
export VLLM_API_KEY="$_key"
unset _key

# The token is optional: an empty file means public models only.
_hf="$(cat /run/secrets/HF_TOKEN)"
if [ -n "$_hf" ]; then
  export HF_TOKEN="$_hf"
fi
unset _hf

exec "$@"
