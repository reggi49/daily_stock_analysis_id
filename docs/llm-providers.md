# LLM Provider Configuration Guide

This guide is for first-time configuration users. It explains how to choose an LLM configuration method, how to map the Web settings page "AI Model Configuration" presets to `.env` / GitHub Actions, and how to handle common detection errors.

> This page does not introduce new external providers, model names, or Base URL compatibility behavior; it only organizes configuration references and official sources. Actual compatibility is based on the repository's current runtime dependencies and test conclusions.
>
> - Runtime basis: `requirements.txt` currently locks `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`; compatibility semantics are based on this version constraint.
> - Verification loop: System configuration pipeline regression see `tests/test_system_config_service.py` and `tests/test_system_config_api.py`; Web-side configuration page interaction regression see existing component test cases.
> - Rollback path: Preserves old variables without automatic migration; can be rolled back via Web/desktop export backup then `POST /api/v1/system/config/import`, or by manually restoring historical `LLM_*` / `LITELLM_*` / `AGENT_*` / `VISION_MODEL` configuration.

Actual available models, quotas, regional restrictions, and pricing are subject to each provider's console; if model list fetching fails, you can manually enter the model name in Web. Provider capability labels, official source links, and configuration notes displayed on the Web settings page come from static provider templates, for configuration reference only and do not represent verified runtime capabilities.

## Choose Configuration Method First

| Method | Best For | Main Variables | Notes |
| --- | --- | --- | --- |
| Minimal legacy | Users who just want to quickly run one model | `LITELLM_MODEL` + corresponding provider key | Fewest variables, good for local quick start; not suitable for complex fallback. |
| Channels | Users needing multiple providers, multiple keys, or fallback | `LLM_CHANNELS` + `LLM_<CHANNEL>_*` | Recommended default path; Web settings page saves this layer of configuration. |
| YAML | Users familiar with LiteLLM routing, load balancing, and enterprise gateways | `LITELLM_CONFIG` / `LITELLM_CONFIG_YAML` | Highest priority; once effective, Channels and legacy no longer participate in the request. |

Priority remains: `LITELLM_CONFIG` / `LITELLM_CONFIG_YAML` > `LLM_CHANNELS` > legacy provider keys. P4 only adds documentation, no migration, clearing, or silent rewriting of old configuration.

Generation backend configuration is a higher-level runtime selection contract. Phase 4 supports `GENERATION_BACKEND=litellm|codex_cli|claude_code_cli|opencode_cli`, but local CLI backends are not LiteLLM providers; do not configure as `LITELLM_MODEL=codex_cli/...`, `LITELLM_MODEL=claude_code_cli/...`, or `LITELLM_MODEL=opencode_cli/...`. The `codex_cli` preset uses `codex exec --output-last-message <temp-file> -` to read the final response; the `claude_code_cli` preset uses `claude --safe-mode --tools "" --disallowedTools "mcp__*" --strict-mcp-config --no-session-persistence --output-format json -p <static instruction>`, with the full DSA prompt via stdin, extracting final text only from the JSON envelope's `result/success` field, with parameter basis in [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference); the `opencode_cli` preset uses `opencode --pure run --format json [--model <OPENCODE_CLI_MODEL>] <static instruction> --file <temp prompt file>`, appending `--model` only when `OPENCODE_CLI_MODEL` is explicitly configured, with the full DSA prompt via a permission-controlled temp file, extracting final text only from non-tool-event JSON event text output, with parameter basis in [OpenCode CLI reference](https://opencode.ai/docs/cli) and config merge semantics in [OpenCode config reference](https://opencode.ai/docs/config). Diagnostic stdout/stderr and final response are jointly constrained by `GENERATION_BACKEND_MAX_OUTPUT_BYTES` total limit; exceeding returns structured `output_too_large`. `GENERATION_FALLBACK_BACKEND=` empty value disables backend-level fallback in local `.env`; when not configured, defaults to `litellm`; the default GitHub Actions workflow explicitly uses `litellm` when this variable is not configured; to disable fallback, set it to the primary backend for a self no-op. Agent tool calls still use LiteLLM; Web settings page only exposes `AGENT_GENERATION_BACKEND=auto|litellm`; hand-written `codex_cli|claude_code_cli|opencode_cli` does not enable text-only Agent mode and returns explicit unsupported tool-calling diagnostics.

The generation backend status endpoint and Web panel separate quick checks and smoke tests: quick checks only read saved `.env`, runtime fallback values, and current drafts without writing configuration, reloading runtime, or making real model requests; only JSON smoke tests use fixed JSON prompts and schemas to make real requests. `health_status` and `last_error_code/message` are current calculation results, not historical last errors. Local CLI preset `supports_tools=false` only means it does not support the DSA Agent tool-calling pipeline, not that plain text generation is unavailable.

