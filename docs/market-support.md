# Market Support & Boundaries

## Japan/Korea Individual Stock Suffix-Only MVP (Issue #1718, Refs #1718)

The current phase supports manually entering Yahoo Finance suffix codes for Japanese and Korean stocks, entering the existing individual stock analysis, history persistence, and basic report display pipeline. Web autocomplete includes a built-in set of common Japanese/Korean stock seed indexes, supporting search by suffix code, Chinese/English name, or common alias.

Supported formats:

- Japan: `7203.T`, `6758.T`
- Korea KOSPI: `005930.KS`
- Korea KOSDAQ: `035720.KQ`

Constraints and boundaries:

- When entering bare codes, the local/remote stock pool is searched first; if `005930`, `000660`, etc. bare codes match `005930.KS`, `000660.KS`, etc. Japanese/Korean entries, analysis is submitted per the matched market; if the stock pool has no match, the existing 6-digit numeric code rules default to A-share semantics and are preserved as a traceable cross-market ambiguity boundary.
- Japanese/Korean stock suffix identification has been centralized to a shared market code utility; data source routing, Prompt market identification, trading calendar, and stock index bare code parsing reuse the same rule set, reducing rule drift during future market expansion.
- Japanese/Korean stock daily data and basic realtime/near-realtime quotes only use `YfinanceFetcher`, without attempting A-share-specific data sources such as AkShare, Tushare, Efinance, Pytdx, or Baostock; yfinance quotes include quality metadata such as `market`, `currency`, `data_quality`, and `missing_fields` where available.
- Fundamentals reuse the existing offshore yfinance lightweight path; A-share-specific capital flows, dragon-tiger lists, sectors, etc. degrade to `not_supported`, and offshore fundamentals context also marks provider, as_of, data_quality, and missing blocks.
- Report Prompts have added Japanese/Korean market semantics to avoid applying A-share limit up/down, northbound capital, dragon-tiger list, and margin trading concepts.
- Trading calendar registers `jp: XTKS / Asia/Tokyo` and `kr: XKRX / Asia/Seoul`. Japanese stock regular phases recognize pre-market, intraday, lunch break, 15:25-15:30 closing auction, post-market, and non-trading days; Korean stock regular phases recognize pre-market, intraday, 15:20-15:30 closing auction, post-market, and non-trading days. If the local `exchange-calendars` version lacks the corresponding calendar, existing fail-open/fail-closed semantics remain unchanged.

Compatibility and rollback notes (for structured detection hits):

