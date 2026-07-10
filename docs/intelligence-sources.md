# News / Intelligence Sources MVP

Issue #1386's v1 capability focuses on "compliant news source collection, local persistence, and queryable evidence," without mixing RSS/Atom into on-demand search semantics or defaulting to adding an independent sentiment page.

## Capability Scope

- Supports configuring RSS / Atom HTTP(S) news sources.
- Supports NewsNow HTTP JSON sources, with built-in defaults for mainstream financial sources including Cailianshe Hot, Xueqiu Hot Stocks, Wall Street CN Flash, Jin10 Data, and Gelonghui Events.
- Supports querying built-in RSS/Atom/NewsNow templates, and creating testable, toggleable news sources from templates; one-click creation of all built-in default sources is also supported.
- Saves news source configuration, enabled status, scope, and last fetch status.
- Fetched items are persisted to `intelligence_items`, saving title, summary, URL, source, publish time, fetch time, market, and scope.
- Deduplication by URL; items without URLs use `no-url:intel:<hash>` as the fallback key.
- Supports `symbol` / `market` / `sector` scope, as well as `cn` / `hk` / `us` / `jp` / `kr` / `tw` / `global` market markers.
- Fetch batching uses fail-open: a single source failure does not block other sources or the main analysis chain.
- Supports retention cleanup to prevent unbounded growth of the news pool.

## Security Boundaries

Custom URLs undergo basic validation:

- Only absolute `http` / `https` URLs are allowed;
- URLs containing username/password are prohibited;
- `localhost`, `.local`, loopback addresses, intranet addresses, link-local addresses, reserved addresses, shared address ranges, and multicast addresses are prohibited;
- Environment proxies (e.g., `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`) are explicitly disabled during parsing and fetching stages to avoid bypassing validation via environment proxies;
- During the actual connection stage, the target host's DNS resolution is re-validated to prevent post-validation resolution drift to restricted addresses;
- Redirected final URLs are also re-validated;
- Error messages sanitize common `token` / `key` / `secret` query parameters.

Explicitly out of scope: no anti-scraping, simulated login, cookie harvesting, or unauthorized portal direct fetching.

## Configuration

```env
NEWS_INTEL_RETENTION_DAYS=30
NEWS_INTEL_FETCH_TIMEOUT_SEC=8
NEWS_INTEL_MAX_ITEMS_PER_SOURCE=50
NEWS_INTEL_AUTO_FETCH_ENABLED=false
NEWSNOW_BASE_URL=https://newsnow.busiyi.world
```

`NEWSNOW_BASE_URL` is used to construct `GET {NEWSNOW_BASE_URL}/api/s?id=<source_id>`.

`NEWS_INTEL_AUTO_FETCH_ENABLED` is disabled by default. When set to `true`, individual stock analysis, Agent analysis, and market review will perform a fail-open auto-refresh before reading the local news pool: built-in news sources that are missing are automatically created and enabled, built-in default sources that exist but are disabled are re-enabled, then all enabled sources are fetched and written to `intelligence_items`. To avoid repeated external site requests per stock, there is a 60-minute cooldown within the running process; during cooldown, local library data is reused.

**External dependency compatibility notes:**

- **Official project and deployment guide**: https://github.com/qqhann/newsnow
- **Current default** `https://newsnow.busiyi.world` is a public demo instance, **not an official deployment**, with the following risks:
  - May become unavailable due to official maintenance, rate limiting, or service discontinuation
  - Stability, reliability, or data accuracy is not guaranteed; used only for demonstration and testing
  - All users point to the same public instance and may encounter rate limiting
- **Production environment strongly recommended**: Self-host a NewsNow instance or connect to a confirmed controllable private/enterprise deployment to ensure stability and data reliability

**API contract compatibility verification (required before deployment):**

- Verify basic reachability and response format:
  ```bash
  curl -sS "${NEWSNOW_BASE_URL}/api/s?id=cls-hot" | python -c "import sys, json; data=json.load(sys.stdin); assert isinstance(data, dict) and isinstance(data.get('items'), list); print('OK')"
  ```
- Detailed field compatibility can be referenced in the automated test: `test_newsnow_source_fetches_json_items`, covering `status`, `id`, `items[].title`, `items[].url`/`mobileUrl`, `items[].pubDate`/`items[].extra.date`, and other fields.
- **Deployed instances are not within automated go-live guarantees**; if relying on the public demo instance, the above verification must be performed in the actual production environment before deployment.

## API

All endpoints are under `/api/v1/intelligence`.