This PR's smoke-verified versions are `claude 2.1.177 (Claude Code)` and `opencode 1.17.11`; no wider minimum version is declared. If the user's installed CLI does not support these fixed preset parameters or non-interactive output contract, DSA returns structured `capability_unsupported`, `cli_contract_unsupported`, `invalid_json`, `schema_validation_failed`, or corresponding backend error, and falls back to `litellm` when backend fallback is configured.

Local CLI Backend is not an offline model. Docker, cloud servers, and CI do not inherently possess the local machine's CLI login state; macOS does not inherit shell PATH when launching desktop from Finder/Dock, and the packaged desktop app appends common Homebrew paths during backend startup; if settings checks still report missing CLI executables, you need to fully quit and relaunch DSA. DSA does not read Codex/Claude/OpenCode credential files, nor does it generate or carry provider API keys for OpenCode; child processes may use the local machine's login state or configuration per CLI mechanisms, and stock codes, news, portfolio context, analysis prompts, and report drafts may be processed by the services behind the corresponding CLI. DSA defaults to inheriting only the minimal runtime environment and refuses wildcard inheritance of `CLAUDE_*`, `ANTHROPIC_*`, `OPENCODE_*`, provider API key/token/base-url/model env, and webhook tokens, reducing parent process configuration leakage risk; `CODEX_HOME` is retained only as an exact-name exception for existing Codex CLI login directory compatibility.

`opencode_cli` is an experimental/limited generation backend that does not support OpenCode serve / web / ACP / MCP / attach / `--dangerously-skip-permissions`. DSA defaults to using the local OpenCode's default model; `OPENCODE_CLI_MODEL` is an optional model override value that is only passed to OpenCode `--model` when configured. DSA writes a minimal project `opencode.json` in a temporary cwd, but OpenCode resolved config may still contain user local global config; runtime security boundaries depend on `--pure`, env denylist, prompt file permissions, and event extractor fail-closed.

## Web Settings Page Path

It's recommended to use the Web settings page for Channels configuration:

1. Open "AI Model Configuration" on the settings page.
2. Select a provider preset in "Quick Add Channel".
3. Enter the API key and optionally click "Fetch Models".
4. Select the primary model, Agent primary model, fallback model, and Vision model, then save.
5. Click "Test Connection" to verify authentication, model name, quota, and response format.
6. To verify JSON / tools / stream / vision capabilities, manually check "Runtime Capability Detection" before triggering; this detection generates real LLM requests and results only represent a best-effort detection of the current account, model, and endpoint; it does not write back to `.env` or block saving.

## Channels Examples

### DeepSeek Official Channel

```env
LLM_CHANNELS=deepseek
LLM_DEEPSEEK_PROTOCOL=deepseek
LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_DEEPSEEK_API_KEY=sk-xxx
LLM_DEEPSEEK_MODELS=deepseek-v4-flash,deepseek-v4-pro
LITELLM_MODEL=deepseek/deepseek-v4-flash
```

### OpenAI-compatible Aggregation or Custom Gateway

```env
LLM_CHANNELS=my_proxy
LLM_MY_PROXY_PROTOCOL=openai
LLM_MY_PROXY_BASE_URL=https://your-proxy.example.com/v1
LLM_MY_PROXY_API_KEY=sk-xxx
LLM_MY_PROXY_MODELS=gpt-5.5,claude-sonnet-4-6
```

OpenAI-compatible Base URLs should only include the provider's compatible entry point, without appending `/chat/completions`. Local `.env`, Docker, and self-hosted scripts can directly use custom channels; GitHub Actions requires the workflow to explicitly pass same-name `LLM_MY_PROXY_*` variables.
The Xiaomi MiMo example follows the same pattern: applicable to local `.env`, Docker, or self-hosted scripts; if using `LLM_CHANNELS=mimo` in GitHub Actions, you need to manually add corresponding `LLM_MIMO_*` mappings in the workflow for them to take effect.

## Common Provider Presets

