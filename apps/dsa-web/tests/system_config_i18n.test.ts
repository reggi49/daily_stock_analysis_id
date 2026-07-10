import { describe, expect, it } from 'vitest';
import { UI_TEXT } from '../src/i18n/uiText';
import { getSettingsHelpContent } from '../src/locales/settingsHelp';
import { getFieldDescriptionZh, getFieldOptionLabelZh, getFieldTitleZh } from '../src/utils/systemConfigI18n';

const requiredLocalizedKeys = [
  'TICKFLOW_API_KEY',
  'TICKFLOW_PRIORITY',
  'TICKFLOW_KLINE_ADJUST',
  'TICKFLOW_BATCH_DAILY_ENABLED',
  'TICKFLOW_BATCH_SIZE',
  'STOCK_INDEX_REMOTE_UPDATE_ENABLED',
  'SEARXNG_BASE_URLS',
  'ENABLE_REALTIME_QUOTE',
  'ENABLE_CHIP_DISTRIBUTION',
  'PYTDX_HOST',
  'PYTDX_PORT',
  'PYTDX_SERVERS',
  'BIAS_THRESHOLD',
  'GENERATION_BACKEND',
  'GENERATION_FALLBACK_BACKEND',
  'GENERATION_BACKEND_TIMEOUT_SECONDS',
  'GENERATION_BACKEND_MAX_OUTPUT_BYTES',
  'GENERATION_BACKEND_MAX_CONCURRENCY',
  'LOCAL_CLI_BACKEND_MAX_CONCURRENCY',
  'LLM_PROMPT_CACHE_TELEMETRY_ENABLED',
  'LLM_PROMPT_CACHE_HINTS_ENABLED',
  'LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL',
  'LLM_USAGE_HMAC_SECRET',
  'LLM_USAGE_HMAC_KEY_VERSION',
  'TELEGRAM_BOT_TOKEN',
  'TELEGRAM_CHAT_ID',
  'TELEGRAM_MESSAGE_THREAD_ID',
  'FEISHU_STREAM_ENABLED',
  'DINGTALK_STREAM_ENABLED',
  'EMAIL_SENDER',
  'EMAIL_PASSWORD',
  'EMAIL_RECEIVERS',
  'DISCORD_WEBHOOK_URL',
  'DISCORD_BOT_TOKEN',
  'DISCORD_MAIN_CHANNEL_ID',
  'DISCORD_INTERACTIONS_PUBLIC_KEY',
  'SLACK_BOT_TOKEN',
  'SLACK_CHANNEL_ID',
  'SLACK_WEBHOOK_URL',
  'PUSHPLUS_TOPIC',
  'PUSHOVER_USER_KEY',
  'PUSHOVER_API_TOKEN',
  'SERVERCHAN3_SENDKEY',
  'ASTRBOT_URL',
  'ASTRBOT_TOKEN',
  'CUSTOM_WEBHOOK_BEARER_TOKEN',
  'WEBHOOK_VERIFY_SSL',
  'SINGLE_STOCK_NOTIFY',
  'REPORT_TYPE',
  'REPORT_LANGUAGE',
  'REPORT_TEMPLATES_DIR',
  'REPORT_INTEGRITY_ENABLED',
  'REPORT_RENDERER_ENABLED',
  'REPORT_INTEGRITY_RETRY',
  'REPORT_HISTORY_COMPARE_N',
  'MERGE_EMAIL_NOTIFICATION',
  'NOTIFICATION_REPORT_CHANNELS',
  'NOTIFICATION_ALERT_CHANNELS',
  'NOTIFICATION_SYSTEM_ERROR_CHANNELS',
  'NOTIFICATION_DEDUP_TTL_SECONDS',
  'NOTIFICATION_COOLDOWN_SECONDS',
  'NOTIFICATION_QUIET_HOURS',
  'NOTIFICATION_TIMEZONE',
  'NOTIFICATION_MIN_SEVERITY',
  'NOTIFICATION_DAILY_DIGEST_ENABLED',
  'SCHEDULE_ENABLED',
  'SCHEDULE_RUN_IMMEDIATELY',
  'TRADING_DAY_CHECK_ENABLED',
  'WEBUI_HOST',
  'LOG_DIR',
  'WEBUI_ENABLED',
  'WEBUI_AUTO_BUILD',
  'ADMIN_AUTH_ENABLED',
  'TRUST_X_FORWARDED_FOR',
  'RUN_IMMEDIATELY',
  'MARKET_REVIEW_ENABLED',
  'DAILY_MARKET_CONTEXT_ENABLED',
  'MARKET_REVIEW_REGION',
  'ANALYSIS_DELAY',
  'SAVE_CONTEXT_SNAPSHOT',
  'DEBUG',
  'AGENT_GENERATION_BACKEND',
  'AGENT_NL_ROUTING',
  'AGENT_DEEP_RESEARCH_BUDGET',
  'AGENT_DEEP_RESEARCH_TIMEOUT',
  'AGENT_EVENT_MONITOR_ENABLED',
  'AGENT_EVENT_MONITOR_INTERVAL_MINUTES',
  'AGENT_EVENT_ALERT_RULES_JSON',
] as const;

