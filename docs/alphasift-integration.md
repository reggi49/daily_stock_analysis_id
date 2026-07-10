# AlphaSift Stock Screening Integration

Data source failure, fallback chains, and recommended configuration diagrams for connected sources like Tushare / TickFlow / AkShare can be found in [Data Source Stability and Failure Handling Diagrams](data-source-stability.md).

AlphaSift is a stock screening engine maintained in a separate repository, integrated into DSA. DSA does not enable it by default and does not copy AlphaSift's strategy logic into the main repository; the backend dependency is installed via `requirements.txt`, and after enabling, it only calls AlphaSift through the stable `alphasift.dsa_adapter` adaptation layer.

## Current Approach

- Disabled by default: `ALPHASIFT_ENABLED=false`.
- Enable entry point: Toggle on from the settings page or screening page, or set `ALPHASIFT_ENABLED=true` in `.env`.
- Dependency source: `requirements.txt` pins to a verified AlphaSift adapter layer commit: `git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf#egg=alphasift` (corresponding to commit `https://github.com/ZhuLinsen/alphasift/commit/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, covering PRs `https://github.com/ZhuLinsen/alphasift/pull/16` through `https://github.com/ZhuLinsen/alphasift/pull/37`). This source covers `alphasift.dsa_adapter` contract, `screen/list_strategies/get_status` calls, Tencent daily K, Sina snapshot, source health, stale daily fallback, candidate-level quote context, wrapper data source caller-side timeout, East Money direct connection rate limiting and jitter, daily line data source health/degradation diagnostics, hard filter waterfall diagnostics, strategy evaluation summaries, theme matching scores, strategy catalog metadata, `blue_chip_income` / `low_volatility_quality` strategies, and LLM ranking `LLM_MAX_TOKENS` output cap, no JSON-mode retry after timeout, and more robust JSON parsing boundaries.
- Fix installation source: `ALPHASIFT_INSTALL_SPEC` is retained and defaults to the same trusted commit. It is no longer the runtime installation primary path for the strategy list or screening interface; it is only used for fix-installation and source validation when explicitly calling `/api/v1/alphasift/install`; when not explicitly configured, it falls back to the code constant `DEFAULT_ALPHASIFT_INSTALL_SPEC`.
- Migration boundary (explicit `.env` priority):
  - If `.env` explicitly retains an old pin (e.g., `...de54ea0da367be85770d9589a5bf7ded4f62d386`), DSA treats this value as a user override and will not automatically replace it with the new pin at runtime;
  - After upgrading, if you want to enable the new commit, manually clean up that line/rewrite it and rebuild dependencies;
  - `ALPHASIFT_INSTALL_SPEC` is tightly bound to the `/api/v1/alphasift/install` allow-list; changing `.env` alone without simultaneously reverting `requirements.txt` and `src/config.py` constants will be rejected by `alphasift_install_spec_not_allowed`.
- Rollback methods:
  - Path A (business quick rollback, ~5 minutes): Set `ALPHASIFT_ENABLED=false` and restart to restore the original analysis pipeline;
  - Path B (adapter layer version rollback): Simultaneously revert `requirements.txt`, `src/config.py` (`DEFAULT_ALPHASIFT_INSTALL_SPEC`), and `.env.example` example values, then rebuild backend image/desktop artifacts after reinstalling dependencies.
- Missing dependency boundary: If `alphasift.dsa_adapter` is missing from the runtime environment, `status` returns `available=false + diagnostics.reason=missing_module`; `strategies` and `screen` return `424` with a prompt to run `pip install -r requirements.txt` or rebuild Docker/desktop backend artifacts, without auto `pip install` in business requests.
- Runtime exception boundary: If the adapter layer can be imported but `get_status()` throws an error or returns `available=false`, DSA returns `424 + diagnostics`, preserving fault diagnostics and preventing reinstallation from masking real runtime errors.
- Strategy ownership: Strategy list, strategy parameters, full market snapshot, initial screening, factor scoring, and LLM reranking are AlphaSift's responsibility; DSA handles the toggle, API shell, data provider, display, and error messaging.

## External Contract Source and Migration Boundary

- External contract basis: This AlphaSift runtime contract (including hot-cache and theme detail fields with `schema_version=2`) corresponds to GitHub commit `https://github.com/ZhuLinsen/alphasift/commit/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`.
  This commit takes effect in DSA through: `requirements.txt` install pin, `src/config.py` default `DEFAULT_ALPHASIFT_INSTALL_SPEC`, `.env.example` default example value.
- Upgrade path:
  - Deployment side only needs `git pull` + `pip install -r requirements.txt` + restart service per deployment method;
  - Before integrating new behavior, confirm `ALPHASIFT_INSTALL_SPEC` has not been explicitly overridden to an old value;
  - When `ALPHASIFT_INSTALL_SPEC` has been manually configured, DSA only validates the source when calling `install`, without runtime silent migration, and will not replace the original value.
- Rollback boundary (two paths):
  - Path A (temporary business rollback, executable within 5 minutes): Set `ALPHASIFT_ENABLED=false` and restart the service/process. Core analysis, daily reports, and original LLM call chains are not affected by this toggle; this path does not affect dependency versions.
  - Path B (adapter layer version rollback): Restore `requirements.txt` and `src/config.py` (`DEFAULT_ALPHASIFT_INSTALL_SPEC`) to old values, simultaneously revert `.env.example` defaults, rebuild backend image/desktop backend artifacts (equivalent to fully reverting this PR) and restart. Changing `.env` alone to revert `ALPHASIFT_INSTALL_SPEC` will be rejected by the current allow-list; it must be reverted together with `requirements.txt` and code allow-list.
  - Installation entry note: `/api/v1/alphasift/install` only allows sources in the current code's `ALLOWED_ALPHASIFT_INSTALL_SPECS` (currently a single-value set). If temporarily connecting another source is needed, manually install and confirm the adapter layer can be imported in the environment first, then restart the service.
- Compatibility note: `ALPHASIFT_INSTALL_SPEC` only affects source validation during `install` calls; `requirements.txt` and `src/config.py` constants are the actual runtime source constraints. `status` returning `install_spec_is_default` allows quick determination of whether the current configuration matches the DSA code default source.

- DSA Enhancement: Through the DSA provider context, AlphaSift only supplements lightweight real-time market data and fundamental context for top candidates before LLM reranking, without fetching news during the initial screening phase; during the DSA API return phase, news and auxiliary summaries are added for final top candidates, with reuse or completion recorded via `dsa_enrichment`.
- Daily K-line feature supplementation: When DSA calls AlphaSift, it prioritizes reusing the DSA historical market data loading pipeline (database cache, Tushare, Efinance, Akshare, Pytdx, Baostock, Yfinance and other fallbacks), only falling back to AlphaSift's original daily line data source when the DSA pipeline has no available data, reducing single upstream timeouts from dragging down the entire stock screening.
- LLM environment: When DSA calls AlphaSift, it bridges DSA's parsed `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `LLM_CHANNELS`, `LLM_<NAME>_*`, `LITELLM_CONFIG`, channel extra headers, and model keys; AlphaSift uses its own `.env`/environment variables when running independently. `LLM_TIMEOUT_SEC` and `LLM_MAX_TOKENS` can be read by AlphaSift's stock screening LLM reranking, limiting single request duration and output token cap respectively.
- Snapshot source: When DSA calls AlphaSift, if `SNAPSHOT_SOURCE_PRIORITY` is not explicitly configured, it is injected in token-aware order: with `TUSHARE_TOKEN` it is `tushare,sina,efinance,akshare_em,em_datacenter`, without a token it is `sina,efinance,akshare_em,em_datacenter`; simultaneously `DAILY_SOURCE=auto`, `DAILY_FETCH_RETRIES=3`, `DAILY_FETCH_MAX_WORKERS=1`, and default candidate context `news,fund_flow,announcement,quote` are injected. Explicitly configured source order, daily line source, and candidate context providers are preserved as-is.
- External data source timeout guardrails: AlphaSift adds caller-side timeout for third-party wrapper sources like efinance, AkShare, Baostock, Tushare, yfinance; `ALPHASIFT_SNAPSHOT_CALL_TIMEOUT_SEC` defaults to 60 seconds, `ALPHASIFT_DAILY_CALL_TIMEOUT_SEC` defaults to 20 seconds, `ALPHASIFT_SOURCE_CALL_TIMEOUT_SEC` serves as a global fallback and can be disabled by setting `0`/`off`/`disabled`. After timeout, source health and `last_error` are logged, and subsequent data sources or last-good/daily history fallbacks continue to be attempted, reducing a single wrapper hanging from dragging down the entire stock screening.
- Latest AlphaSift capabilities: Pinned commit `9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf` includes stock screening pipeline performance optimization, Tencent daily K, Sina snapshot, source health, stale daily fallback, candidate quote context, wrapper data source caller-side timeout, East Money direct shared retry session/rate limiting/random jitter, LLM ranking timeout/max tokens boundary, last-good snapshot fallback, daily history cache, industry/concept provider cache, hotspot/industry heat factors, hotspot topic rankings, local scorecard/post-analysis metadata, daily line data source health ranking and alerts, hard filter waterfall diagnostics, strategy evaluation summaries, multi-window price path evaluation, theme matching scores, strategy catalog metadata, `blue_chip_income` and `low_volatility_quality` strategies. When DSA calls, it injects isolated cache default paths `data/alphasift`, `data/alphasift/snapshot.last_good.json`, `data/alphasift/daily_history`, `data/alphasift/industry_provider_cache`; the Web screening page provides a "Hot Topics" manual refresh entry point, explicitly using the `akshare` provider to prioritize fetching specific concept/theme anomalies (e.g., molybdenum, lead-zinc, copper, diagnostic services real-time sector anomalies) when requesting `/api/v1/alphasift/hotspots`, with industry sectors only as fallback; by default when opening the page, it prioritizes reading the last successful hot topics cache with at least 3 entries, only fetching in real-time and overwriting cache when clicking refresh, with fallback to old cache when real-time fetch fails; if the AlphaSift contract layer returns only a few hotspots or those missing key fields like price change percentage, DSA substitutes with the East Money sector anomaly direct ranking. Clicking a topic requests `/api/v1/alphasift/hotspots/{topic}` to display fermentation routes and concept stocks; topic details have a separate DSA-side 30-minute disk cache at `data/alphasift/hotspot_details` or custom `ALPHASIFT_DATA_DIR/hotspot_details`, with repeated clicks on the same topic prioritizing cache return, real-time detail failures falling back to expired cache; manually refreshing the hot topics list while keeping the current topic passes `refresh=true` to detail requests to bypass the detail cache; will not by default trigger AlphaSift's DSA deep-analysis callback, avoiding expanding the recursive call surface without notice.
- Hot topics refresh error tolerance: When `/api/v1/alphasift/hotspots` is called without an explicit provider and `INDUSTRY_PROVIDER` is not configured, it defaults to the DSA East Money fallback provider (response provider is `akshare`), avoiding falling into AlphaSift's empty provider path; East Money hotspot direct sources encountering connection interruption, timeout, or `Connection aborted` perform short backoff retries; when manual refresh fails and no hotspot cache is available, it returns a stable empty state payload, `source_errors=["eastmoney_hotspot_unavailable"]`, and user-readable `message`, with the original exception only retained in server logs or diagnostic pipelines. Desktop updates preserve `data/alphasift/hotspots.json`, `data/alphasift/hotspot.history.jsonl`, `data/alphasift/hotspot_details`, and `data/alphasift/snapshot.last_good.json`, avoiding last-good cache loss after updates.
- Hot topics data source supplement: DSA provider uses direct HTTP approach, East Money sector fallback source uses `push2.eastmoney.com/api/qt/clist/get` and retains fields like price change percentage, leading stocks, rising/falling counts; topic details are cached and merged within a single provider lifecycle, combining East Money constituent stocks, Tonghuashun page parsing, and sector anomaly leading stock fallback, prioritizing multiple concept stock returns, with fermentation routes aggregated by date to avoid splitting the same intraday observation into multiple entries at the same time point; event catalysts no longer use DSA built-in static text, only displaying real information from the AlphaSift contract timeline, Tonghuashun summaries, configured news search sources, or East Money sector anomaly structure; news search hits are prioritized for compression into a one-sentence theme catalyst summary via the configured LLM, falling back to local short summaries when the LLM is unavailable, avoiding displaying full reports in the timeline.
- Risk disclaimer: The frontend settings page and screening page display third-party source and investment risk notices; will not interrupt users with pop-ups.

## AlphaSift Adapter Layer Requirements

AlphaSift needs to provide the `alphasift.dsa_adapter` module and maintain the following stable functions:

- `/api/v1/alphasift/hotspots` supports `include_details=true`: list responses will try to include the `details` mapping for top topics, enabled by default on the Web side, for batch reuse of fermentation routes and concept stock caches, reducing secondary waits when switching between different topics.

```python
def get_status() -> dict: ...
def list_strategies() -> list[dict]: ...
def screen(
    strategy: str,
    *,
    market: str = "cn",
    max_results: int = 20,
    use_llm: bool = True,
    context: dict | None = None,
) -> dict: ...
```

`get_status()` should return:

```json
{
  "available": true,
  "contract_version": "1",
  "version": "0.2.0",
  "strategy_count": 8,
  "supported_markets": ["cn"]
}
```

`list_strategies()` should at minimum return `id`; it is recommended to also return `name`, `description`, `category`, `tags`, `market_scope`.

`screen()` return value should include:

```json
{
  "run_id": "20260531-...",
  "strategy": "dual_low",
  "market": "cn",
  "snapshot_count": 100,
  "after_filter_count": 5,
  "llm_ranked": true,
  "llm_coverage": 1.0,
  "warnings": [],
  "source_errors": [],
  "candidates": []
}
```

Candidates should include `code`, `name`, `score`, `reason`, `risk_level`, `risk_flags`, `price`, `change_pct`, `amount`, `industry`, `factor_scores`, and LLM fields: `llm_score`, `llm_confidence`, `llm_thesis`, `llm_catalysts`, `llm_risks`, `llm_watch_items`, etc.

DSA will pass the following in adapters that support `context`:

```python
context = {
    "llm": {
        "model": "...",
        "fallback_models": [...],
        "channels": [...],
        "model_list": [...],
    },
    "dsa": {
        "contract_version": "1",
        "mode": "pre_rank_light",
        "max_candidates": 3,
        "include_news": False,
        "news_max_results": 0,
        "capabilities": ["candidate_context", "daily_history", "realtime_quote", "fundamental_context"],
        "get_candidate_context": callable,
        "get_daily_history": callable,
        "get_realtime_quote": callable,
        "get_fundamental_context": callable,
    },
}
```

AlphaSift will call the providers in `context["dsa"]` after L1 initial screening and before LLM reranking, supplementing DSA market data and fundamental lightweight context for limited top candidates, and returning `dsa_context` with the candidates. News search, full summaries, and missing field completion are performed by the DSA API during the final top candidate phase; if candidates already carry complete news context, the DSA API return phase reuses these fields to avoid duplicate requests.

AlphaSift side has provided DSA provider context support and DSA adapter contract at `ZhuLinsen/alphasift@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, and supports reusing DSA's `LLM_TIMEOUT_SEC`; the same pin also reads `LLM_MAX_TOKENS` to limit LLM reranking output, and does not blindly retry JSON mode-less requests after timeout. The `dsa_adapter` stable contract still only returns DSA-consumed strategy base fields and stock screening result fields; upstream strategy facets, overview, local read-only APIs, and strategy card capabilities do not enter the DSA API contract for now.

## DSA Backend Behavior

- `/api/v1/alphasift/status`: Returns toggle, availability, default install source identifier, adapter layer metadata, and AlphaSift in-process snapshot/daily source health; does not expose full install source.
- `/api/v1/alphasift/install`: Explicit fix-installation entry point. Desktop mode (`DSA_DESKTOP_MODE=true`) does not require an admin session; non-desktop deployments must have `ADMIN_AUTH_ENABLED=true` with a valid admin session, otherwise returns `401/403`. The endpoint only allows the default trusted install source and will force reinstall the pinned commit, avoiding old `alphasift` package residue.
- `/api/v1/alphasift/strategies`: Reads the AlphaSift strategy list; if `ALPHASIFT_ENABLED=true` but the adapter layer is missing or in an abnormal state, returns `424 + diagnostics` without triggering runtime installation.
- `/api/v1/alphasift/screen`: Calls the adapter layer `screen(..., use_llm=True)` and temporarily injects DSA's parsed LLM runtime environment during the call, while passing structured LLM/DSA provider configuration to the adapter layer; AlphaSift consumes only lightweight DSA provider context before LLM and prioritizes supplementing AlphaSift factor features through the DSA daily line pipeline, with the DSA return phase adding news for final top candidates and reusing enhanced fields. Missing adapter layer or runtime exceptions return `424 + diagnostics` with original error boundaries preserved.
- `/api/v1/alphasift/screen/tasks`: Background task entry point used by the Web/desktop screening page; returns `task_id` immediately after submission, with actual screening continuing in a shared task queue, preventing browser long requests from timing out due to external snapshots, market data, news, or LLM delays.
- `/api/v1/alphasift/screen/tasks/{task_id}`: Queries background screening task status. In progress returns `pending/processing + progress/message`, on completion returns the same candidate structure as `/screen` in `result`, on failure returns `failed + error`; only accepts task IDs with `report_type=alphasift_screen`, with normal analysis tasks not being misread as screening results.

## Configuration Compatibility Boundary (LLM / LiteLLM / Base URL)

- Compatible semantics and version evidence (traceable):
  - Runtime dependency constraint: `requirements.txt` pins LiteLLM to `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` and installs the AlphaSift adapter layer via `git+https://github.com/ZhuLinsen/alphasift.git@9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`.
  - Documentation basis:
    - LiteLLM Providers: https://docs.litellm.ai/docs/providers
    - LiteLLM OpenAI-compatible: https://docs.litellm.ai/docs/providers/openai_compatible
    - LiteLLM model_list/proxy configuration (including `api_base`, `api_key`, `extra_headers`): https://docs.litellm.ai/docs/proxy/configs
    - OpenAI request semantics and authorization headers: https://platform.openai.com/docs/api-reference/making-requests, https://platform.openai.com/docs/api-reference/authentication

- Structured detection clarification: This PR touches `.env.example`, `requirements.txt`, `src/config.py`, and this document because the AlphaSift dependency pin update and call-period runtime bridge need to pass through existing DSA LLM configuration to the external adapter layer; this PR does not upgrade LiteLLM major version, does not add or rename provider protocols, and does not modify `LITELLM_MODEL`/`LITELLM_FALLBACK_MODELS`/`LLM_CHANNELS`/`LLM_<NAME>_*` persisted parsing semantics.
- LLM runtime compatibility boundary: AlphaSift does not change the main configuration pipeline and only injects parsed `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `LLM_CHANNELS`, and `LLM_<NAME>_*` into the process environment during the call period; managed provider fallback filtering behavior maintains existing strategy without silent migration of historical configuration. `ALPHASIFT_ENABLED` is the only new persistent branch in the current scenario.
- Note: This injection is **short-lived memory injection**; it does not rewrite `.env`, does not write back historical configuration, and does not silently migrate user-defined provider/model routing; on failure or when disabled, besides AlphaSift stock screening capability itself, other DSA business pipelines maintain existing configuration execution.
- Injection source and rollback principles:
  - `LITELLM_MODEL` and `LITELLM_FALLBACK_MODELS` prioritize DSA-declared routing: `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `llm_model_list`; undeclared custom provider/model retains user original configuration and is not rewritten.
  - `OPENAI_BASE_URL` prioritizes reusing the main configuration's `OPENAI_BASE_URL`; only when not configured does it fall back to the declared openai `LLM_CHANNEL` base_url; will not override private gateway or alias configuration in the main configuration.
  - `LLM_<NAME>_API_KEYS/BASE_URL/MODELS` are only merged and injected according to declared channels; undeclared channels do not get new injection fields.
- If existing custom model names, channel, Base URL, or extra headers are present, enabling/retrying AlphaSift will not automatically overwrite `.env`. To roll back, restore per original configuration:
  - Roll back to old model name: Directly modify `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, or clear custom `LLM_CHANNELS`.
  - Restore old channels: Retain historical `LLM_<NAME>_API_KEYS/BASE_URL` and restart to take effect, without executing additional migration scripts.
- Compatibility verification basis (operations verification):
  - Dependency version basis: Current server constraint is `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` (see `requirements.txt`); AlphaSift only reuses this dependency's provider/model parsing, `model_list`, and call parameter semantics.
  - Official provider/model basis: LiteLLM Providers documentation (https://docs.litellm.ai/docs/providers) defines provider prefixes; OpenAI-compatible documentation (https://docs.litellm.ai/docs/providers/openai_compatible) explains `openai/<model>`, `api_base`, `api_key` compatible semantics.
  - Official `model_list`/extra headers basis: LiteLLM config documentation (https://docs.litellm.ai/docs/proxy/configs) explains `litellm_params` supports `model`, `api_base`, `api_key`, and `extra_headers`. DSA only converts declared channels to the same structure for AlphaSift without adding new model routing mappings or provider mode migration.
  - Compatible header semantics basis: OpenAI call conventions (https://platform.openai.com/docs/api-reference/making-requests) and authentication conventions (https://platform.openai.com/docs/api-reference/authentication) correspond to `Authorization` and custom header passing behavior; `extra_headers` is only for supplementing session headers without modifying model routing.
  - Rollback path is "disable AlphaSift from the settings page or keep `ALPHASIFT_ENABLED=false`" while maintaining existing `LITELLM_*` and `LLM_*` configuration; when triggering fails, check `status`/`screen` `diagnostics` first, then restart the service.
- Old configuration preservation evidence:
  - `src/services/alphasift_service.py`'s `_alphasift_runtime_env()` saves same-name `os.environ` values before calling and restores or deletes temporarily added keys item by item after calling; this path does not call `dotenv_values()` to write back and does not modify `.env` file.
  - `src/services/alphasift_service.py`'s `_build_alphasift_runtime_env()` only generates a temporary env dict from the current `Config`; undeclared channels do not generate `LLM_<NAME>_*`, and existing custom provider/model/base URL will not be renamed or cleaned.
  - `tests/test_alphasift_api.py` covers `test_screen_bridges_dsa_llm_config_into_alphasift_runtime`, `test_screen_bridges_legacy_openai_fields_into_alphasift_runtime_env`, `test_screen_injects_openai_compatible_model_headers_into_alphasift_litellm_calls`, `test_screen_disabled_preserves_existing_llm_env_state`, and `test_screen_filters_undeclared_managed_fallbacks_for_dsa_routes`, proving injection, OpenAI-compatible header/base URL, disabled state, and undeclared fallback all do not rewrite user original configuration.
- Failure visibility: `status`/`screen` endpoints return clear error codes and `message`; the frontend displays `403/424/400/422` errors directly to the user on the settings or screening page, facilitating identification and rollback to "disable AlphaSift + maintain original LLM runtime pipeline."

## Compatibility Acceptance Index (Pre-release Verification)

- Dependency and source code constraint verification: `litellm` constraint in `requirements.txt` matches `src/config.py`/`requirements.txt`.
- Hotspot contract compatibility verification: `docs/alphasift-integration.md`, `api/v1/endpoints/alphasift.py`, and `src/services/alphasift_service.py` maintain `hotspots`/`hotspots/{topic}` field consistency with `tests/test_alphasift_api.py`, with `snapshot.last_good` cache fallback before and after calls.
- External version source: This integration dependency source is `https://github.com/ZhuLinsen/alphasift/commit/9f522747caafd3c0b1ddb7e14d5cf44c8580b6cf`, requiring import and interface contract replay by this commit pin during verification.
- Behavior verification: `src/services/alphasift_service.py`'s `_build_alphasift_runtime_env` and `_build_alphasift_context` only write to the process environment during the call period; `/api/v1/alphasift/screen`, `strategies`, `status` do not write back `.env` at runtime.
- Rollback verification: After disabling `ALPHASIFT_ENABLED` and restarting the configuration pipeline, the system restores original `LITELLM_MODEL/FALLBACK_MODELS`, `LLM_CHANNELS`, and `LLM_*` runtime semantics without executing migration cleanup scripts.
- Semantic source verification: LiteLLM documentation (https://docs.litellm.ai/docs/providers), OpenAI-compatible documentation (https://docs.litellm.ai/docs/providers/openai_compatible), and LiteLLM configuration documentation (https://docs.litellm.ai/docs/proxy/configs) are used to verify provider/model/base_url/extra_headers mapping chains.
- Status diagnostics: `/api/v1/alphasift/status` maintains `200` + `available=false` compatible semantics for AlphaSift package or `alphasift.dsa_adapter` not installed; if import process, `get_status()` call, or return structure has unexpected exceptions, the backend logs warnings and appends a `diagnostics` field without install source plaintext to the response, facilitating issue location from endpoint status and server logs.

Error strategy:

- Disabled returns `403 alphasift_disabled`.
- Fix-installation endpoint with untrusted source returns `403 alphasift_install_spec_not_allowed`.
- AlphaSift not installed, missing adapter layer, or adapter layer not callable returns `424`.
- Market or strategy rejected by adapter layer returns `400/422`.
- Runtime failure returns `424 alphasift_screen_failed`.

## Web Behavior

- The settings page provides an AlphaSift toggle; when enabled, writes `ALPHASIFT_ENABLED=true` and checks adapter layer availability; if missing, rolls back the toggle and prompts to run `pip install -r requirements.txt` or rebuild Docker/desktop backend artifacts.
- `ALPHASIFT_ENABLED` is the persistent state behind the "Enable Screening" button and is not displayed repeatedly as a regular data source configuration item.
- The screening page shows the enable button when not enabled; when enabled, reads the AlphaSift strategy list.
- Currently only exposes A-share `cn` market.
- Default return count is 3 to avoid slow screening or excessive results.
- The screening page obtains results through background task submission and status polling; the task ID is saved in the current browser tab's `sessionStorage`, allowing progress or final results to continue when returning to the screening page after switching pages. When the backend restarts or the task is cleaned up, the frontend prompts that the task is unrecoverable and allows re-running.
- The result page displays run ID, sample count, post-filter count, whether LLM reranking was used, LLM coverage rate, and DSA enhancement count; if AlphaSift returns warnings/source errors/LLM parse errors or `llm_ranked=false`, the page clearly displays the degradation reason, avoiding misdisplaying local factor results as normal LLM judgments; duplicate snapshot source fallback warnings/source errors are merged on the frontend into a single "Data Source Degradation" notice.
- When expanding candidates, AlphaSift summaries, factors, and LLM judgments are displayed; if DSA has enhanced, `DSA Enhanced Summary`, `DSA News`, and `DSA Enhancement Notes` are also displayed.

## Desktop Notes

Source-run desktop reuses the same Python backend environment and sets `DSA_DESKTOP_MODE=true`; when enabling from the settings page, if the adapter layer is missing, it prompts to update dependencies or rebuild backend artifacts.

Packaged desktop does not depend on runtime `pip install`: Windows/CI uses `scripts/build-backend.ps1`, macOS uses `scripts/build-backend-macos.sh`, both executing `pip install -r requirements.txt` first, then verifying and collecting `alphasift.dsa_adapter` into PyInstaller artifacts. Release packages default to disabled; users enable from the Web settings page, which first checks the adapter layer, and if the packaged artifact is abnormally missing, should rebuild or update the desktop backend.

## Docker Notes

Docker images are consistent with desktop release packages: `docker/Dockerfile` installs AlphaSift via `requirements.txt` and verifies `alphasift.dsa_adapter` can be imported. The container runtime defaults to AlphaSift disabled; users enable it via `ALPHASIFT_ENABLED=true` or the Web settings page using the image's built-in dependencies, and if the adapter layer is missing from the runtime environment, should rebuild the image.

## Verification Records

- `python -m pytest tests/test_alphasift_api.py -q`
- `python -m pytest tests/test_main_schedule_mode.py -q -k "start_api_server_fails_before_thread_when_port_is_busy"`
- `python -m py_compile api/v1/endpoints/alphasift.py src/services/alphasift_service.py tests/test_alphasift_api.py src/config.py src/core/config_registry.py`
- `cd apps/dsa-web && npm run test -- alphasift.test.ts StockScreeningPage.test.tsx SettingsPage.test.tsx --run`
- `cd apps/dsa-web && npm run lint`
- `cd apps/dsa-web && npm run build`

## Rollback

- Disable feature: Disable AlphaSift from the settings page, or configure `ALPHASIFT_ENABLED=false`.
- Version rollback: To downgrade the alphasift adapter layer, you must simultaneously revert the trusted pin in the repository's `requirements.txt` and `src/config.py`; otherwise changing only `.env`'s `ALPHASIFT_INSTALL_SPEC` will be rejected by `alphasift_install_spec_not_allowed`; after confirmation, rebuild dependencies and restart the service.
- Special source: To use an AlphaSift installation package outside the default source, first manually install in the backend Python environment and confirm `alphasift.dsa_adapter` can be imported, then restart the service (do not trigger the `/api/v1/alphasift/install` allow-list validation path before installation).
- Code rollback: Remove the AlphaSift API registration, Web screening entry, and related configuration items to restore to the pre-integration flow; in the default disabled state, original stock analysis, report generation, and notification flows are not affected.