| Provider | Channel Name | Protocol | Base URL | Model Example |
| --- | --- | --- | --- | --- |
| AIHubmix | `aihubmix` | `openai` | `https://aihubmix.com/v1` | `gpt-5.5,claude-sonnet-4-6,gemini-3.1-pro-preview` |
| Anspire Open | `anspire` | `openai` | `https://open-gateway.anspire.cn/v6` (example) | `Doubao-Seed-2.0-lite,Doubao-Seed-2.0-pro,qwen3.5-flash,MiniMax-M2.7` (example) |
| OpenAI | `openai` | `openai` | `https://api.openai.com/v1` | `gpt-5.5,gpt-5.4-mini` |
| DeepSeek | `deepseek` | `deepseek` | `https://api.deepseek.com` | `deepseek-v4-flash,deepseek-v4-pro` |
| Gemini | `gemini` | `gemini` | Leave empty | `gemini-3.1-pro-preview,gemini-3-flash-preview` |
| Anthropic Claude | `anthropic` | `anthropic` | Leave empty | `claude-sonnet-4-6,claude-opus-4-7` |
| Kimi / Moonshot | `moonshot` | `openai` | `https://api.moonshot.cn/v1` | `kimi-k2.6,kimi-k2.5` |
| Tongyi Qianwen / DashScope | `dashscope` | `openai` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen3.6-plus,qwen3.6-flash` |
| Zhipu GLM | `zhipu` | `openai` | `https://open.bigmodel.cn/api/paas/v4` | `glm-5.1,glm-4.7-flash` |
| MiniMax | `minimax` | `openai` | `https://api.minimax.io/v1` | `MiniMax-M3,MiniMax-M2.7,MiniMax-M2.7-highspeed` |
| Xiaomi MiMo | `mimo` | `openai` | Official console (not mapped by default in Actions) | Per official documentation/console |
| Volcengine / Doubao | `volcengine` | `openai` | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-seed-1-6-251015,doubao-seed-1-6-thinking-251015` |
| SiliconFlow | `siliconflow` | `openai` | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3.2,Qwen/Qwen3-235B-A22B-Thinking-2507` |
| OpenRouter | `openrouter` | `openai` | `https://openrouter.ai/api/v1` | `~anthropic/claude-sonnet-latest,~openai/gpt-latest` |
| Ollama | `ollama` | `ollama` | `http://127.0.0.1:11434` | `llama3.2,qwen2.5` |

## Official Sources and Compatibility