describe('systemConfigI18n required key coverage', () => {
  it('provides zh title and description mapping for known missing keys', () => {
    requiredLocalizedKeys.forEach((key) => {
      expect(getFieldTitleZh(key, key)).not.toBe(key);
      expect(getFieldDescriptionZh(key, 'schema fallback description')).not.toBe('schema fallback description');
    });
  });

  it('uses a Chinese primary title for SearXNG base URLs', () => {
    const title = getFieldTitleZh('SEARXNG_BASE_URLS', 'SEARXNG_BASE_URLS');

    expect(title).toBe('SearXNG 自建实例地址');
    expect(title).not.toBe('SearXNG Base URLs');
  });

  it('documents LLM usage HMAC privacy boundaries', () => {
    const zh = getSettingsHelpContent('settings.ai_model.LLM_USAGE_HMAC_SECRET', undefined, 'zh-CN');
    const en = getSettingsHelpContent('settings.ai_model.LLM_USAGE_HMAC_SECRET', undefined, 'en');

    expect(zh?.summary).toContain('HMAC');
    expect(zh?.notes?.join(' ')).toContain('不要');
    expect(en?.summary).toContain('HMAC');
    expect(en?.notes?.join(' ')).toContain('Do not');
  });
});

describe('systemConfigI18n option label localization', () => {
  const realSelectOptionCases = [
    ['NEWS_STRATEGY_PROFILE', 'ultra_short', undefined, 'Ultra short (1 day)'],
    ['NEWS_STRATEGY_PROFILE', 'short', undefined, 'Short (3 days)'],
    ['NEWS_STRATEGY_PROFILE', 'medium', undefined, 'Medium (7 days)'],
    ['NEWS_STRATEGY_PROFILE', 'long', undefined, 'Long (30 days)'],
    ['REPORT_TYPE', 'simple', undefined, 'Simple'],
    ['REPORT_TYPE', 'full', undefined, 'Full'],
    ['REPORT_TYPE', 'brief', undefined, 'Brief'],
    ['REPORT_LANGUAGE', 'zh', 'Chinese', 'Chinese'],
    ['REPORT_LANGUAGE', 'en', 'English', 'English'],
    ['NOTIFICATION_MIN_SEVERITY', '', 'Not set', 'Not set'],
    ['NOTIFICATION_MIN_SEVERITY', 'info', 'info', 'Info'],
    ['NOTIFICATION_MIN_SEVERITY', 'warning', 'warning', 'Warning'],
    ['NOTIFICATION_MIN_SEVERITY', 'error', 'error', 'Error'],
    ['NOTIFICATION_MIN_SEVERITY', 'critical', 'critical', 'Critical'],
    ['LOG_LEVEL', 'DEBUG', undefined, 'Debug'],
    ['LOG_LEVEL', 'INFO', undefined, 'Info'],
    ['LOG_LEVEL', 'WARNING', undefined, 'Warning'],
    ['LOG_LEVEL', 'ERROR', undefined, 'Error'],
    ['LOG_LEVEL', 'CRITICAL', undefined, 'Critical'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'off', undefined, 'Close'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'basic', undefined, 'Basic'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'debug', undefined, 'Debug'],
    ['MARKET_REVIEW_COLOR_SCHEME', 'green_up', 'Green Up / Red Down', 'Green up / Red down'],
    ['MARKET_REVIEW_COLOR_SCHEME', 'red_up', 'Red Up / Green Down', 'Red up / Green down'],
    ['GENERATION_BACKEND', 'litellm', undefined, 'Default model settings'],
    ['GENERATION_FALLBACK_BACKEND', 'litellm', undefined, 'Default model settings'],
    ['AGENT_GENERATION_BACKEND', 'auto', 'Auto', 'Auto'],
    ['AGENT_GENERATION_BACKEND', 'litellm', undefined, 'Default model settings'],
    ['AGENT_ARCH', 'single', 'Single Agent', 'Single Agent'],
    ['AGENT_ARCH', 'multi', 'Multi Agent (Orchestrator)', 'Multi Agent (Orchestrator)'],
    ['AGENT_ORCHESTRATOR_MODE', 'quick', 'Quick', 'Quick'],
    ['AGENT_ORCHESTRATOR_MODE', 'standard', 'Standard', 'Standard'],
    ['AGENT_ORCHESTRATOR_MODE', 'full', 'Full', 'Full'],
    ['AGENT_ORCHESTRATOR_MODE', 'specialist', 'Specialist', 'Specialist'],
    ['AGENT_SKILL_ROUTING', 'auto', 'Auto (Regime-based)', 'Auto (Regime-based)'],
    ['AGENT_SKILL_ROUTING', 'manual', 'Manual (Use AGENT_SKILLS)', 'Manual (Use AGENT_SKILLS)'],
  ] as const;

  it('localizes all select options currently exposed by system config schema', () => {
    realSelectOptionCases.forEach(([key, value, fallbackLabel, expectedLabel]) => {
      const label = getFieldOptionLabelZh(key, value, fallbackLabel);

      expect(label).toBe(expectedLabel);
      expect(label).not.toBe(value);
      if (fallbackLabel) {
        expect(label).not.toBe(fallbackLabel);
      }
    });
  });

  it('treats free-text config keys as passthrough for option labels', () => {
    expect(getFieldOptionLabelZh('MARKET_REVIEW_REGION', 'cn')).toBe('cn');
    expect(getFieldOptionLabelZh('MARKET_REVIEW_REGION', 'cn,us,jp,kr')).toBe('cn,us,jp,kr');
  });
});