- `#1815` this round only adds optional field metadata in `yfinance` quote/fundamentals context (such as `market`, `currency`, `data_quality`, `missing_fields`, `provider`) without modifying LLM provider/model/base URL, configuration schema, runtime environment variables, database fields, existing cache serialization, or message protocol versions.
- Configuration semantics related to this PR: no new or replaced providers, models, or base URLs; no new configuration cleanup/migration branches; saved configurations remain unchanged; rollback is to revert this commit.
- External API boundaries remain limited to existing `yfinance` fetch paths (including `Ticker`/`history`/`fast_info`) and existing fallback logic; no new or migrated API gateway/host; `YFINANCE_PRIORITY` is the only affected visible parameter. JP/KR major index and Yahoo symbol mappings (verifiable):
  - Nikkei 225: `^N225` (<https://finance.yahoo.com/quote/%5EN225/>)
  - TOPIX: `^TOPX` (<https://finance.yahoo.com/quote/%5ETOPX/>)
  - KOSPI: `^KS11` (<https://finance.yahoo.com/quote/%5EKS11/>)
  - KOSDAQ: `^KQ11` (<https://finance.yahoo.com/quote/%5EKQ11/>)
  - Dependency version: `yfinance>=0.2.0` in `requirements.txt`; regression coverage in `tests/test_yfinance_jp_kr_indices.py` and `tests/test_yfinance_hk_indices.py`.
- Compatibility and rollback: `MARKET_REVIEW_REGION` retains valid comma subsets (e.g., `cn,us`) and maintains `both` full behavior; invalid or empty values fall back to `cn` without clearing or migrating saved configurations.
- Runtime boundaries: JP/KR indices are fetched per item under market_review's fail-open convention; a single item failure does not block other indices or markets; when neither market has a usable main index quote, a locally visible `None/empty` is returned and the main flow continues with remaining markets or degrades directly.
- Compatibility verification basis: quote/fundamentals context in `data_provider/base.py` and `realtime_types.py` passes through downstream via existing `getattr`/optional field conventions without mandatory read/write of new fields; no configuration migration scripts; no observed provider/model/base URL fallback path changes.
- Rollback: If new metadata fields cause compatibility issues on some side, ignore these fields and run via existing market determination + quote display pipeline; if necessary, revert this commit or restore old behavior by removing `jp/kr` `MarketSymbol` and routing extensions.

Not committed:

- Not committed to realtime quotes; Yahoo Finance data may be delayed or have missing fields.
- Not committed to complete fundamentals, industry/sectors, market breadth, or advance/decline counts. JP/KR market review v1 only provides major indices, news leads, and template/LLM review without Japanese/Korean market breadth or sector rankings.
- Not committed to complete Japanese/Korean full-market stock lists; Web autocomplete currently only covers commonly used targets in the repository's seed indexes (expanded to approximately 30 leading stocks per market); unmatched cases can still be entered manually with suffix codes.
- Does not complete Portfolio's JPY/KRW exchange rates, cost basis, or market value full scope; related fields only release market type to avoid front/back-end validation rejection.

Rollback: Remove `jp/kr` market identification, trading calendar registration, YFinance routing extensions, Web/API type release, `scripts/stock_index_seeds/` Japanese/Korean seed indexes, and remove the capability declarations in this document.

## Japan/Korea Market Review v1 (Issue #1815 Phase 2)

`MARKET_REVIEW_REGION` adds `jp` and `kr`, included in `both` multi-market order: `cn,hk,us,jp,kr`.

Scope of support:

- `jp`: Fetches Nikkei 225 `^N225` and TOPIX `^TOPX` via Yahoo Finance, outputting Japanese stock market review. Verifiable pages:
  - `^N225`: <https://finance.yahoo.com/quote/%5EN225/>
  - `^TOPX`: <https://finance.yahoo.com/quote/%5ETOPX/>
- `kr`: Fetches KOSPI `^KS11` and KOSDAQ `^KQ11` via Yahoo Finance, outputting Korean stock market review. Verifiable pages:
  - `^KS11`: <https://finance.yahoo.com/quote/%5EKS11/>
  - `^KQ11`: <https://finance.yahoo.com/quote/%5EKQ11/>
- Web settings page input for `MARKET_REVIEW_REGION` as comma-separated subsets (e.g., `cn,jp`, `cn,us,jp,kr`); trading-day check filters `both` for markets open that day per `XTKS / Asia/Tokyo` and `XKRX / Asia/Seoul`.
- Review strategy, news search terms, Prompt market semantics, and Chinese/English notification titles all use JP/KR independent profiles.

Notes (compatibility and acceptance criteria):

- Live data availability comes from Yahoo Finance index pages and API contracts; the current implementation only covers index routing and degradation behavior in `data_provider/yfinance_fetcher.py`; no stability commitment for realtime quote connectivity.
- Local automated verification for this target defaults to offline regression: `tests/test_yfinance_jp_kr_indices.py`, `tests/test_yfinance_hk_indices.py` (shared mapping/fallback) and `tests/test_trading_calendar.py` (trading-day filtering). For supplementary live availability verification, directly visit the above Yahoo Finance pages in a network-connected environment for one-time spot checks.

- External compatibility boundaries (current implementation default assumptions):
  - Data source: `yfinance` (version floor `yfinance>=0.2.0` in `requirements.txt`)
  - Long-term constraint: `^N225`, `^TOPX`, `^KS11`, `^KQ11` must have searchable quote pages on the Yahoo Finance side; inability to search is treated as index-level unavailability, with `market_review` fail-open mechanism degrading to existing market output without interrupting the main flow.
- Compatibility verification (verifiable):
  - <https://finance.yahoo.com/quote/%5EN225/>
  - <https://finance.yahoo.com/quote/%5ETOPX/>
  - <https://finance.yahoo.com/quote/%5EKS11/>
  - <https://finance.yahoo.com/quote/%5EKQ11/>
  - Reproducible online verification command (optional):
```bash
python - <<'PY'
from yfinance import Ticker
for symbol in ("^N225", "^TOPX", "^KS11", "^KQ11"):
    data = Ticker(symbol).history(period="5d")
    print(symbol, "rows", len(data))
PY
```

Boundaries:

- JP/KR market review v1 does not provide advance/decline counts, limit up/down, industry/sector rankings, or capital flow statistics; in structured payloads, `breadth` only appears when market breadth data is available.
- A single JP/KR index fetch failure follows existing yfinance fail-open logic to skip without dragging down other indices or markets.
- If `exchange-calendars` lacks the corresponding exchange calendar, existing trading-day fail-open/fail-closed semantics continue.

Rollback: Remove `jp` / `kr` from `MARKET_REVIEW_REGION` valid values, Web settings enum, MarketProfile/MarketStrategy, `_MARKET_REVIEW_MARKETS`, and the capability declarations in this document.

## Taiwan Individual Stock Support (Suffix-Only, Issue #1772 / #1777)

The current phase supports manually entering Yahoo Finance suffix codes for Taiwan stocks, entering the existing individual stock analysis, history persistence, report rendering, DecisionSignal, Portfolio, and Intelligence pipeline. TWSE-listed stocks use the `.TW` suffix and TPEx-listed (OTC) stocks use the `.TWO` suffix, both folded under the same `tw` market label.

The Taiwan stock pipeline has converged from the early MVP to a first-class individual stock analysis market: market identification, data routing, trading calendar/market phase, YFinance daily data and basic quotes, major indices, service layer/API/Web market enum, TWD currency annotation, institutional investor report blocks, and LLM Prompt consumption are all integrated. Boundaries that still need to be preserved: Taiwan stock pool seeds/autocomplete, market review `MARKET_REVIEW_REGION=tw`, Market Light market red/green light alerts, and complete Taiwan market breadth/sector rankings are not yet included.

Supported formats:

- Listed (TWSE): `2330.TW`, `0050.TW`
- OTC (TPEx): `6488.TWO`, `5483.TWO`
- Code base is 4-6 digits (common stocks 4 digits, ETF/others up to 6 digits, e.g., `00878.TW`, `006208.TW`), wider than the 4-5 digits of Japanese stock `.T`.

Constraints and boundaries:

- **Strict suffix-only**: Bare `2330`, `00878`, etc. without suffix do not enter Taiwan stock semantics (`detect_market` / `get_market_for_stock` only returns `tw` with explicit `.TW`/`.TWO` suffix). No Taiwan stock index/seed parsing is built in; Web autocomplete does not guarantee a complete Taiwan stock pool; unmatched cases require manual entry of the full suffix code.
- Taiwan stock daily data and basic realtime/near-realtime quotes only use `YfinanceFetcher`, without attempting A-share-specific data sources.
- Fundamentals reuse the existing offshore yfinance lightweight path; the `institution` block additionally consumes Taiwan stock three institutional investor data and renders it in the report; A-share-specific capital flows, dragon-tiger lists, and sectors degrade to `not_supported`.
- Report Prompts have added Taiwan stock market semantics (New Taiwan Dollar, three institutional investors, TWSE/TPEx ±10% limit up/down), injecting three institutional investor net buy/sell into the LLM analysis context, avoiding application of A-share northbound capital and dragon-tiger list concepts.
- Trading calendar registers `tw: XTAI / Asia/Taipei`. TWSE trades continuously from 09:00–13:30 with no lunch break; closing auction 13:25–13:30 is modeled with a 5-minute heuristic window (`_CLOSING_AUCTION_WINDOW_MINUTES["tw"]=5`, `market_phase` can return `closing_auction`). JP/KR also have closing auction windows aligned with regular trading sessions (JP 15:25-15:30, KR 15:20-15:30). If the local `exchange-calendars` version lacks the corresponding calendar, existing fail-open/fail-closed semantics remain unchanged.
- Major indices include the TAIEX `^TWII` and TPEx Index `^TWOII`.
- Three institutional investor buy/sell (institutional flows) data layer: `TwInstitutionalFetcher` (`data_provider/tw_institutional_fetcher.py`) provides daily foreign investors, investment trusts, dealers, and three institutional investor buy/sell for listed (TWSE T86, legacy `rwd` endpoint) / OTC (TPEx OpenAPI) (unit: **shares**; cached per day per market, then filtered by individual stock; TPEx ROC year to Gregorian year conversion has unit test coverage). API failure/rate-limit/empty response/missing fields all **fail-open** returning no data without interrupting analysis; only effective for `.TW`/`.TWO` without changing existing market flow. Data source is government open data under the "Government Data Open Authorization License v1" (OGDL v1, allows commercial use and redistribution, requires source attribution).
- The three institutional investor fetcher has concurrency cache anti-cache-breakdown and TWSE/TPEx split circuit breaker protection; TPEx OpenAPI only serves the latest trading day; passing a specific date that does not match the served date returns no data via fail-open, avoiding wrong-date data silently entering the report.
- Taiwan stock financial amounts use TWD -> "New Taiwan Dollar" annotation to avoid falling into the A-share context default "yuan".

Not committed:

- Not committed to realtime quotes; Yahoo Finance data may be delayed or have missing fields.
- Not committed to complete fundamentals, industry/sectors, market breadth, advance/decline counts, or Taiwan stock market review; `MARKET_REVIEW_REGION` still only accepts `cn/hk/us/jp/kr/both` or comma subsets of these markets.
- Taiwan stock indexes/seeds and Web autocomplete are not yet fully integrated; alert MarketRegion and backend Market Light alerts remain `cn/hk/us` without `tw`.
- Does not complete Portfolio's TWD exchange rates, cost basis, or market value full scope; Taiwan stock Portfolio currently belongs to partial valuation markets.

Rollback: Remove `tw` market identification, trading calendar registration, YFinance routing extensions, three institutional investor data layer/report consumption, TWD annotation, service layer/API market enum, and frontend market type release; remove the capability declarations in this document.

## Japan/Korea Portfolio & Market Light Boundaries (Issue #1815 Phase 3)

Portfolio allows JP/KR accounts, trades, and position snapshots into the existing pipeline but marks account/position snapshots as `data_quality=partial` and explicitly indicates `realtime_quote_best_effort`, `fx_and_cost_basis_partial`, `sector_and_risk_metrics_limited` via `limitations`; no commitment to complete JPY/KRW exchange rates, cost basis, market value, industry concentration, or portfolio risk metrics.

- JP/KR account, trade, cash flow, and corporate action APIs remain creatable/queryable; no new JPY/KRW exchange rate sources, tax models, trading unit/tick size validation, or industry mapping added this round.
- Market Light snapshots and Market Light alerts still only support `cn` / `hk` / `us`.
- Web alert market dropdown does not display `jp` / `kr`; backend `normalize_market_region()` returns an explicit unsupported error for `jp` / `kr`.
- Web settings page `MARKET_REVIEW_REGION` converges from a fixed-enum dropdown to free-text input for saving comma-separated subsets like `cn,us,jp`, `cn,hk,us`; this UI change only affects market review configuration, not Market Light alert market enum.
- Existing `cn`, `hk`, `us` in `MARKET_REVIEW_REGION` can be retained as-is; if users want to maintain the three-market review boundary that `both` corresponded to before JP/KR expansion, change to `cn,hk,us`; only use `both` or explicitly configure `cn,hk,us,jp,kr` when intending five-market review.
- This boundary convergence does not change LLM Provider / Model / Base URL persistence semantics and does not execute default model, runtime configuration cleanup, or writeback; configuration updates remain **atomic upsert** (`ConfigManager.apply_updates`), save/import only writes submitted keys, unsubmitted old values such as `LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `AGENT_LITELLM_MODEL`, `VISION_MODEL`, `OPENAI_BASE_URL` are preserved without clearing.
- Directly verifiable configuration compatibility evidence: no new or replaced external provider/model/Base URL this round, still using LiteLLM OpenAI-compatible routing (<https://docs.litellm.ai/docs/providers/openai_compatible>), OpenAI Chat Completions request shapes (<https://platform.openai.com/docs/api-reference/chat/create>), and provider official source links centrally maintained in [LLM Provider Configuration Guide](llm-providers.md#official-sources-and-compatibility). Current runtime dependency window is `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0` per `requirements.txt`; old configurations have no migration scripts or cleanup branches, save/import still writes only submitted keys via `ConfigManager.apply_updates`. Rollback path is restoring `MARKET_REVIEW_REGION` from pre-change `.env`/configuration backup, or directly reverting this PR; unsubmitted `LITELLM_CONFIG`, `LLM_CHANNELS`, `LLM_OPENAI_*`, `LITELLM_MODEL`, `AGENT_LITELLM_MODEL`, `LITELLM_FALLBACK_MODELS`, `VISION_MODEL`, `OPENAI_*` existing runtime configurations need no migration. Regression evidence: `tests/test_system_config_service.py::SystemConfigServiceTestCase::test_update_market_review_region_does_not_trigger_runtime_model_cleanup` and `tests/test_config_env_compat.py::test_market_review_region_updates_do_not_change_llm_provider_model_contract`.
- Web UI visual evidence scope: when Market Light alert target scope is switched to "Market Overview", the market region dropdown only displays A-shares, Hong Kong stocks, and US stocks without Japanese/Korean stocks; settings page `MARKET_REVIEW_REGION` renders as a text input box for comma-separated values. The repository does not save one-time screenshot evidence; alternative evidence includes assertions in `apps/dsa-web/src/components/alerts/__tests__/AlertRuleForm.test.tsx`, `apps/dsa-web/src/components/settings/__tests__/SettingsField.test.tsx`, and `apps/dsa-web/tests/system_config_i18n.test.ts`.

Rollback: Remove Portfolio snapshot `data_quality` / `limitations` extensions, restore alert frontend/backend old boundary descriptions for market enum; for full rollback, remove `jp/kr` market identification, trading calendar registration, YFinance routing extensions, Web/API type release, `scripts/stock_index_seeds/` Japanese/Korean seed indexes, and remove the capability declarations in this document.