- `POST /sources`: Create a news source.
- `GET /sources`: Query news sources.
- `GET /sources/templates?market=hk`: Query built-in news source templates.
- `POST /sources/templates/{template_id}`: Create a news source from a built-in template, with overrides for name, enabled status, scope, and description.
- `POST /sources/defaults`: One-click creation of all built-in default sources; the endpoint is idempotent — existing sources with the same name return `created=false` without duplicate insertion. When `enabled` is not passed, defaults to `false`; to enable by default, pass `{ "enabled": true }`.
- `POST /sources/test`: Test payload without persistence.
- `POST /sources/{source_id}/fetch?dry_run=false`: Fetch a single source.
- `POST /sources/fetch-enabled`: Fail-open fetch of all enabled sources.
- `GET /items?scope_type=market&market=cn&days=7`: Query news items.

If you want automatic "create source -> fetch -> persist -> analysis consumption" in local `.env`, Docker, or other runtimes with explicit environment variable passthrough, set:

```env
NEWS_INTEL_AUTO_FETCH_ENABLED=true
```

This toggle represents explicit user consent for the runtime to access configured external RSS/Atom/NewsNow HTTP sources; defaulting to off avoids unconfirmed external requests, public NewsNow demo instance pressure, and analysis prompt input changes.

> Note: This toggle only takes effect when visible in the actual runtime process environment variables. The repository's default `00-daily-analysis.yml` uses an allowlist mapping strategy for `env`; when not explicitly listed in the mapping, even setting a same-name variable in the repository's Variables/Secrets will not inject it into the runtime environment, so the default workflow will not automatically receive this toggle. To enable this capability in the repository's built-in daily analysis task, add explicit variable passthrough in the workflow, or run locally/Docker with the environment variable configured directly.

## NewsNow Default Sources

NewsNow is not RSS but an aggregation hotspot platform. DSA reads its JSON response directly via HTTP API without needing MCP:

```text
GET {NEWSNOW_BASE_URL}/api/s?id=cls-hot
```

This PR first integrates the following finance-related default sources to ensure the "source config -> fetch -> persist -> analysis read" pipeline runs end-to-end:

- `cls-hot`: Cailianshe Hot, biased toward A-shares and theme hotspots.
- `xueqiu-hotstock`: Xueqiu Hot Stocks, biased toward individual stock attention.
- `wallstreetcn-quick`: Wall Street CN Flash, biased toward macro, commodities, and market events.
- `jin10`: Jin10 Data, biased toward global macro and offshore events.
- `gelonghui`: Gelonghui Events, biased toward Hong Kong and ADR context.

If more domestic platforms are needed, additional NewsNow sources can be added via `POST /sources` with `source_type=newsnow` and `url` set to `https://<your-newsnow>/api/s?id=<source_id>`. If you prefer RSS, compliant RSS sources like RSSHub can also be integrated via `source_type=rss`.

## Follow-up Integration Recommendations

Beyond the v1 baseline, the analysis chain will best-effort read the local news pool:

- Individual stock traditional analysis prioritizes reading `symbol=<stock_code>` news and supplements same-market `market`-level news; content is appended to the existing `news_context` and saved with the AnalysisContextPack summary and historical `news_content`.
- Agent analysis also injects local news evidence via `news_context`, avoiding the need for the Agent to re-search to see already-persisted news.
- Market review merges same-market `market`-level news into the market news list; Prompt, structured payload, and report news fields all show source links.
- If `NEWS_INTEL_AUTO_FETCH_ENABLED=true`, the above entry points will first perform a fail-open auto-refresh of the local news pool; refresh failures do not block analysis.
- This capability only adds a local news consumption path without changing model names, provider/base URL, default model strategy, fallback strategy, `save_context_snapshot` pre-cleanup logic, or runtime configuration semantics; it is compatible with existing deployment configurations, and rollback involves removing the local news integration entry point or removing local news source configuration/data.

Follow-up PRs can continue to improve the NewsNow HTTP provider, report evidence display, and Web settings/report viewing entry points.

## Compatibility & Rollback Notes (Issue #1386)

- This feature does not modify third-party LLM provider semantics and does not add new provider/model/base URL/default model strategy/runtime routing or configuration migration branches.
- Model/API compatibility risks flagged in structured detection do not apply to this change: the `news_context` injection chain only reuses existing LLM analysis input construction flow (`src/core/pipeline.py`, `src/market_analyzer.py`, `src/analyzer.py`) and does not add `.env` writes, pre-save cleanup, or clear/backfill logic.
- Rollback: `revert` this PR; for degraded configuration, only disable and remove local news source configuration (including `sources` table and `intelligence_items` existing data); existing models, providers, or other historical analysis chains are unaffected.

## PR Reusable Content (Issue #1386)

- Refs: `#1386`
- Compatibility conclusion: This change only adds a local news consumption path without changing model name/provider/base URL/default model strategy/fallback strategy/pre-save cleanup logic/runtime configuration migration. The extensions to `news_context` and `market_review_payload` are best-effort additions that do not affect existing contracts and compatibility boundaries.
- Rollback plan: The minimum rollback path is `revert this PR`; for degraded integration only, local news sources (`sources` and `intelligence_items`) can be disabled and cleaned up at runtime.