| Provider | Official Source | Compatibility Notes |
| --- | --- | --- |
| Anspire Open | [Anspire Open](https://open.anspire.cn/?share_code=QFBC0FYC) | `ANSPIRE_API_KEYS` can be used for LLM gateway and search when no higher-priority OpenAI-compatible source is configured; page and `.env` default example is `openai/Doubao-Seed-2.0-lite` + `https://open-gateway.anspire.cn/v6`; availability subject to console and model permissions. |
| OpenAI | [Model List](https://platform.openai.com/docs/models) | Official model page recommends starting with `gpt-5.5`; for low-latency/low-cost scenarios use `gpt-5.4-mini` or `gpt-5.4-nano`. |
| DeepSeek | [Quick Start](https://api-docs.deepseek.com/) | Official OpenAI Base URL is `https://api.deepseek.com`; `deepseek-chat` / `deepseek-reasoner` will be deprecated after 2026-07-24; current template uses `deepseek-v4-flash` / `deepseek-v4-pro` directly. |
| Gemini | [Model List](https://ai.google.dev/gemini-api/docs/models) | Gemini 3.1 Pro / Gemini 3 Flash are still preview; for production stability, switch to 2.5 stable models in the console. |
| Anthropic Claude | [Model Overview](https://docs.anthropic.com/en/docs/about-claude/models/all-models) | Claude current API IDs include `claude-sonnet-4-6`, `claude-opus-4-7`; Sonnet is more suitable as the default cost-effective entry point. |
| Kimi / Moonshot | [Kimi K2.6 Quick Start](https://platform.kimi.com/docs/guide/kimi-k2-6-quickstart), [Model List](https://platform.kimi.com/docs/models) | Officially recommends `kimi-k2.6`; `kimi-k2` series will be retired on 2026-05-25; legacy `moonshot-v1-*` is retained only as a stable old workload option. |
| Tongyi Qianwen / DashScope | [Text Generation](https://help.aliyun.com/zh/model-studio/text-generation-model/) | Bailian recommends `qwen3.6-plus`; after confirming results, use `qwen3.6-flash` to reduce cost. |
| Zhipu GLM | [Model Overview](https://docs.bigmodel.cn/cn/guide/start/model-overview), [GLM-5.1](https://docs.bigmodel.cn/cn/guide/models/text/glm-5.1) | `glm-5.1` is the current flagship; `glm-4.7-flash` serves as a lightweight/free model example. |
| MiniMax | [OpenAI API Compatible](https://platform.minimax.io/docs/api-reference/text-chat), [Get Model List](https://platform.minimax.io/docs/api-reference/models/openai/list-models), [Pricing](https://platform.minimax.io/docs/guides/pricing-paygo) | Official OpenAI-compatible Base URL is `https://api.minimax.io/v1`, listing `MiniMax-M3` (default, supports image input, officially supports up to 1M input context, pricing differentiates `<=512K` and `>512K` input tiers), `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`, and legacy model `MiniMax-M2.5`. This repository's fallback cost estimate conservatively registers M3 at the `<=512K` tier and retains M2.5 legacy pricing for historical user config compatibility; China-region Coding tool scenarios may use `.com`/Anthropic dedicated endpoints, subject to the console. |
| Xiaomi MiMo | Official documentation / console | Currently accessed via OpenAI-compatible method; Base URL, model name, and permissions per MiMo official documentation/console; `mimo` channel is not explicitly mapped in the repository's default workflow; for Actions use, add custom mappings per this guide's "GitHub Actions Configuration" section. |
| Volcengine / Doubao | [Online Inference (Standard)](https://www.volcengine.com/docs/82379/2121998), [Model List](https://www.volcengine.com/docs/82379/1949118) | Official example uses `https://ark.cn-beijing.volces.com/api/v3` with `doubao-seed-1-6-251015`; if using Coding Plan, use its dedicated Base URL and model name, do not apply this table's online inference template. |
| SiliconFlow | [Model List](https://docs.siliconflow.cn/quickstart/models), [Get Model List API](https://docs.siliconflow.cn/cn/api-reference/models/get-model-list) | Platform models update in real time and `/models` requires API Key; template only gives common new model examples; before saving, click "Fetch Models" on the Web settings page to confirm account visibility. |
| OpenRouter | [Models API](https://openrouter.ai/docs/api/api-reference/models/get-models) | OpenRouter supports `~anthropic/claude-sonnet-latest`, `~openai/gpt-latest` and other latest router aliases; a manual live smoke test on 2026-05-03 passed with Claude Sonnet latest as the default example, with GPT latest retained as an alternative switchable by account permissions. |
| LiteLLM | [OpenAI-Compatible Endpoints](https://docs.litellm.ai/docs/providers/openai_compatible) | OpenAI-compatible endpoints require writing runtime models as `openai/<model>`; Base URLs should only include the provider's compatible entry point without appending `/chat/completions`. |

This page's presets only guarantee configuration shape consistency with the current dependency's OpenAI-compatible routing rules; actual connectivity still depends on provider account permissions, region, quota, and model enablement status. The current LiteLLM version constraint is `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` (see `requirements.txt`), preserving historical minimum version, explicitly excluding PyPI incident versions, and preventing future major versions from auto-entering.

## OpenAI-compatible and LiteLLM Rules

- OpenAI-compatible provider channel `protocol` is typically `openai`.
- Runtime model names are typically written as `openai/<model>`; for example, `gpt-5.5` in a custom gateway can be routed by LiteLLM as `openai/gpt-5.5`.
- `Qwen/...`, `deepseek-ai/...` are service-provider or model-repository organization name prefixes, not LiteLLM provider prefixes; do not misidentify them as `provider/model` routing just because they contain slashes.
- Base URLs should only include the official or gateway-provided compatible entry point, typically to `/v1`, `/api/v3`, or the path specified in vendor documentation; do not manually append `/chat/completions`.
- If using YAML mode, configure per LiteLLM `model_list` / `litellm_params` native semantics; when YAML is effective, its priority exceeds Channels.

## GitHub Actions Configuration

The bundled `.github/workflows/00-daily-analysis.yml` only passes through environment variables explicitly listed in the workflow. When using channel mode, first set `LLM_CHANNELS` in Repository Variables or Secrets, then add corresponding `LLM_<CHANNEL>_*` by channel name.

| Field | Recommended Location | Notes |
| --- | --- | --- |
| `LLM_CHANNELS` | Variables or Secrets | Comma-separated channel names, e.g., `deepseek,minimax,volcengine`. |
| `LLM_<CHANNEL>_PROTOCOL` | Variables or Secrets | Non-sensitive, typically `openai`, `deepseek`, `gemini`, `anthropic`, or `ollama`. |
| `LLM_<CHANNEL>_BASE_URL` | Variables or Secrets | Non-sensitive preferred in Variables; private gateway addresses in Secrets. |
| `LLM_<CHANNEL>_MODELS` | Variables or Secrets | Non-sensitive model list, comma-separated. |
| `LLM_<CHANNEL>_ENABLED` | Variables or Secrets | Optional, defaults to enabled when not configured; set to `false` to skip the channel. |
| `LLM_<CHANNEL>_API_KEY` / `LLM_<CHANNEL>_API_KEYS` | Secrets | Key fields must be in Repository Secrets; same-name Variables are not read by the workflow. |
| `LLM_<CHANNEL>_EXTRA_HEADERS` | Secrets or Variables | JSON strings; when containing auth, tenant, organization, or private gateway info, should be in Secrets. |
| `LITELLM_CONFIG` | Variables or Secrets | YAML file path; when used with `LITELLM_CONFIG_YAML`, the workflow writes to this path. |
| `LITELLM_CONFIG_YAML` | Secrets preferred | YAML content itself may contain private gateways or headers, recommended in Secrets. |
| `LLM_USAGE_HMAC_SECRET` | Secrets | Optional; only configure the same high-entropy random key when cross-deployment usage message HMAC comparison is needed, e.g., `openssl rand -hex 32`; do not put in Variables or commit to version control. |
| `LLM_USAGE_HMAC_KEY_VERSION` | Variables or Secrets | Optional; update version tag when rotating `LLM_USAGE_HMAC_SECRET` to avoid miscomparing HMACs generated by different keys. |

The default workflow already explicitly maps `primary`, `secondary`, `aihubmix`, `anspire`, `deepseek`, `dashscope`, `zhipu`, `moonshot`, `minimax`, `volcengine`, `siliconflow`, `openrouter`, `gemini`, `anthropic`, `openai`, `ollama`, `hermes`; `mimo` is not mapped in the default workflow. When using `mimo` (or any unmapped channel name), besides configuring same-name `LLM_<CHANNEL>_*` in Variables/Secrets, you also need to add corresponding env mappings in the workflow; local `.env`, Docker, and self-hosted scripts are not affected by this limitation.

When rolling back HMAC telemetry explicit configuration, remove `LLM_USAGE_HMAC_SECRET` and restore or delete `LLM_USAGE_HMAC_KEY_VERSION`; when left empty, the system returns to the default behavior of locally generating `.llm_usage_hmac_secret`.

Ollama's default Base URL `http://127.0.0.1:11434` is primarily for local, Docker, or self-hosted runners that can access that service. GitHub-hosted runners typically don't have a local Ollama service, so configuring `LLM_CHANNELS=ollama` directly will likely fail to connect.

### Hermes Local HTTP Generation (Phase 3)

Hermes is a reserved local HTTP generation preset, only enabled via `LLM_CHANNELS=hermes`. Default protocol is `openai`, default address is `http://127.0.0.1:8642/v1`, default model is `hermes-agent`:

```env
LLM_CHANNELS=hermes
LLM_HERMES_PROTOCOL=openai
LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1
LLM_HERMES_API_KEY=sk-local-hermes
LLM_HERMES_MODELS=hermes-agent
LITELLM_MODEL=openai/hermes-agent
```

Phase 3 only supports standard analysis / JSON generation, not stream/SSE, tools, Vision, Agent tools, remote Hermes, or process lifecycle management. `LLM_HERMES_API_KEY` should come from local `.env`, runtime config, or GitHub Secrets; do not write it to the repository. Hermes only allows loopback `/v1` endpoints; `localhost` is normalized to `127.0.0.1`, and `LLM_HERMES_API_KEYS` and `LLM_HERMES_EXTRA_HEADERS` are not supported. The Web settings page clears these two legacy fields and displays a warning when saving the reserved Hermes channel; to restore old values, use `.env` backup, Git history, or desktop export backup, but non-empty multi-Key / Extra Headers will still be rejected by the backend.

In GitHub Actions, `127.0.0.1` on GitHub-hosted runners refers to the runner itself, not the user's machine. Only self-hosted runners or same-machine services can access local Hermes; otherwise connection will fail.

## Common Errors and Handling Recommendations

| `details.reason` / Symptom | Common Cause | Recommended Action |
| --- | --- | --- |
| `missing_api_key` | API Key is empty, or `API_KEYS` comma-separated values have no non-empty segments. | Enter at least one valid key; exceptions for local Ollama or localhost compatible services. |
| `api_key_rejected` | Provider returned 401 / 403; key invalid, insufficient permissions, or project not enabled. | Re-copy the key; check account, project, organization, region, and model permissions. |
| `insufficient_balance` | Insufficient balance, billing not enabled, or quota exhausted. | Check balance, billing status, and model plans in the provider console. |
| `quota_exceeded` | Account or organization quota exhausted. | Check plans, project quota, organization quota, and provider billing page. |
| `rate_limit` | RPM / TPM / concurrency limit triggered. | Reduce concurrency, switch to a lighter model, or increase limits in the console. |
| `timeout` | Request timed out; may be slow network, slow provider response, or local service not responding. |
