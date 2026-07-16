# LLM (large model) Configuration Guide

welcome！Whether you are new to AI novice novice，Still proficient in various API veteran of high game，This guide can help you quickly convert large models（LLM）run。

This project provides a unified AI Model access experience，Support mainstream official API、OpenAI Compatible with platforms and native models。The bottom layer consists of [LiteLLM](https://docs.litellm.ai/) drive，But most users just need to understand“Choose a service provider、fill in API Key、Master selection model/channel”This default path。In order to take care of users at different stages，we designed“Three levels of priority”Configuration，Just choose the method that suits you best according to your needs。

If you are choosing a specific service provider、Configuration GitHub Actions Secrets / Variables、troubleshooting `details.reason` Error or prepare to rollback configuration，Please check first [LLM Service Provider Configuration Guide](./llm-providers.md)。This document is maintained centrally provider Default、Actions Variable comparison、Runtime capability detection boundaries and common error handling suggestions。

> of this page provider/model/Base URL Note that no external compatibility semantics are added this time，Only used to synchronize existing network agreements；The actual compatibility judgment is still based on the current warehouse lock dependency and runtime implementation.：
> - dependency boundary：`litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（with `requirements.txt` consistent）。
> - Compatible verification entrance：`tests/test_system_config_service.py`、`tests/test_system_config_api.py` And the existing front-end model configuration page regression use case。
> - fallback path：priority use `.env` Configuration backup + `POST /api/v1/system/config/import` restore；You can also manually backfill the old `LITELLM_MODEL` / `LLM_*` / `AGENT_LITELLM_MODEL` / `VISION_MODEL` / `LLM_TEMPERATURE` / `LLM_USAGE_HMAC_*`。

> **Description**：This page is for provider/model/base URL The instructions simultaneously use the current dependency constraints and historical conventions.，Just to supplement the documentation，No new runtime is introduced provider、model or Base URL behavior change。

---

## Quick navigation：Which section should you watch?？

1. **【Newbie】** "I just want to get the system running quickly，The simpler the better！" -> [guide the way【Method one：Extremely simple model configuration】](#Method 1: extremely simple model configuration suitable for novices)
2. **【Advanced user】** "I have several Key，Want to configure a backup model，Also need to change the custom URL(Base URL)。" -> [guide the way【Method 2：channel(Channels)Mode configuration】](#Method 2 channelchannelsMode configuration is suitable for advanced multi-models)
3. **【Advanced player】** "I want to do complex load balancing、Request routing、Even multi-heterogeneous platforms are highly available！" -> [guide the way【Method three：YAML Advanced configuration】](#Method threeyamlAdvanced configuration suitable for veteran customization)
4. **【local model】** "I want to use Ollama local model！" -> [guide the way【Example 4：Use Ollama local model】](#Example-4Use-ollama-local model)
5. **【visual model】** "I want to identify stock symbols using pictures！" -> [guide the way【Extended functions：View diagram model(Vision)Configuration】](#Extended function to view picture modelvisionConfiguration)

---

## Generation Backend（Phase 4）

Generation backend It's a normal analysis、Market review and `generate_text()` The outer runtime selection of。The default is still `litellm`，Zero-configuration path remains consistent with historical behavior；`codex_cli` / `claude_code_cli` / `opencode_cli` is explicit opt-in of local CLI backend，Currently marked as **experimental/limited**。

```env
GENERATION_BACKEND=litellm
GENERATION_FALLBACK_BACKEND=litellm
GENERATION_BACKEND_TIMEOUT_SECONDS=300
GENERATION_BACKEND_MAX_OUTPUT_BYTES=1048576
GENERATION_BACKEND_MAX_CONCURRENCY=1
LOCAL_CLI_BACKEND_MAX_CONCURRENCY=1
# Optional：Leave blank to use this machine OpenCode Default model；Configure as --model Override value passed to OpenCode。
# OPENCODE_CLI_MODEL=provider/model
AGENT_GENERATION_BACKEND=auto
```

- `GENERATION_BACKEND=litellm|codex_cli|claude_code_cli|opencode_cli`。local CLI backend Yes generation backend，No LiteLLM provider；don't write `LITELLM_MODEL=codex_cli/...`、`LITELLM_MODEL=claude_code_cli/...` or `LITELLM_MODEL=opencode_cli/...`。
- `GENERATION_BACKEND=opencode_cli` Not transmitted by default `--model`，by this machine OpenCode Use your own default model configuration；`OPENCODE_CLI_MODEL` Just optional override value，Only configured as a single `--model` Parameters passed to OpenCode。provider Certification、Account and model availability are determined by the local OpenCode Responsible for own configuration；DSA Do not take over these configurations。
- `GENERATION_FALLBACK_BACKEND` Default when not configured `litellm`；local `.env` explicit null value `GENERATION_FALLBACK_BACKEND=` Indicates disabled backend-level fallback；primary with fallback At the same time, it is resolved as no-op。Warehouse comes with GitHub Actions workflow This variable is exported explicitly when not configured `litellm`，If you want to be in Actions disabled in backend fallback，please put fallback set to primary backend，For example `GENERATION_BACKEND=codex_cli` + `GENERATION_FALLBACK_BACKEND=codex_cli`。
- `GENERATION_BACKEND=codex_cli|claude_code_cli` and no Gemini/OpenAI/Anthropic/DeepSeek API Key time，Ordinary analysis and market review will still try local CLI backend；If corresponding executable does not exist，will return a structured `command_not_found`，Will not report“API Key Not configured”。
- current `codex_cli` preset Use `codex exec --output-last-message <temp-file> -` Read the final response；Codex CLI will still print the same final response to stdout，DSA will follow stdout Remove this duplicate content from diagnostic preview and output size statistics，Not involved in main analysis JSON parse。For the official basis, see [Codex non-interactive mode](https://developers.openai.com/codex/noninteractive) with [Codex CLI command line options](https://developers.openai.com/codex/cli/reference)。This warehouse currently only verifies `codex-cli 0.142.0`，Do not declare wider minimum version；if CLI Version not supported preset parameters，DSA will return a structured `capability_unsupported` / `cli_contract_unsupported` Diagnosis，and in configuration backend fallback fall back to `litellm`。
- current `claude_code_cli` preset Use `claude --safe-mode --tools "" --disallowedTools "mcp__*" --strict-mcp-config --no-session-persistence --output-format json -p <static instruction>`，complete DSA prompt Pass stdin incoming。DSA only from Claude JSON envelope of `result/success` Final field extraction text；If subsequently enabled `--json-schema`，schema mode Must be extracted `structured_output`，and will continue to pass DSA Existing JSON validator、minimal parser contract、`_parse_response()`、integrity retry、placeholder fill and usage telemetry。Parameter basis see [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)；Ben PR smoke The verified version is `claude 2.1.177 (Claude Code)`，Do not declare wider minimum version。
- current `opencode_cli` preset Use `opencode --pure run --format json [--model <OPENCODE_CLI_MODEL>] <static instruction> --file <temp prompt file>`；Explicit configuration only `OPENCODE_CLI_MODEL` Added only when `--model`，complete DSA prompt Write to a temporary file with controlled permissions，Do not enter argv。DSA Only parse OpenCode JSON event There are no tool events in the output `text` content，and require normal `step_finish`；appear `tool_use`、`error`、`question`、`permission` Waiting for events will fail structurally。Parameter basis see [OpenCode CLI reference](https://opencode.ai/docs/cli)，Project configuration merge semantics see [OpenCode config reference](https://opencode.ai/docs/config)；Ben PR smoke The verified version is `opencode 1.17.11`，Do not declare wider minimum version。
- local CLI backend Not supported streaming。Request stream will be automatically downgraded to non-stream，will not be returned for this reason `capability_unsupported`。
- local CLI usage Usually not available，The system will not write fake 0 token、fake cost or fake cache telemetry。
- local CLI Enforcement caps have hard bounds：`GENERATION_BACKEND_TIMEOUT_SECONDS` maximum `3600`，`GENERATION_BACKEND_MAX_OUTPUT_BYTES` maximum `33554432`，`GENERATION_BACKEND_MAX_CONCURRENCY` maximum `16`，`LOCAL_CLI_BACKEND_MAX_CONCURRENCY` maximum `4`。Diagnosis stdout/stderr When the total with the final response exceeds the output upper limit, a structured `output_too_large`；Yes `--output-last-message` preset，stdout Final responses printed repeatedly in will not be counted twice，Nor will it act `stdout_preview` exposed。
- local CLI The default concurrency is 1；The effective concurrency is `min(LOCAL_CLI_BACKEND_MAX_CONCURRENCY, GENERATION_BACKEND_MAX_CONCURRENCY)`，Not inherited `MAX_WORKERS`。
- `AGENT_GENERATION_BACKEND=auto` Will not inherit `GENERATION_BACKEND` of local CLI value；Agent Tool call continues to use LiteLLM。Web The settings page is only exposed `auto|litellm`；handwriting `AGENT_GENERATION_BACKEND=codex_cli|claude_code_cli|opencode_cli` Not realized text-only Agent mode，will return clear unsupported tool-calling Diagnosis。
- Web The settings page's build backend quick check only reads saved `.env`、Runtime botched values and unsaved drafts；it won't write configuration、Reload runtime，It will also not initiate a real model request。`available` It only means that the current configuration has the conditions to try to run。JSON Smoke testing is a separate explicit operation，Will use server side fixed JSON prompt words and schema Initiate a real build backend request，for validating extractors、JSON contract、timeout、Output limits and usage-unavailable Semantics。
- `GET /api/v1/system/config/generation-backends/status` Read only saved configurations；Unsaved draft needs to be called `POST /api/v1/system/config/generation-backends/status/preview` or `POST /api/v1/system/config/generation-backends/smoke-test`。Masked key fields will continue to inherit the saved value。`health_status` with `last_error_code/message` Only represents the results of this calculation，Not a historical lasting health state。

### Local CLI local backend Privacy and boundaries

- local CLI Backend Not equal to offline model；Codex / Claude Code / OpenCode The service behind it may handle stock symbols、News、Position context、analysis prompt、Draft reports, etc.。
- Docker、cloud server、CI Not naturally owned by your machine CLI Login status。
- GitHub Actions Only responsible for transparent transmission of configuration values，No installation or local login CLI；if in Actions in opt-in local CLI backend，runner You should see structured failures when the executable or login state is missing。
- DSA Do not read Codex/Claude/OpenCode credential File，But the child process may read CLI Self login status。
- macOS from Finder/Dock Not inherited when starting desktop shell PATH；Packaging the desktop side will add common features when starting the backend. Homebrew path（Such as `/opt/homebrew/bin`、`/usr/local/bin`）。If the settings check still prompts that it cannot be found CLI executable file，Please exit completely and reopen DSA；open CLI The interactive window does not change the running backend PATH。
- DSA By default, only the minimum operating environment is inherited，and reject wildcard inheritance `CLAUDE_*`、`ANTHROPIC_*`、`OPENCODE_*`、`OPENAI_*`、`GOOGLE_*`、`GEMINI_*`、`AWS_*`、`AZURE_*`、`VERTEX_*`、`*_API_KEY`、`*_AUTH_TOKEN`、`*_ACCESS_TOKEN`、`*_SECRET`、`*_PASSWORD`，lower DSA API keys、provider tokens and webhook tokens leakage risk。`CODEX_HOME` is for compatibility with existing Codex CLI Exact exceptions to login directory retention；will not be restored `CODEX_CLI_*` Wildcard。
- `opencode_cli` will be temporary cwd Write minimal project `opencode.json` to turn off sharing、Automatic updates、Snapshot and common tool permissions，But OpenCode resolved config May still contain user local global configuration；Runtime security boundaries depend on `--pure`、env denylist、prompt file permissions and event extractor fail-closed。
- Web The settings page only exposes security preset，Not allowed to submit any command / argv / shell string。
- `codex_cli` / `claude_code_cli` / `opencode_cli` still marked as experimental/limited；if your CLI The version does not support the verified non-interactive output contract of this repository，DSA will return a structured `capability_unsupported`、`cli_contract_unsupported`、`invalid_json`、`schema_validation_failed` or corresponding backend error，and in configuration backend fallback fall back to `litellm`。When the risk of version drift cannot be accepted，please keep `GENERATION_BACKEND=litellm`。
- `opencode_cli` Not supported OpenCode serve / web / ACP / MCP / attach / `--dangerously-skip-permissions`；DSA No OpenCode final text As Agent tool success。

## Method one：Extremely simple model configuration（Suitable for novices）

**target：** Just remember to fill in API Key and the corresponding model name can be used immediately。No need to fiddle with complicated concepts。

If you only plan to use one model，This is the fastest way。Open the project root directory `.env` File（if not，Make a copy `.env.example` and renamed to `.env`）。

### Anspire Open Example：

> 💡 **Recommended [Anspire Open](https://open.anspire.cn/?share_code=QFBC0FYC)**：Support Chinese optimized online search and OpenAI-compatible Path integrated experience，Suitable for preparing only one Key of users。
> - The following is a configuration example，Model and gateway availability are determined by account permissions and Anspire The control panel shall prevail；Documentation examples are not a substitute for actual connectivity verification。
> - It is recommended to Web Click on the settings page“test connection”Perform actual authentication and model availability checks，Avoid using document defaults directly as availability promises。

```env
# Anspire Open API Keys（Support multiple，comma separated）
# Get: https://open.anspire.cn/?share_code=QFBC0FYC
# When the default priority conditions are met，The system will reuse the Key Handle searches with LLM（Sample backend paths only）。
# Example model：Doubao-Seed-2.0-lite；Example gateway：https://open-gateway.anspire.cn/v6
ANSPIRE_API_KEYS=sk-xxxxxxxxxxxxxxxx
# Optional：Switch models or gateways by console availability
# ANSPIRE_LLM_MODEL=Doubao-Seed-2.0-pro
# ANSPIRE_LLM_BASE_URL=https://open-gateway.anspire.ai/v6
```

### Example 1：Use common third-party platforms（Compatible OpenAI Format，Recommended）

Most third-party aggregation platforms on the market now（For example silicon based flow、AIHubmix、Ali Bailian、Wisdom spectrum, etc.）All compatible OpenAI interface format。As long as the platform provides API Key and Base URL，You can configure it brainlessly according to the following format：

```env
# Fill in the information provided by the platform API Key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
# Fill in the interface address of the platform (very important：It usually ends with /v1)
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
# Fill in the specific model name on the platform（very important：Note that it must be added before openai/ Prefix helps system identification）
LITELLM_MODEL=openai/deepseek-ai/DeepSeek-V3 
```

### Example 2：Use DeepSeek Official interface
```env
# Fill in where you are DeepSeek Apply through the official platform API Key
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```
*Compatibility tips：When only filling in this line，The system will still use `deepseek/deepseek-chat` And the log prompts migration。*
`deepseek-chat` / `deepseek-reasoner` Still available for compatibility with older configurations，But DeepSeek Officially marked as 2026/07/24 later abandoned；New configuration recommendations passed Web fast channel or explicit `LITELLM_MODEL=deepseek/deepseek-v4-flash` Migrate to `deepseek-v4-flash` / `deepseek-v4-pro`。

### Example 3：Use Gemini free API
```env
# Fill in what you got Google Gemini Key
GEMINI_API_KEY=AIzac...
```

### Example 4：Use Ollama local model
```env
# Ollama No need API Key，Run locally ollama serve Can be used after
OLLAMA_API_BASE=http://localhost:11434
LITELLM_MODEL=ollama/qwen3:8b
```

> **important**：Ollama Must use `OLLAMA_API_BASE` Configuration，**Don't**Use `OPENAI_BASE_URL`，Otherwise, the system will incorrectly splice URL（Such as 404、`api/generate/api/show`）。remote Ollama time，will `OLLAMA_API_BASE` Set to actual address（Such as `http://192.168.1.100:11434`）。The current dependency constraints are `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（with requirements.txt consistent）。

> **Congratulations！Novices can run the program after reading this.！**
> I want to test it and see if it works.？Open the command line input in the home directory：`python scripts/check_env.py --llm`

---

## Method 2：channel(Channels)Mode configuration（Suitable for advanced/multiple models）

**target：** I have several for different platforms Key Want to mix it up，If the main model is stuck/The network is down，I want it to automatically switch to the alternate model。

**The web page can be configured directly：** You can start the program after，in **Web UI of“System settings -> AI model -> AI Model access”** Very intuitive visual configuration in！

> **New edition editing experience supplement**：for DeepSeek、Ali Bailian（DashScope）and other compatible OpenAI `/v1/models` channels，The settings page now supports direct clicks“Get model”，from `{base_url}/models` Pull available models and multi-select；The bottom layer will still be saved as the original `LLM_{CHANNEL}_MODELS=model1,model2` comma format。If the channel does not support this interface、Authentication failed or temporarily unreachable，You can still continue to fill in the model list manually，Does not affect saving。

### First startup configuration status

The backend provides a read-only status interface `GET /api/v1/system/config/setup/status`，Used to determine whether the most basic configurations in the first closed-loop startup are ready.：LLM main channel、Agent channel、Optional stocks、Notification channels and local storage。This interface only reads saved `.env` with current process environment variables，Runtime configuration will not be reloaded、write `.env`、Test real models or create database files；Front-end wizard and follow-up smoke run Can be gradually accessed based on this interface。

### Web Channel Editor Compatibility / Migrate / Fallback rules

- in default provider / Base URL / The example model is only for**Initialize form**；When the order is actually placed, it will still be the one you currently entered. `LLM_{CHANNEL}_PROTOCOL`、`LLM_{CHANNEL}_BASE_URL`、`LLM_{CHANNEL}_MODELS`、`LLM_{CHANNEL}_API_KEY(S)`，It will not be secretly changed to something else in the background. provider name or URL。
- settings page“Get model”only right `OpenAI Compatible` / `DeepSeek` Channel call `{base_url}/models`；“test connection”By default, only one minimum chat request is initiated for the first item in the model list.，And display the backend normalized results in the results `resolved_model`。If return `details.reason=model_access_denied`（For example Issue #1208 have been observed in SiliconFlow / OpenAI Compatible by LiteLLM Return `Model disabled`），Please think of it as based on provider copywriting best-effort Model availability diagnostics，Prioritize to confirm whether the model is already in the current account/key Open next，If necessary, adjust the order of the models or remove unavailable models and try again.；Not covered or semantically different provider The copywriter will continue to make thorough diagnoses。Optional“Runtime capability testing”Must be triggered after explicit selection by the user，Will initiate additional JSON / tools / stream / vision smoke Request，The result only represents the current account、model and endpoint once best-effort Detection。The above detection returns `stage / error_code / details / latency_ms / capability_results` Only for structured diagnostic prompts，**Won't write back** `.env`，Will not prevent saving。
- If return `details.reason=provider_blocked`，Indicates that the service provider or transit gateway has explicitly intercepted this request.；It is different from local network / TLS exception and `model_access_denied`，Account risk control should be checked as a priority、Region or request source restrictions、Model permissions、Agency gateway policy and content security policy。
- Runtime capability detection will produce real LLM Request，may bring token / Image input fee、RPM/TPM Current limiting、Insufficient balance or timeout。Detection failure may come from account permissions、The model is not activated、endpoint area、balance、Service provider compatibility layer or LiteLLM conversion path，does not mean that provider The corresponding capability is not supported globally。P3 not true for all provider do online smoke；Compatibility basis comes from current dependency constraints `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` down LiteLLM `completion()` / OpenAI I/O format / streaming / exception mapping，and OpenAI Chat Completions of JSON mode、tool calling、streaming and vision input shape。
- Relevant external sources：LiteLLM Python SDK / OpenAI I/O format / streaming / exception mapping：<https://docs.litellm.ai/>；LiteLLM OpenAI-compatible routing：<https://docs.litellm.ai/docs/providers/openai_compatible>；OpenAI Chat Completions：<https://platform.openai.com/docs/api-reference/chat/create>；JSON mode：<https://platform.openai.com/docs/guides/structured-outputs?api-mode=chat>；tool calling：<https://platform.openai.com/docs/guides/function-calling?api-mode=chat>；streaming：<https://platform.openai.com/docs/guides/streaming-responses?api-mode=chat>；vision input：<https://platform.openai.com/docs/guides/images-vision?api-mode=chat>。
- When saving a channel，Only this submission will be updated key；The entire old configuration will not be silently migrated due to switching channel modes。The only one who will be**Synchronous cleaning**is a runtime model reference：if `LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`VISION_MODEL` or `LITELLM_FALLBACK_MODELS` Points to a model that no longer exists in the currently enabled channel，The settings page will clear these invalid references before saving./Remove，Avoid pointing to invalid models at runtime；Even if the channel is currently enabled without any selectable models，It will also clean up missing legacy Key Supported hosting provider old value。`cohere/*`、`google/*`、`xai/*` This type of direct connection model is only used to illustrate the history `direct-env` Compatible with retention semantics，Not equal to availability promise，Please click on the official model of each manufacturer for availability./API Documents are then physically verified。
- Backend consistency basis：Configure the verification link in `SystemConfigService._validate_llm_runtime_selection`（`src/services/system_config_service.py`）pass `_uses_direct_env_provider`（`src/config.py`）Determine runtime source；Currently only `gemini`、`vertex_ai`、`anthropic`、`openai`、`deepseek` Belongs to hosting key provider，`cohere`、`google`、`xai` Not in the whitelist，Therefore it will remain as a direct connection model。
- Fallback methods are also kept to a minimum：Change the corresponding channel model list back and select the main model again. / fallback，Or export the backup directly using the desktop / Manual `.env` Restore previous `LLM_*`、`LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`VISION_MODEL`、`LLM_TEMPERATURE`、`LLM_USAGE_HMAC_*` That’s it，No need to run additional migration scripts。Web If the client needs to restore the configuration，You can also enable administrator authentication in（`ADMIN_AUTH_ENABLED=true`）After passing `POST /api/v1/system/config/import` rollback。
- The dependency constraints of the current warehouse on this link are `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（see `requirements.txt`）；Regression coverage includes `tests/test_system_config_service.py`、`tests/test_system_config_api.py` and `apps/dsa-web/src/components/settings/__tests__/LLMChannelEditor.test.tsx`。

> **external provider Example model description**：`cohere/*`、`google/*`、`xai/*` Wait provider The prefix value is only used to describe the current save cleanup semantics，**does not represent a model-by-model availability guarantee within this dependency constraint**。Specific model names in documentation or tests are examples of configuration-preserving behavior.，Not a production recommendation；For actual availability, please refer to the corresponding official model document.，And combined with warehouse dependency constraints `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` Review。

### Fallback and Compatibility Evidence

- Dependency constraints and silent cleanup scope：in `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` down，Save only clean up the invalid ones runtime model reference（`LITELLM_MODEL`、`AGENT_LITELLM_MODEL`、`VISION_MODEL`、`LITELLM_FALLBACK_MODELS`），`cohere/*`、`google/*`、`xai/*` The non-channel direct connection model will be retained.。
- Fallback：You can directly use the desktop to export the backup and pass `POST /api/v1/system/config/import` restore；Manual handle is also available `.env` Chinese history `LITELLM_* / AGENT_LITELLM_MODEL / VISION_MODEL / LLM_TEMPERATURE / LLM_USAGE_HMAC_*` It will take effect after restarting after backfilling.。Web Please enable administrator authentication before executing the import.（`ADMIN_AUTH_ENABLED=true`）。
- fallback regression evidence：`tests/test_system_config_service.py::test_import_desktop_env_restores_runtime_models_after_cleanup` Cover“After cleaning, use the desktop to export the backup and restore it. runtime Quote”。
- direct connection provider regression evidence：`tests/test_system_config_service.py::SystemConfigServiceTestCase::test_validate_accepts_minimax_model_as_direct_env_provider`、`test_validate_accepts_cohere_model_as_direct_env_provider`、`test_validate_accepts_google_model_as_direct_env_provider`、`test_validate_accepts_xai_model_as_direct_env_provider` Direct coverage provider Preserve semantics。
- Front-end regression command：`cd apps/dsa-web && npm run lint && npm run build && npm run test -- src/components/settings/__tests__/LLMChannelEditor.test.tsx`。
- Recommended fallback operation link（Contains settings page refresh）：Export desktop backup first，`POST /api/v1/system/config/import` After importing，pass again `GET /api/v1/system/config` Refresh page configuration，Confirm again `LITELLM_MODEL / AGENT_LITELLM_MODEL / VISION_MODEL / LLM_TEMPERATURE / LLM_USAGE_HMAC_*` Continue to use it after it is consistent with the model list.。

### Commonly used official document sources（Used to check presets provider / Base URL / Model naming）

- OpenAI Compatible normative（LiteLLM）：<https://docs.litellm.ai/docs/providers/openai_compatible>
- OpenAI official：<https://platform.openai.com/docs/api-reference/chat>
- DeepSeek official：<https://api-docs.deepseek.com/>
- Anspire Open：<https://open.anspire.cn/?share_code=QFBC0FYC>
- Ali Bailian DashScope Compatibility mode：<https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope>
- Moonshot / Kimi official：<https://platform.moonshot.ai/docs/guide/compatibility>
- Anthropic official：<https://docs.anthropic.com/en/api/messages>
- Gemini official：<https://ai.google.dev/gemini-api/docs/openai>
- Cohere official：<https://docs.cohere.com/>
- Cohere API Reference：<https://docs.cohere.com/reference/>
- Cohere LiteLLM Provider：<https://docs.litellm.ai/docs/providers/cohere>
- Google Gemini API with model：<https://ai.google.dev/gemini-api/docs/openai>、<https://ai.google.dev/gemini-api/docs/models>
- Google LiteLLM Provider：<https://docs.litellm.ai/docs/providers/gemini>
- xAI official：<https://docs.x.ai/docs>
- xAI LiteLLM Provider：<https://docs.litellm.ai/docs/providers/xai>
- Ollama official：<https://github.com/ollama/ollama/blob/main/docs/api.md>

If it is not convenient to use the web version，in `.env` The configuration in the file is also very smooth，It allows you to manage multiple third-party platforms simultaneously。The rules are as follows：

1. **First declare how many channels you have**：`LLM_CHANNELS=Channel name1,Channel name2`
2. **Fill in the configuration for each channel separately**（Note all capital letters）：`LLM_{Channel name}_XXX`

### Example：Configure at the same time DeepSeek and a transfer platform，and set up a backup switch
```env
# 1. Turn on channel mode，It is stated that there are two channels here：deepseek and aihubmix
LLM_CHANNELS=deepseek,aihubmix

# 2. Channel one：Configuration DeepSeek official
LLM_DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_DEEPSEEK_API_KEY=sk-1111111111111
LLM_DEEPSEEK_MODELS=deepseek-v4-flash,deepseek-v4-pro

# 3. Channel 2：Configure a common aggregation relay API
LLM_AIHUBMIX_BASE_URL=https://api.aihubmix.com/v1
LLM_AIHUBMIX_API_KEY=sk-2222222222222
LLM_AIHUBMIX_MODELS=gpt-5.5,claude-sonnet-4-6

# 4. 【key】Specify primary and backup model lists
# Usually preferred deepseek This model：
LITELLM_MODEL=deepseek/deepseek-v4-flash
# Optional：Agent Ask stocks to specify the main model separately（Leave blank to inherit the main model）
AGENT_LITELLM_MODEL=deepseek/deepseek-v4-pro
# If the main model crashes, immediately try the following two backup models one by one.：
LITELLM_FALLBACK_MODELS=openai/gpt-5.4-mini,anthropic/claude-sonnet-4-6
```

### Example：Ollama channel model（local model，No need API Key）
```env
# 1. Turn on channel mode，Statement ollama channel
LLM_CHANNELS=ollama

# 2. Configuration Ollama address（local default 11434 port）
LLM_OLLAMA_BASE_URL=http://localhost:11434
LLM_OLLAMA_MODELS=qwen3:8b,llama3.2

# 3. Specify the main model
LITELLM_MODEL=ollama/qwen3:8b
```

### Example：Hermes local HTTP Generation（Phase 3）
```env
LLM_CHANNELS=hermes
LLM_HERMES_PROTOCOL=openai
LLM_HERMES_BASE_URL=http://127.0.0.1:8642/v1
LLM_HERMES_API_KEY=sk-local-hermes
LLM_HERMES_MODELS=hermes-agent
LITELLM_MODEL=openai/hermes-agent
```

Hermes It is a reserved channel name，Only supports local machine loopback `/v1` OpenAI-compatible generation。Phase 3 Only verify normal analysis with JSON output；Not supported Stream/SSE、Tools、Vision、Agent tools、remote Hermes or process life cycle management。Hermes API Key Only a single `LLM_HERMES_API_KEY`，Do not configure `LLM_HERMES_API_KEYS` or `LLM_HERMES_EXTRA_HEADERS`。if Hermes Illegal configuration，The system will block legacy provider silent fallback，Avoid mistakenly switching to external models。Web Save settings page reserved Hermes channel time，will explicitly clear the old `LLM_HERMES_API_KEYS` / `LLM_HERMES_EXTRA_HEADERS` and return warning；If you need to restore the old value，Please start from `.env` backup、Git Manual restore of historical or desktop export backup，But Phase 3 Will still reject non-empty longs Key / Extra Headers Configuration。

### MiniMax Instructions for filling in the channel model

- if you pass OpenAI Compatible channel access MiniMax，Please fill it in directly in the channel model `minimax/<Model name>`，For example `minimax/MiniMax-M1`。
- Web Main model in settings page、Agent master model、Fallback、Vision The drop-down will keep this value and display it as it is.，It will no longer be mistakenly rewritten as `openai/minimax/<Model name>`。

### Ask about stocks Agent / LiteLLM Configuration compatibility instructions

- Ask about stocks Agent The runtime follows the same three-tier priority as normal analysis：`LITELLM_CONFIG`（LiteLLM YAML）> `LLM_CHANNELS` > legacy provider keys。As long as the upper-level configuration is valid, it will take effect，The lower configuration will no longer participate in this request.。
- YAML mode，Agent Direct reuse LiteLLM `model_list` / `model_name` routing semantics；In channel mode，Read first `AGENT_LITELLM_MODEL`，Inherited when left blank `LITELLM_MODEL`，Press again `LITELLM_FALLBACK_MODELS` continue fallback。
- If you don't enable YAML / Channels，and `AGENT_LITELLM_MODEL` Also leave blank，But the local area still retains legacy environment variables，Ask about stocks Agent The old configuration will still be inherited：`GEMINI_API_KEY + GEMINI_MODEL` -> `gemini/<model>`，`OPENAI_API_KEY + OPENAI_MODEL` -> `openai/<model>`，`ANTHROPIC_API_KEY + ANTHROPIC_MODEL` -> `anthropic/<model>`。
- This compatibility logic only enhances“Keep the real error reason in the backend when failure occurs”and“Not configured LLM give a more specific diagnosis”，**No**Delete silently、Clear、Migrate or adapt your existing `GEMINI_*` / `OPENAI_*` / `ANTHROPIC_*` / `LITELLM_*` Configuration。
- If there is nothing valid in the current environment Agent model link，The stock inquiry page will continue to return with failure semantics，And directly display the real configuration diagnosis of the backend；It can be restored after filling any valid model source.，No need to execute additional configuration migration scripts。
- The recommended new configuration method is still to set it explicitly `LITELLM_MODEL` / `AGENT_LITELLM_MODEL` or use `LLM_CHANNELS`；legacy provider keys Currently reserved as a compatible fallback path，Convenient old `.env`、local macOS The development environment and historical deployments continue to run smoothly。

### Asking stocks visible conversation context compression

By default，Question stocks still only inject the latest according to historical behavior 20 visible conversations。Long session required token time，Can be turned on：

```env
AGENT_CONTEXT_COMPRESSION_ENABLED=true
AGENT_CONTEXT_COMPRESSION_PROFILE=balanced
# Leave blank to follow profile preset
AGENT_CONTEXT_COMPRESSION_TRIGGER_TOKENS=
AGENT_CONTEXT_PROTECTED_TURNS=
```

Compression only handles `session_id` Visible to the next user `user` / `assistant` text history，Not processed provider trace、thinking blocks、tool calls or tool results，It will not change the transparent transmission called by the same round tool.。third gear preset They are `cost`（6000 tokens / protect 2 wheel）、`balanced`（12000 / 4）and `long_context_raw_first`（24000 / 6）；trigger / protected If left empty, follow the current profile，Override when filled in explicitly profile。

Ask about stocks single-agent An additional path will be maintained provider-aware trace split track，used for DeepSeek V4 thinking + tool-call Inter-turn protocol playback：Only the same round appears at the same time `tool_calls` with `reasoning_content` will only press the current `session_id + provider + model` Save recent 3 minimum agreement materials，And insert the corresponding visible data back in the original timing in the next round. assistant before replying。the trace It can only be kept as it is or discarded in its entirety.，Do not participate in summary、Do not write Web Conversation message、No new addition `.env` Configuration；model/provider no match、The anchor point has been summary If coverage or budget is insufficient, the entire paragraph will be skipped.。Claude extended thinking This round only covers adapter/storage level opaque `thinking` / `redacted_thinking` / `signature` blocks plumbing with offline fixture，No declaration of production end-to-end support；multi-agent trace Injection is still follow-up。External agreement bases include DeepSeek thinking mode Documentation（<https://api-docs.deepseek.com/guides/thinking_mode>）and Anthropic Claude extended thinking Documentation（<https://platform.claude.com/docs/en/docs/build-with-claude/extended-thinking>），LiteLLM The compatibility window still starts with `requirements.txt` of `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` Subject to。

### strict temperature Model compatibility instructions

- Moonshot Official description Kimi API Compatible OpenAI interface，Base URL Use `https://api.moonshot.ai/v1`：<https://platform.kimi.ai/docs/guide/kimi-k2-6-quickstart>
- LiteLLM official request OpenAI Compatible Channel model name usage `openai/` prefix：<https://docs.litellm.ai/docs/providers/openai_compatible>
- Moonshot The official compatibility document distinguishes between two fixed values：**thinking Mode fixed `1.0`，non-thinking Mode fixed `0.6`**；Passing other values will be rejected by the interface：<https://platform.moonshot.ai/docs/guide/compatibility#parameters-differences-in-request-body>
- OpenAI Chat Completions In specification `temperature` is an optional parameter；Yes GPT-5 / o Series etc. only accept models with default temperature，This item will be omitted at the request layer `temperature`，Let the server use the default value，rather than rewriting your `LLM_TEMPERATURE`：<https://platform.openai.com/docs/api-reference/chat/create>
- The runtime dependency constraints of the current warehouse are `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（see `requirements.txt`）；This compatible logic regression verified the main analysis according to this constraint.、Market review、Agent direct connection LiteLLM，And the channel connectivity test on the system settings page。
- Therefore, this project will press**Actual request pattern**normalization `kimi-k2.6` and its `kimi-k2.6-*` Variants：Default / thinking Path usage `temperature=1.0`；if your LiteLLM YAML It is explicitly written in the route alias. `litellm_params.extra_body.thinking.type: disabled`（or equivalent non-thinking Configuration），will automatically switch to `temperature=0.6`。you are here `.env` or Web saved in settings `LLM_TEMPERATURE` will not be rewritten。
- If the compatible platform returns an explicit parameter error for a new model that is not included（For example `temperature` Not supported、Only use the default `1.0`、`top_p` Not supported），When run, it will**current request**Make a parameter correction and try again；The policy will be cached in the current process only after the retry is successful.。The cache will not write back `.env`，After the service is restarted, it will be judged again according to the configuration and adaptation rules.。
- Streaming response to partial content that has been produced，The system will not switch parameters after half output；Still using the original“Same model non-streaming retry / fallback model”stable path，Avoid splicing together inconsistent answers。
- `SystemConfigService` in Web Save settings / Desktop `.env` When importing, only update what you submitted key，It won’t be because it’s cut to the strictest temperature Model is cleared silently、Migrate or rewrite existing `LLM_TEMPERATURE`；The temporary parameter policy in the channel test request will not be written back to the configuration file.。
- non-strict master model、not strict fallback And the request after switching back to the normal model，Still continue to use the temperature you configured；In other words, the old configuration does not need to be migrated，Switching models automatically restores the original behavior。
- For compatibility regression coverage in this repository, see：`tests/test_llm_channel_config.py`、`tests/test_market_analyzer_generate_text.py`、`tests/test_agent_pipeline.py`、`tests/test_system_config_service.py`。
- Minimal rollback method：Directly roll back this time LLM Changes related to parameter adaptation，No need to migrate existing ones separately `LLM_TEMPERATURE` Configuration。

### Compatibility and Fallback Checklist（press PR Audit caliber）

- runtime dependency constraints：`litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`（with `requirements.txt` consistent）。
- Regression verification entry：
  - Channel model discovery and connection：`tests/test_llm_channel_config.py`
  - Runtime source cleanup and recovery（Includes desktop export backup link）：`tests/test_system_config_service.py`
  - Interface verification and problem-oriented fields：`tests/test_system_config_api.py`
  - Setting page interaction and prompt after saving：`apps/dsa-web/src/components/settings/__tests__/LLMChannelEditor.test.tsx`
- Old configuration fallback path：`Desktop export backup -> /api/v1/system/config/import`，Or restore manually `LLM_* / LITELLM_* / AGENT_LITELLM_MODEL / VISION_MODEL / LLM_TEMPERATURE / LLM_USAGE_HMAC_*`；Web The same requirements are required before importing backup `ADMIN_AUTH_ENABLED=true`，Otherwise it will return 403。

> **Fatal pit avoidance instructions**：If you enable `LLM_CHANNELS`，Then you write it directly outside `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` will**All invalid（The system will always ignore）**！Both**Just choose one**，Never write both the novice mode and the channel mode, resulting in conflicts.。
> **Docker Note**：if you are `docker compose environment:` or `docker run -e` Explicitly passed in `LITELLM_MODEL`、`LLM_CHANNELS`、`LLM_DEEPSEEK_MODELS` equal variables，These environment variables will be overwritten after the container is restarted. Web settings page written `.env`，Deployment configuration needs to be modified simultaneously。

### Compatibility basis and rollback audit instructions（This time PR Adaptation instructions）

- The official and runtime compatibility basis adopts two layers：The first layer is the official interface semantics（LiteLLM OpenAI-compatible routing、OpenAI Chat Completions、Moonshot/Kimi Documentation and official model description）；The second layer is the current runtime semantics of this warehouse（`litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`）Actual error classification under。
- This compatible recovery only uses“Local runtime error classification + Single request correction retry + In-process cache”Strategy，Do not write `.env`、No configuration migration，Dynamic evasion does not support parameters only on the execution path（`temperature`、`top_p`、`presence_penalty`、`frequency_penalty`、`seed`）。To roll back，No additional migration commands required，Just restore the old value。
- Regression and evidence：`tests/test_llm_param_recovery.py`、`tests/test_system_config_service.py`、`tests/test_llm_channel_config.py`、`tests/test_system_config_api.py`、`tests/test_market_analyzer_generate_text.py`、`tests/test_agent_pipeline.py`；Desktop import and runtime cleanup rollback additionally `test_import_desktop_env_restores_runtime_models_after_cleanup` direct coverage。

---

### LLM usage HMAC Telemetry

P0a usage telemetry Will be actually sent message generate HMAC-SHA256 fingerprint，The same for subsequent judgments prompt/message Is the prefix stable?。This capability only writes to the local `llm_usage` record，Do not change prompt、provider parameters、cache hint、model output or fallback order。

Usage Sources are read in three layers：

- Read first provider / LiteLLM Public response fields `usage`。
- Next read LiteLLM Public response fields `usage_metadata`。
- read last `_hidden_params["usage"]`，This is LiteLLM private/internal of best-effort fallback，Not a stable public contract；When missing, it only represents usage/cache telemetry may be incomplete，It does not mean that the model request failed。

Cache token Normalization only does allowlisted best-effort normalization。The external field basis and runtime boundaries are as follows，Avoid putting official stability contracts、LiteLLM The current normalization behavior is compatible with this warehouse allowlist lumped together：

| Provider / Source | Read fields | Basis and boundaries | Coverage |
| --- | --- | --- | --- |
| OpenAI | `usage.prompt_tokens_details.cached_tokens` | official Prompt Caching Documentation description 1024 tokens The following will also be returned `cached_tokens=0`：<https://developers.openai.com/api/docs/guides/prompt-caching> | unit/mock Cover；Ben PR Not done OpenAI live smoke |
| Anthropic | `cache_creation_input_tokens` / `cache_read_input_tokens` / `input_tokens` | official Prompt Caching Document definition `total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens`：<https://platform.claude.com/docs/en/build-with-claude/prompt-caching> | unit/mock Cover；Ben PR Not done Anthropic live smoke |
| Gemini / Vertex AI | The official field is `UsageMetadata.cachedContentTokenCount`；Runtime consumption LiteLLM exposed snake_case / normalized Field，Such as `cached_content_token_count`、`cache_read_input_tokens` or `prompt_tokens_details.cached_tokens` | Gemini `UsageMetadata` See the official field <https://ai.google.dev/api/generate-content#UsageMetadata>；No new additions will be made to this warehouse native camelCase runtime fallback，Runtime boundaries start with `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` Subject to | unit/mock Cover；Ben PR Not done Gemini / Vertex live smoke |
| DeepSeek | `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens` | DeepSeek Chat Completion Documentation description `prompt_tokens = prompt_cache_hit_tokens + prompt_cache_miss_tokens`：<https://api-docs.deepseek.com/api/create-chat-completion> | unit/mock Cover；Ben PR Only do one desensitization DeepSeek smoke，Don't save full response |
| GLM / OpenAI-compatible / StepFun and other compatible platforms | Modeled token/cache count allowlist A value that can be mapped to a unified field | No official statement of stability cache telemetry contract；Only represents the current LiteLLM / OpenAI-compatible shape Do it next best-effort normalization，Not modeled metadata Not persistent | unit/fixture/mock Cover；Ben PR Didn't do this provider of live smoke |
| LiteLLM public response shape | `usage` / `usage_metadata` | Press current dependency window `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` of response / `Usage` object shape consumption；inaction LiteLLM 2.x Compatibility Commitment | Analyzer / Agent / usage tests Cover |
| LiteLLM private fallback | `_hidden_params["usage"]` | private/internal best-effort fallback，No LiteLLM stable public contract；only in public usage zero-only/no-signal Wait for narrow scenes to make up for it streaming usage，Do not change provider Request parameters | unit/mock Cover；If missing, only affects telemetry integrity，It does not mean that the model request failed |

```env
LLM_USAGE_HMAC_SECRET=
LLM_USAGE_HMAC_KEY_VERSION=local-v1
```

- `LLM_USAGE_HMAC_SECRET` When left blank，The system will generate the `.llm_usage_hmac_secret`，Suitable for single deployment local comparison。
- Only need to compare across deployments HMAC time，Only explicitly configure the same high-entropy random key；Recommended `openssl rand -hex 32` generate。
- `.llm_usage_hmac_secret` is local secret artifact，Already in `.gitignore` Ignore by file name。
- Synchronous updates when keys are rotated `LLM_USAGE_HMAC_KEY_VERSION`，Avoid generating different keys HMAC mistakenly compared。
- Do not reuse logins session secret，Also don't commit real keys to version control or expose them to issue、Log、Screenshot in progress。

### Provider prompt cache Configuration（P1 / P1.5）

Prompt cache The configuration only controls whether this project is recorded cache usage / diagnostics，And whether the main analysis path actively sends verified provider-specific hint；it does not control OpenAI、Gemini、DeepSeek Wait provider of implicit / provider-managed cache。

```env
LLM_PROMPT_CACHE_TELEMETRY_ENABLED=true
LLM_PROMPT_CACHE_HINTS_ENABLED=false
LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL=off
```

- `LLM_PROMPT_CACHE_TELEMETRY_ENABLED=false` time，Not persistent provider raw usage JSON、normalized cache fields and cache decision diagnostics；Basics token usage Records remain compatible。
- `LLM_PROMPT_CACHE_HINTS_ENABLED=true` Only main analysis allowed / analyzer LiteLLM path direction registry has been verified or smoke-tested of provider / route send `prompt_cache_key`、`cache_control`、`user_id` Wait hint。Ask about stocks Agent The path is currently only recorded capability / usage diagnostics，Do not send proactively provider-specific hints。unknown OpenAI-compatible gateway Default telemetry only。
- `LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL=basic` only in debug Logging and test observables are available in provider、api surface、verification status、hint applied / disabled reason etc. non-sensitive enumeration。`debug` additionally available within the same range HMAC-derived route/cache diagnostics and matched caps id，but still prohibited raw prompt、request body、message content、stocks/User original text、webhook or API key；These diagnoses are not public Usage API Or normal settings page output。
- Provider Cache Capability Registry Yes `src/llm/provider_cache.py` in code-level Manual ability table。Entry band `doc_sources`、`last_verified_at` and `verification_status`；New provider or upgrade LiteLLM The entries and tests should be updated simultaneously。
- Prompt cache key、route key and DeepSeek session isolation Reuse `LLM_USAGE_HMAC_SECRET` / `.llm_usage_hmac_secret` do domain-separated HMAC，No new addition prompt-cache dedicated secret。

### Legacy message stability audit（P0.5a）

P0.5a The analysis path for ordinary stocks is legacy `[system, user]` message Add internal stability audit field，Continue writing locally `llm_usage`。It reuses the above message HMAC，Do not modify prompt content、message order、provider Request parameters、cache hint、Model output、fallback order，Nor will it be extended to the public Usage API or Web Page。

The new fields are only used for maintainer diagnosis：

- `language`、`market_group`、`analysis_mode`、`legacy_prompt_mode`、`provider`、`transport`、`message_count` Describe the low-sensitivity routing context of this common stock analysis call。
- `skill_config_hmac` is based on parsed skill prompt fragment、Default skill strategy and legacy prompt schema generated HMAC-SHA256，used to judge system message Whether to follow skill configuration change；will not be saved skill Original text。
- `known_dynamic_marker_positions` Yes JSON string，record only `marker_name`、`message_role`、`char_offset`；Stock ticker will not be saved、Stock name、Date、News text、Quote value、headers、response text or prompt fragment。
- `estimated_total_prompt_tokens`、`approx_common_prefix_chars`、`approx_common_prefix_tokens` Based on stability within the project canonical render Estimate：press message sequential splicing `role + "\n" + content`，and concatenate with fixed separator。This caliber does not claim to be equivalent to provider true wire bytes。
- `char_offset` Yes marker In correspondence message `content` location within；`approx_common_prefix_chars` Yes canonical render Starting point to first known dynamic marker Number of characters before。No marker time common-prefix The fields are `NULL`。
- token Estimated usage `ceil(chars / 3)`，Just do diagnostics，No replacement provider usage，Nor participate cache threshold Judgment；The Chinese scene may be on the low side。

P0.5a Not introduced PromptBlock IR、`block_id`、`stability_class`、`static_prefix_hash` or `dynamic_context_hash`。Agent、research with market review The path is not currently connected to the audit。

---

## Method three：YAML Advanced configuration（Suitable for veteran customization）

**target：** I don’t care about the learning threshold，I want supreme control，I want to use native rules to achieve enterprise-level high availability！

This layer will be mapped directly to the bottom layer LiteLLM routing capability，Support high concurrency、Automatic retry、press RPM/TPM Load balancing and other operations。

### Run locally / Docker Deployment mode configuration instructions

1. in `.env` Leave only one line pointing to the declaration：
   ```env
   LITELLM_CONFIG=./litellm_config.yaml
   ```
2. Create a `litellm_config.yaml`（You can refer to the provided `docs/examples/litellm_config.example.yaml`）。

Example `litellm_config.yaml`：
```yaml
model_list:
  - model_name: my-smart-model
    litellm_params:
      model: deepseek/deepseek-v4-flash
      api_base: https://api.deepseek.com
      api_key: "os.environ/MY_CUSTOM_SECRET_KEY"  # Read from environment variables Key，Safe and leak-proof

  # Ollama local model（No need api_key）
  - model_name: ollama/qwen3:8b
    litellm_params:
      model: ollama/qwen3:8b
      api_base: http://localhost:11434
```

### GitHub ActionsConfiguration instructions

1. `Settings` → `Secrets and variables` → `Actions`。Non-sensitive configuration（Such as model name、switch、Base URL）can be placed `Secret` or `Variables`；Everyday `*_API_KEY` / `*_API_KEYS` and `LLM_<NAME>_API_KEY` / `LLM_<NAME>_API_KEYS` This type of key field，Please put them together `Secret` tab page `New repository secret`

2. Configure according to the table，Only all required configurations are configured correctly，YAML Advanced configuration mode can only take effect，YAMLHow to write configuration files，You can refer to the provided `docs/examples/litellm_config.example.yaml`

| Secret Name | Description | Required |
|------------|------|:----:|
| `LITELLM_CONFIG` | Advanced model routing configuration file path，Usually configured `./litellm_config.yaml` | Required |
| `LITELLM_MODEL` | Default main model name or routing alias | Required |
| `LITELLM_CONFIG_YAML` | store YAML Configuration file content，Can not submit physical files in the warehouse | Optional |
| `LITELLM_API_KEY` | for storageAPI Key，Can be referenced in configuration files（Environment variable reference method）。due toGitHub ActionsImported environment variables must be specified，Therefore you cannot name environment variables freely like in local run mode | Optional，Must be configured torepository secretin |
| `ANTHROPIC_API_KEY` | If you want multipleAPI Key，This variable name can also be used | Optional，Must be configured torepository secretin |
| `OPENAI_API_KEY` | Same as above，can be used to storeAPI Key | Optional，Must be configured torepository secretin |

Channel mode does not require uploading YAML File。Warehouse comes with `00-daily-analysis.yml` The following common fields have been explicitly passed through：

- runtime selection：`GENERATION_BACKEND`、`GENERATION_FALLBACK_BACKEND`、`GENERATION_BACKEND_TIMEOUT_SECONDS`、`GENERATION_BACKEND_MAX_OUTPUT_BYTES`、`GENERATION_BACKEND_MAX_CONCURRENCY`、`LOCAL_CLI_BACKEND_MAX_CONCURRENCY`、`AGENT_GENERATION_BACKEND`、`LLM_CHANNELS`、`LITELLM_MODEL`、`LITELLM_FALLBACK_MODELS`、`AGENT_LITELLM_MODEL`、`VISION_MODEL`、`VISION_PROVIDER_PRIORITY`、`LLM_TEMPERATURE`、`LLM_USAGE_HMAC_SECRET`、`LLM_USAGE_HMAC_KEY_VERSION`、`LLM_PROMPT_CACHE_TELEMETRY_ENABLED`、`LLM_PROMPT_CACHE_HINTS_ENABLED`、`LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL`
- Much Key：`GEMINI_API_KEYS`、`ANTHROPIC_API_KEYS`、`OPENAI_API_KEYS`、`DEEPSEEK_API_KEYS`（current workflow only from repository secrets import，Will not read the same name Variables）
- Common channel names：`primary`、`secondary`、`aihubmix`、`deepseek`、`dashscope`、`zhipu`、`moonshot`、`minimax`、`volcengine`、`siliconflow`、`openrouter`、`gemini`、`anthropic`、`openai`、`ollama`

For example in GitHub Actions Medium configuration `LLM_CHANNELS=primary,deepseek` time，Need to synchronize configuration `LLM_PRIMARY_*` / `LLM_DEEPSEEK_*`。Among them `LLM_<NAME>_API_KEY` / `LLM_<NAME>_API_KEYS` Currently only from repository secrets import；If you put these values in Variables，It will not take effect when running。If you use a custom channel name（Such as `my_proxy`），GitHub Actions Must still be there workflow `env:` Explicitly add the corresponding `LLM_MY_PROXY_*` mapping；local `.env` and Docker Not subject to this restriction。


> **Three-tier configuration mutual exclusion guidelines**：YAML highest priority！Just configure YAML，**channel model** and **Minimalist mode for beginners** All ignored。The system priority is：`YAMLConfiguration > channel model > Extremely simple model`。

---

## Extended functions：View diagram model (Vision) Configuration

There are some specific functions in the system（For example, upload stock software screenshots，let AI Extract the stock code in the screenshot and put it into the self-selected stock pool）must be used“visual ability”model。you need to be there `.env` Assign it a separate model that understands images。

```env
# Specify a model name specifically for viewing pictures
VISION_MODEL=openai/gpt-5.5
# Don’t forget to fill in the corresponding provider API KEY，if yes OpenAI Compatible channels are provided OPENAI_API_KEY：
# OPENAI_API_KEY=xxx
```

**Alternate picture viewing mechanism：** To prevent occasional strikes，The system has built-in switching strategy。If the main visual model call fails，It will try to find if there are other image viewing models in the order below Key：
```env
# Default fallback order：
VISION_PROVIDER_PRIORITY=gemini,anthropic,openai
```

---

## Detection and Troubleshooting (Troubleshooting)

After matching it, I was very frightened and didn’t know if it was right or not.？at the command line（Terminal）Enter the following code to help you register for consultation：

- `python scripts/check_env.py --config` ：pure detection `.env` Is the logic in the configuration file written correctly?，Did you write less?。（Results in seconds，No network calls，Purely check local text spelling）
- `python scripts/check_env.py --llm` ：The system will actually send a greeting to the big model，Let you see his answer with your own eyes。This can completely test your**The network is not working、Is the account in arrears?**。

### Common pitfalls and Q&A desk

| I encountered some weird error message？ | What could be the culprit?？ | How to clean it up？ |
|----------------------|----------------------|------------------|
| **The interface prompts that the main model is not configured.** | The system doesn’t know which model from which company you want to use. | in `.env` Write a clear sentence in：`LITELLM_MODEL=provider/your model name`。For example `openai/gpt-5.5` |
| **I have written for severalKey，Why does only one of life and death take effect?？The modification has not worked yet？** | you put **minimalist mode** and **channel model** I wrote it in a mixed manner！ | Think of a way to get to the dark side——Just delete it simply `LLM_CHANNELS` beginning；If you want to enrich backup switching, you must switch all to `LLM_CHANNELS` In the preparation below。 |
| **error code report 400 or 401 or Invalid API Key** | API Key Wrong entry、Less copy、The account recharge did not arrive.、Or the model name is wrongly typed（extremely common）。 | 1. Check the copied Key Are there any blanks filled in by mistake before and after?。<br> 2. Check Base URL Is there one missing in the end? `/v1`。<br> 3. Check whether the model name is omitted `openai/` prefixes like！ |
| **Kimi K2.6 newspaper `invalid temperature`（It may prompt that only allowed `1.0` or `0.6`）** | This model presses thinking / non-thinking Mode requirements are different and fixed temperature；The old configuration or call entry may still be transmitted. `0.7`。 | After the upgrade, the system will `kimi-k2.6` Default / thinking Request automatic use `temperature=1.0`；if you are LiteLLM YAML Explicitly turn it off in the route thinking，will automatically switch to `0.6`。It is recommended that the model name be written as `openai/kimi-k2.6` and cooperate Moonshot / aggregation platform OpenAI Compatible Base URL with API Key。Not Kimi fallback will continue to use your configured `LLM_TEMPERATURE`。 |
| **GPT-5 / o series of newspapers `temperature` Not supported or only default values allowed** | This type of model only accepts server-side default sampling parameters，But the old call entry will explicitly pass `0.7`。 | After the upgrade, the request layer will be omitted. `temperature`，Let the server use the default value；`.env` / Web in settings `LLM_TEMPERATURE` will not be rewritten，After switching back to the normal model, the original value will still be sent.。 |
| **spinning around in circles，Last report Timeout / ConnectionRefused Wait** | 1. Use foreign originals in China（like Google、OpenAI），I didn’t open an agent and was blocked.。<br>2. The cloud server you bought cannot be exported abroad at all.。 | Highly recommended to use**Domestic official**（Such asDeepSeek、Ali）or various**Compatible OpenAI aggregation transit interface**。Because the transfer station has solved the network problem for you.。 |
| **Ollama newspaper 404、`Could not get model info` or `api/generate/api/show`** | misuse `OPENAI_BASE_URL` Configuration Ollama，The system will splice incorrectly URL | Use instead `OLLAMA_API_BASE=http://localhost:11434` or channel model（`LLM_CHANNELS=ollama` + `LLM_OLLAMA_BASE_URL`） |

*Advice from an advanced veteran：If you enable **Agent (Deep Thoughts on Internet Search Stocks) mode**，Here is a lesson from experience，It is recommended to choose such as `deepseek-v4-pro` This large model with stronger logical derivation capabilities。If you use a small model to save money, Agent，Its logical ability will most likely not be able to keep up.，Not only did it fall short of expectations，It will also run a bunch of empty processes in vain.。*