describe('SAVE_CONTEXT_SNAPSHOT settings help contract', () => {
  it('describes the persistence boundary without implying old records are changed', () => {
    const help = getSettingsHelpContent('settings.system.SAVE_CONTEXT_SNAPSHOT', undefined, 'zh-CN');
    const text = [
      help?.summary,
      help?.usage,
      ...(help?.valueNotes ?? []),
      ...(help?.impact ?? []),
      ...(help?.notes ?? []),
    ].join('\n');

    expect(text).toContain('New history records');
    expect(text).toContain('Does not disable current AnalysisContextPack build');
    expect(text).toContain('Does not disable LLM Prompt');
    expect(text).not.toContain('Old records');
  });
});

describe('generation backend settings help contract', () => {
  it('uses user-facing generation channel copy instead of implementation terms', () => {
    const zhInlineText = [
      getFieldTitleZh('GENERATION_BACKEND', ''),
      getFieldDescriptionZh('GENERATION_BACKEND', ''),
      getFieldTitleZh('GENERATION_FALLBACK_BACKEND', ''),
      getFieldDescriptionZh('GENERATION_FALLBACK_BACKEND', ''),
      getFieldTitleZh('GENERATION_BACKEND_TIMEOUT_SECONDS', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_TIMEOUT_SECONDS', ''),
      getFieldTitleZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', ''),
      getFieldTitleZh('GENERATION_BACKEND_MAX_CONCURRENCY', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_MAX_CONCURRENCY', ''),
      getFieldTitleZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', ''),
      getFieldDescriptionZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', ''),
      getFieldTitleZh('AGENT_GENERATION_BACKEND', ''),
      getFieldDescriptionZh('AGENT_GENERATION_BACKEND', ''),
    ].join('\n');
    const zhBackend = getSettingsHelpContent('settings.ai_model.GENERATION_BACKEND', undefined, 'zh-CN');
    const enBackend = getSettingsHelpContent('settings.ai_model.GENERATION_BACKEND', undefined, 'en');
    const zhFallback = getSettingsHelpContent('settings.ai_model.GENERATION_FALLBACK_BACKEND', undefined, 'zh-CN');
    const enFallback = getSettingsHelpContent('settings.ai_model.GENERATION_FALLBACK_BACKEND', undefined, 'en');
    const zhAgent = getSettingsHelpContent('settings.agent.AGENT_GENERATION_BACKEND', undefined, 'zh-CN');
    const enAgent = getSettingsHelpContent('settings.agent.AGENT_GENERATION_BACKEND', undefined, 'en');
    const zhText = [
      zhBackend?.title,
      zhBackend?.summary,
      zhBackend?.usage,
      ...(zhBackend?.valueNotes ?? []),
      ...(zhBackend?.impact ?? []),
      ...(zhBackend?.notes ?? []),
      zhFallback?.title,
      zhFallback?.summary,
      zhFallback?.usage,
      ...(zhFallback?.valueNotes ?? []),
      ...(zhFallback?.impact ?? []),
      ...(zhFallback?.notes ?? []),
      zhAgent?.title,
      zhAgent?.summary,
      zhAgent?.usage,
      ...(zhAgent?.valueNotes ?? []),
      ...(zhAgent?.impact ?? []),
      ...(zhAgent?.notes ?? []),
    ].join('\n');
    const enText = [
      enBackend?.title,
      enBackend?.summary,
      enBackend?.usage,
      ...(enBackend?.valueNotes ?? []),
      ...(enBackend?.impact ?? []),
      ...(enBackend?.notes ?? []),
      enFallback?.title,
      enFallback?.summary,
      enFallback?.usage,
      ...(enFallback?.valueNotes ?? []),
      ...(enFallback?.impact ?? []),
      ...(enFallback?.notes ?? []),
      enAgent?.title,
      enAgent?.summary,
      enAgent?.usage,
      ...(enAgent?.valueNotes ?? []),
      ...(enAgent?.impact ?? []),
      ...(enAgent?.notes ?? []),
    ].join('\n');

    expect(zhBackend?.title).toBe('Analysis generation method');
    expect(zhFallback?.title).toBe('Fallback generation method');
    expect(zhAgent?.title).toBe('Ask-Stock generation method');
    expect(getFieldTitleZh('GENERATION_BACKEND_TIMEOUT_SECONDS', '')).toBe('Generation timeout (seconds)');
    expect(getFieldTitleZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', '')).toBe('Maximum output size (bytes)');
    expect(getFieldTitleZh('GENERATION_BACKEND_MAX_CONCURRENCY', '')).toBe('Max model generation concurrency');
    expect(getFieldTitleZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', '')).toBe('Local CLI max concurrency');
    expect(zhBackend?.showFieldKey).toBe(false);
    expect(zhFallback?.showFieldKey).toBe(false);
    expect(zhAgent?.showFieldKey).toBe(false);
    expect(zhBackend?.examples).toEqual([]);
    expect(zhFallback?.examples).toEqual([]);
    expect(zhAgent?.examples).toEqual([]);
    expect(zhInlineText).toContain('Stock analysis');
    expect(zhInlineText).toContain('Ask-Stock assistant');
    expect(zhInlineText).toContain('currently available method');
    expect(zhInlineText).not.toContain('Follows the currently available model channel');
    expect(zhText).toContain('Stock analysis');
    expect(zhText).toContain('Market Review');
    expect(zhText).toContain('Auto');
    expect(zhBackend?.usage).toContain('Default model settings');
    expect(zhFallback?.usage).toContain('Default model settings');
    expect(zhAgent?.usage).toContain('currently available method');
    expect(zhAgent?.valueNotes).toContain('如果不确定，选择“自动”即可。');
    expect(zhText).not.toContain('Prioritizes currently available');
    expect(zhText).not.toContain('unsupported_tool_calling');
    expect(zhText).not.toContain('run_agent_loop');
    [
      'Backend',
      'backend',
      'backend-level',
      'generation backend',
      'self fallback',
      'stdout',
      'stderr',
      'contract',
      'MAX_WORKERS',
      'Router',
      'diagnostics',
      'executable',
      'coding-agent',
      'experimental/limited',
      'fail-fast',
      'LiteLLM',
    ].forEach((term) => {
      expect(zhInlineText).not.toContain(term);
      expect(zhText).not.toContain(term);
    });

    expect(enBackend?.title).toBe('Analysis Generation Method');
    expect(enFallback?.title).toBe('Fallback Generation Method');
    expect(enAgent?.title).toBe('Ask-Stock Generation Method');
    expect(enText).toContain('stock analysis');
    expect(enText).toContain('market reviews');
    expect(enText).toContain('Auto');
    expect(enBackend?.usage).toContain('Default model settings');
    expect(enFallback?.usage).toContain('Default model settings');
    expect(enAgent?.usage).toContain('currently available method');
    expect(enAgent?.valueNotes).toContain('If you are unsure, choose Auto.');
    expect(enBackend?.notes?.join('\n')).toContain('Default model settings continue');
    expect(enBackend?.notes?.join('\n')).not.toContain('Advanced note');
    expect(enBackend?.notes?.join('\n')).not.toContain('LiteLLM');
    expect(enText).not.toContain('current available model channel');
    expect(enText).not.toContain('unsupported_tool_calling');
    expect(enText).not.toContain('run_agent_loop');
  });
});

describe('generation backend status panel i18n contract', () => {
  it('keeps the new status panel copy localized in both UI languages', () => {
    expect(UI_TEXT.zh['settings.generationBackendStatus']).toBe('Generation backend status');
    expect(UI_TEXT.zh['settings.generationBackendSmokeTest']).toBe('JSON smoke test');
    expect(UI_TEXT.zh['settings.generationBackendPrimary']).toBe('Primary backend');
    expect(UI_TEXT.zh['settings.generationBackendFallback']).toBe('Fallback backend');
    expect(UI_TEXT.zh['settings.generationBackendGenerationOnly']).toBe('Generation only');
    expect(UI_TEXT.zh['settings.generationBackendStatusDescription']).toContain('Quick check');
    expect(UI_TEXT.zh['settings.generationBackendStatusDescription']).not.toContain('cheap check');
    expect(UI_TEXT.zh['settings.generationBackendSmokePassed']).not.toContain('Smoke test');

    expect(UI_TEXT.en['settings.generationBackendStatus']).toBe('Generation backend status');
    expect(UI_TEXT.en['settings.generationBackendSmokeTest']).toBe('JSON smoke test');
    expect(UI_TEXT.en['settings.generationBackendPrimary']).toBe('Primary backend');
    expect(UI_TEXT.en['settings.generationBackendFallback']).toBe('Fallback backend');
    expect(UI_TEXT.en['settings.generationBackendGenerationOnly']).toBe('Generation only');
  });
});

describe('decision signal settings guard', () => {
  it('does not add placeholder DecisionSignal setting translations without a real schema field', () => {
    const placeholderKeys = [
      'DECISION_SIGNAL_ENABLED',
      'DECISION_SIGNALS_ENABLED',
      'DECISION_SIGNAL_WRITE_ENABLED',
      'DECISION_SIGNAL_EXTRACT_ENABLED',
    ];

    placeholderKeys.forEach((key) => {
      expect(getFieldTitleZh(key, key)).toBe(key);
      expect(getFieldDescriptionZh(key, 'schema fallback description')).toBe('schema fallback description');
    });
  });
});
