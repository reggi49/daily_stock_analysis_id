# -*- coding: utf-8 -*-
"""
===================================
AStock selection intelligent analysis system - AIAnalysis layer
===================================

Responsibilities：
1. encapsulation LLM Call logic（pass LiteLLM Unified call Gemini/Anthropic/OpenAI wait）
2. Generate analysis reports combining technical aspects and news aspects
3. parse LLM Response is structured AnalysisResult
"""

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple, Callable

import litellm
from json_repair import repair_json
from litellm import Router

from src.agent.llm_adapter import (
    get_thinking_extra_body,
    resolve_fallback_litellm_wire_models,
    register_fallback_model_pricing,
)
from src.agent.provider_trace import resolved_model_provider_identity
from src.agent.skills.defaults import CORE_TRADING_SKILL_POLICY_ZH
from src.config import (
    Config,
    extra_litellm_params,
    get_api_keys_for_model,
    get_config,
    get_configured_llm_models,
    resolve_news_window_days,
)
from src.llm.hermes import (
    HERMES_CHANNEL_NAME,
    build_hermes_redaction_values,
    canonicalize_hermes_model_ref,
    filter_non_hermes_deployments,
    hermes_blocked_route_candidates,
    is_masked_secret_placeholder,
    open_hermes_no_proxy_client,
    route_deployment_origins,
    route_has_hermes,
    sanitize_hermes_error_text,
)
from src.llm.generation_params import apply_litellm_generation_params
from src.llm.errors import call_litellm_with_param_recovery
from src.llm.backend_registry import (
    LOCAL_CLI_GENERATION_BACKEND_IDS,
    LITELLM_BACKEND_ID,
    resolve_generation_backend_id,
    resolve_generation_fallback_backend_id,
)
from src.llm.backend_factory import create_generation_backend
from src.llm.generation_backend import (
    GenerationBackend,
    GenerationError,
    GenerationErrorCode,
)
from src.llm.usage import (
    attach_legacy_message_stability_audit,
    attach_message_hmacs,
    extract_usage_payload,
    normalize_litellm_usage,
    should_persist_usage_telemetry,
)
from src.llm.local_cli_backend import redact_diagnostic_text
from src.llm.provider_cache import (
    apply_prompt_cache_hints,
    build_provider_cache_route_context,
    filter_prompt_cache_telemetry,
)
from src.llm.response_content import strip_leading_think_wrapper
from src.storage import persist_llm_usage
from src.data.stock_mapping import STOCK_NAME_MAP
from src.report_language import (
    get_signal_level,
    get_no_data_text,
    get_placeholder_text,
    get_unknown_text,
    get_chip_unavailable_text,
    infer_decision_type_from_advice,
    is_chip_placeholder_value,
    localize_chip_health,
    localize_confidence_level,
    localize_operation_advice,
    localize_trend_prediction,
    normalize_report_language,
)
from src.schemas.decision_action import build_action_fields
from src.schemas.decision_scale import (
    CANONICAL_DECISION_SCALE_PROMPT_ZH,
    score_band_metadata,
)
from src.schemas.report_schema import AnalysisReportSchema
from src.market_context import detect_market, get_market_role, get_market_guidelines
from src.services.daily_market_context import format_daily_market_context_prompt_section
from src.market_phase_prompt import format_market_phase_prompt_section
from src.market_structure_prompt import format_market_structure_prompt_section

logger = logging.getLogger(__name__)


def _localized_text(language: Any, *, en: str, zh: str, ko: str) -> str:
    """Pick a deterministic fallback string for the report language (zh/en/ko)."""
    normalized = normalize_report_language(language)
    if normalized == "en":
        return en
    if normalized == "ko":
        return ko
    return zh


def _normalize_risk_warning_values(value: Any) -> List[str]:
    """Normalize arbitrary risk_warning values into a flat list of text alerts."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, (list, tuple, set)):
        normalized: List[str] = []
        for item in value:
            normalized.extend(_normalize_risk_warning_values(item))
        return normalized
    if isinstance(value, dict):
        if not value:
            return []
        try:
            dumped = json.dumps(value, ensure_ascii=False)
            text = dumped.strip()
        except (TypeError, ValueError):
            text = str(value).strip()
        return [text] if text else []
    text = str(value).strip()
    return [text] if text else []


def _today_has_realtime_overlay(today: Any) -> bool:
    if not isinstance(today, dict):
        return False
    data_source = today.get("data_source") or today.get("dataSource")
    if isinstance(data_source, str) and data_source.startswith("realtime:"):
        return True
    if today.get("is_partial_bar") is True or today.get("isPartialBar") is True:
        return True
    if today.get("is_estimated") is True or today.get("isEstimated") is True:
        return True
    return bool(today.get("estimated_fields") or today.get("estimatedFields"))


def _today_looks_complete_daily_bar(
    context: Dict[str, Any],
    phase_context: Dict[str, Any],
) -> bool:
    today = context.get("today")
    if (
        not isinstance(today, dict)
        or today.get("close") in (None, "")
        or _today_has_realtime_overlay(today)
    ):
        return False

    effective_date = phase_context.get("effective_daily_bar_date")
    today_date = today.get("date") or today.get("trade_date") or context.get("date")
    if effective_date and today_date and str(today_date) != str(effective_date):
        return False
    return True


def _phase_aware_quote_labels(context: Dict[str, Any]) -> Tuple[str, str]:
    """Choose Chinese quote-table labels that do not conflict with phase context."""
    phase_context = context.get("market_phase_context")
    if not isinstance(phase_context, dict):
        return "Today's Quote", "closing price"

    phase = str(phase_context.get("phase") or "").strip()
    if phase in {"premarket", "non_trading"}:
        today = context.get("today")
        if _today_looks_complete_daily_bar(context, phase_context):
            return "Quotes from the last full trading day", "Last full trading day's closing price"
        if _today_has_realtime_overlay(today):
            return "Latest Quotes", "Real-time price estimate"
        if isinstance(today, dict) and today.get("close") not in (None, ""):
            return "Latest Quotes", "latest price"
        return "Today's Quote", "closing price"

    if (
        phase in {"intraday", "lunch_break", "closing_auction"}
        and phase_context.get("is_partial_bar") is True
    ):
        return "Latest Quotes", "Intraday estimated price"

    return "Today's Quote", "closing price"


def _should_hide_regular_session_ohlc(context: Dict[str, Any]) -> bool:
    phase_context = context.get("market_phase_context")
    if not isinstance(phase_context, dict):
        return False

    phase = str(phase_context.get("phase") or "").strip()
    return phase in {"premarket", "non_trading"} and not _today_looks_complete_daily_bar(
        context,
        phase_context,
    )


def _legacy_market_group(stock_code: Any) -> str:
    code = str(stock_code or "").strip()
    if not code or code.lower() == "unknown":
        return "unknown"
    market = detect_market(code)
    return market if market in {"cn", "hk", "us"} else "unknown"


def _legacy_audit_marker_specs(
    context: Dict[str, Any],
    *,
    code: str,
    stock_name: str,
    report_language: str,
    news_context: Optional[str],
    analysis_context_pack_summary: Optional[str],
) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []

    def add(marker_name: str, value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        markers.append(
            {
                "marker_name": marker_name,
                "message_role": "user",
                "text": text,
            }
        )

    add("stock_code", code)
    add("stock_name", stock_name)
    add("analysis_date", context.get("date"))
    add("market_phase", "## Market Phase Context" if report_language in ("en", "ko") else "## 市场阶段上下文")
    add("daily_market_context", "## Daily Market Context" if report_language in ("en", "ko") else "## 大盘环境摘要")
    add("market_structure_context", "## Market Structure Context" if report_language in ("en", "ko") else "## 市场结构上下文")
    add("analysis_context_pack", analysis_context_pack_summary)
    add("quote", "## 📈 Technical data")
    add("news_context", "## 📰 public opinion intelligence" if news_context else None)
    return markers


class _LiteLLMStreamError(RuntimeError):
    """Internal error wrapper that records whether any text was streamed."""

    def __init__(self, message: str, *, partial_received: bool = False):
        super().__init__(message)
        self.partial_received = partial_received


class _AllModelsFailedError(Exception):
    """Raised when every model in the fallback chain fails.

    This includes both LLM call errors and JSON parse errors (when a
    ``response_validator`` is provided to :meth:`GeminiAnalyzer._call_litellm`).

    The ``last_response_text`` attribute holds the raw text from the last model
    that *did* return a response (but whose JSON could not be validated), so
    callers can still attempt a best-effort text fallback.

    ``last_model`` and ``last_usage`` record the model name and token usage
    from the last attempt so callers can persist usage even on fallback.
    """

    def __init__(
        self,
        message: str,
        *,
        last_response_text: Optional[str] = None,
        last_model: Optional[str] = None,
        last_usage: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.last_response_text = last_response_text
        self.last_model = last_model
        self.last_usage = last_usage or {}


from src.utils.data_processing import normalize_report_signal_attribution


def check_content_integrity(
    result: "AnalysisResult",
    *,
    require_phase_decision: bool = False,
) -> Tuple[bool, List[str]]:
    """
    Check mandatory fields for report content integrity.
    Returns (pass, missing_fields). Module-level for use by pipeline (agent weak mode).

    Note:
    - Required fields: missing → pass=False, added to missing_fields
    - Optional fields (e.g., signal_attribution): missing → pass=True and are not added to missing_fields
    """
    missing: List[str] = []

    def _is_blank_text(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        return True

    def _is_invalid_risk_alerts(value: Any) -> bool:
        return not isinstance(value, list)

    def _is_invalid_stop_loss(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, tuple, dict)):
            return True
        if isinstance(value, str):
            return not value.strip()
        return False

    if result.sentiment_score is None:
        missing.append("sentiment_score")
    advice = result.operation_advice
    if not advice or not isinstance(advice, str) or _is_blank_text(advice):
        missing.append("operation_advice")
    summary = result.analysis_summary
    if not summary or not isinstance(summary, str) or _is_blank_text(summary):
        missing.append("analysis_summary")
    dash = result.dashboard if isinstance(result.dashboard, dict) else {}
    core = dash.get("core_conclusion")
    core = core if isinstance(core, dict) else {}
    if _is_blank_text(core.get("one_sentence")):
        missing.append("dashboard.core_conclusion.one_sentence")
    intel = dash.get("intelligence")
    intel = intel if isinstance(intel, dict) else None
    if intel is None or _is_invalid_risk_alerts(intel.get("risk_alerts")):
        missing.append("dashboard.intelligence.risk_alerts")
    if result.decision_type in ("buy", "hold"):
        battle = dash.get("battle_plan")
        battle = battle if isinstance(battle, dict) else {}
        sp = battle.get("sniper_points")
        sp = sp if isinstance(sp, dict) else {}
        stop_loss = sp.get("stop_loss")
        if _is_invalid_stop_loss(stop_loss):
            missing.append("dashboard.battle_plan.sniper_points.stop_loss")
    if require_phase_decision:
        phase_decision = dash.get("phase_decision")
        phase_decision = phase_decision if isinstance(phase_decision, dict) else {}
        if not isinstance(phase_decision.get("phase_context"), dict):
            missing.append("dashboard.phase_decision.phase_context")
        if _is_blank_text(phase_decision.get("action_window")):
            missing.append("dashboard.phase_decision.action_window")
        if _is_blank_text(phase_decision.get("immediate_action")):
            missing.append("dashboard.phase_decision.immediate_action")
        if not isinstance(phase_decision.get("watch_conditions"), list):
            missing.append("dashboard.phase_decision.watch_conditions")
        if _is_blank_text(phase_decision.get("next_check_time")):
            missing.append("dashboard.phase_decision.next_check_time")
        if _is_blank_text(phase_decision.get("confidence_reason")):
            missing.append("dashboard.phase_decision.confidence_reason")
        if not isinstance(phase_decision.get("data_limitations"), list):
            missing.append("dashboard.phase_decision.data_limitations")
    return len(missing) == 0, missing


def apply_placeholder_fill(result: "AnalysisResult", missing_fields: List[str]) -> None:
    """Fill missing mandatory fields with placeholders (in-place). Module-level for pipeline."""

    def _is_blank_text(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        return True

    def _is_invalid_risk_alerts(value: Any) -> bool:
        return not isinstance(value, list)

    def _is_invalid_stop_loss(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, (list, tuple, dict)):
            return True
        if isinstance(value, str):
            return not value.strip()
        return False

    report_language = normalize_report_language(getattr(result, "report_language", "zh"))
    placeholder = get_placeholder_text(report_language)
    phase_decision_placeholders = {
        "dashboard.phase_decision.action_window": _localized_text(
            report_language,
            en="Model did not provide a phase action window",
            zh="The model does not provide a staged action window",
            ko="모델이 단계별 행동 구간을 제공하지 않았습니다",
        ),
        "dashboard.phase_decision.immediate_action": _localized_text(
            report_language,
            en="Model did not provide a phase-aware immediate action",
            zh="The model does not provide staged instant actions",
            ko="모델이 단계 인식 즉시 동작을 제공하지 않았습니다",
        ),
        "dashboard.phase_decision.next_check_time": _localized_text(
            report_language,
            en="Model did not provide a next check point",
            zh="The model does not provide the next checkpoint",
            ko="모델이 다음 점검 시점을 제공하지 않았습니다",
        ),
        "dashboard.phase_decision.confidence_reason": _localized_text(
            report_language,
            en="Model did not provide a phase confidence rationale",
            zh="Model does not provide staged confidence reasons",
            ko="모델이 단계별 신뢰도 근거를 제공하지 않았습니다",
        ),
    }
    for field in missing_fields:
        if field == "sentiment_score":
            result.sentiment_score = 50
        elif field == "operation_advice":
            if _is_blank_text(result.operation_advice):
                result.operation_advice = placeholder
        elif field == "analysis_summary":
            if _is_blank_text(result.analysis_summary):
                result.analysis_summary = placeholder
        elif field == "dashboard.core_conclusion.one_sentence":
            if not result.dashboard:
                result.dashboard = {}
            core = result.dashboard.get("core_conclusion")
            if not isinstance(core, dict):
                core = {}
                result.dashboard["core_conclusion"] = core
            fallback_sentence = (
                result.analysis_summary
                or result.operation_advice
                or placeholder
            )
            if _is_blank_text(core.get("one_sentence")):
                result.dashboard["core_conclusion"]["one_sentence"] = fallback_sentence
        elif field == "dashboard.intelligence.risk_alerts":
            if not result.dashboard:
                result.dashboard = {}
            intelligence = result.dashboard.get("intelligence")
            if not isinstance(intelligence, dict):
                intelligence = {}
                result.dashboard["intelligence"] = intelligence
            if _is_invalid_risk_alerts(intelligence.get("risk_alerts")):
                risk_warning_values = _normalize_risk_warning_values(result.risk_warning)
                intelligence["risk_alerts"] = risk_warning_values
        elif field == "dashboard.battle_plan.sniper_points.stop_loss":
            if not result.dashboard:
                result.dashboard = {}
            battle_plan = result.dashboard.get("battle_plan")
            if not isinstance(battle_plan, dict):
                battle_plan = {}
                result.dashboard["battle_plan"] = battle_plan
            sniper_points = battle_plan.get("sniper_points")
            if not isinstance(sniper_points, dict):
                sniper_points = {}
                battle_plan["sniper_points"] = sniper_points
            if _is_invalid_stop_loss(sniper_points.get("stop_loss")):
                sniper_points["stop_loss"] = placeholder
        elif field.startswith("dashboard.phase_decision."):
            if not result.dashboard:
                result.dashboard = {}
            phase_decision = result.dashboard.get("phase_decision")
            if not isinstance(phase_decision, dict):
                phase_decision = {}
                result.dashboard["phase_decision"] = phase_decision
            if field == "dashboard.phase_decision.phase_context":
                if not isinstance(phase_decision.get("phase_context"), dict):
                    phase_decision["phase_context"] = {}
            elif field == "dashboard.phase_decision.watch_conditions":
                if not isinstance(phase_decision.get("watch_conditions"), list):
                    phase_decision["watch_conditions"] = []
            elif field == "dashboard.phase_decision.data_limitations":
                if not isinstance(phase_decision.get("data_limitations"), list):
                    phase_decision["data_limitations"] = []
            elif field in phase_decision_placeholders:
                if _is_blank_text(phase_decision.get(field.rsplit(".", 1)[-1])):
                    phase_decision[field.rsplit(".", 1)[-1]] = phase_decision_placeholders[field]


# ---------- chip_structure fallback (Issue #589) ----------

_CHIP_KEYS: tuple = ("profit_ratio", "avg_cost", "concentration", "chip_health")


def _is_value_placeholder(v: Any) -> bool:
    """True if value is empty or placeholder (N/A, missing data, etc.)."""
    return is_chip_placeholder_value(v)


_RISK_WARNING_PLACEHOLDER_TEXTS = {
    "",
    "n/a",
    "na",
    "none",
    "null",
    "unknown",
    "tbd",
    "None",
    "To be added",
    "missing data",
    "unknown",
    "none",
}

_STRUCTURAL_RISK_PHRASE_HINTS = (
    "major negative",
    "significant risk",
    "key risks",
    "Reduce holdings",
    "Reduce holdings at high level",
    "delisting",
    "Delisting risk",
    "trading suspension",
    "Important inquiries",
    "punishment",
    "Limited sale",
    "Violation",
    "Risk of non-compliance",
    "litigation",
    "Inquiry",
    "supervision",
    "finance",
    "audit",
    "thunder",
    "Thunderstorm",
    "breach of contract",
    "default risk",
    "liquidity crisis",
    "debt",
    "liquidation",
    "Bankruptcy",
    "major face change",
    "major risk",
    "material adverse",
    "suspension",
    "delisting",
    "regulatory",
    "downgrade",
    "liquidity",
    "default",
)

_CAPITAL_FLOW_UNAVAILABLE_STATUS = {
    "not_supported",
    "not supported",
    "unsupported",
    "unavailable",
    "not_available",
    "not available",
    "none",
    "na",
    "n/a",
    "null",
    "missing",
}


def _is_meaningful_text(value: Any) -> bool:
    text = str(value).strip() if value is not None else ""
    if not text:
        return False
    lowered = text.strip().lower()
    return lowered not in _RISK_WARNING_PLACEHOLDER_TEXTS


def _safe_float(v: Any, default: float = 0.0) -> float:
    """Safely convert to float; return default on failure. Private helper for chip fill."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        try:
            return default if math.isnan(float(v)) else float(v)
        except (ValueError, TypeError):
            return default
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return default


def _coerce_chip_metric(v: Any) -> Optional[float]:
    """Convert chip metrics while preserving the distinction between missing and zero."""
    if v is None:
        return None
    try:
        numeric = float(v)
    except (TypeError, ValueError):
        try:
            numeric = float(str(v).strip())
        except (TypeError, ValueError):
            return None
    return None if math.isnan(numeric) else numeric


_BULLISH_TREND_HINTS: Tuple[str, ...] = (
    "multi-head arrangement",
    "Continue to rise",
    "Trending up",
    "uptrend",
    "Divergent upward",
    "bullish",
    "uptrend",
)
_WEAK_BULLISH_TREND_HINTS: Tuple[str, ...] = ("Weak bulls",)
_BEARISH_TREND_HINTS: Tuple[str, ...] = (
    "Short arrangement",
    "Continued decline",
    "trending down",
    "downtrend",
    "diverge downward",
    "bearish",
    "downtrend",
)
_WEAK_BEARISH_TREND_HINTS: Tuple[str, ...] = ("Weak short",)
_NEGATION_TOKENS: Tuple[str, ...] = (
    "no",
    "Not",
    "not yet",
    "No",
    "not yet",
    "not yet",
    "not yet",
    "none",
    "Does not belong",
    "No",
    "not ",
    "no ",
)
_NEGATION_BREAK_CHARS: Tuple[str, ...] = (",", ".", ";", ":", "!", "?", "，", "。", "；", "：", "！", "？", "\n")
_NEGATION_LOOKBACK_CHARS = 16
_NEGATION_MAX_GAP_CHARS = 8
_NEGATION_SCOPE_BREAK_TOKENS: Tuple[str, ...] = (
    "Rather",
    "but",
    "but",
    "instead",
    "On the contrary",
    "convert to",
    "Convert to",
    "Change to",
    "Change to",
    " but ",
    " instead ",
    " rather ",
)
_SINGLE_CHAR_NEGATION_GAP_PREFIXES: Tuple[str, ...] = (
    "form",
    "Appear",
    "Enter",
    "convert to",
    "Convert to",
    "constitute",
    "present",
    "show",
    "belong",
    "yes",
    "have",
    "able",
    "See",
    "stand",
    "break",
    "break",
)


def _normalize_prompt_reason_items(items: Any) -> List[str]:
    """Normalize prompt reason/risk items into a clean string list."""
    if not isinstance(items, list):
        return []
    normalized: List[str] = []
    for item in items:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _contains_trend_hint(text: str, hints: Tuple[str, ...]) -> bool:
    """Return True when text contains a non-negated strong trend hint."""
    lowered = text.strip().lower()

    def _has_negation_scope_break(gap: str) -> bool:
        normalized_gap = gap.lower()
        for token in _NEGATION_SCOPE_BREAK_TOKENS:
            token_index = normalized_gap.find(token)
            if token_index > 0:
                return True
        return False

    def _is_valid_negation_gap(token: str, gap: str) -> bool:
        if not gap:
            return True
        if token not in {"Not yet", "None", "Not"}:
            return True
        return any(gap.startswith(prefix) for prefix in _SINGLE_CHAR_NEGATION_GAP_PREFIXES)

    def _is_negated_match(index: int) -> bool:
        prefix = lowered[max(0, index - _NEGATION_LOOKBACK_CHARS):index]
        for token in _NEGATION_TOKENS:
            token_index = prefix.rfind(token)
            if token_index < 0:
                continue
            gap = prefix[token_index + len(token):]
            if any(char in gap for char in _NEGATION_BREAK_CHARS):
                continue
            stripped_gap = gap.strip()
            if len(stripped_gap) > _NEGATION_MAX_GAP_CHARS:
                continue
            if _has_negation_scope_break(stripped_gap):
                continue
            if not _is_valid_negation_gap(token, stripped_gap):
                continue
            return True
        return False

    for hint in hints:
        keyword = hint.lower()
        start = 0
        while True:
            index = lowered.find(keyword, start)
            if index < 0:
                break
            if not _is_negated_match(index):
                return True
            start = index + len(keyword)
    return False


def _infer_trend_direction(trend: Dict[str, Any]) -> str:
    """Infer the final trend direction from trend_status and ma_alignment."""
    combined = " ".join(
        str(trend.get(key, "")).strip()
        for key in ("trend_status", "ma_alignment")
        if str(trend.get(key, "")).strip()
    )
    if not combined:
        return "neutral"
    lowered = combined.lower()
    normalized = lowered.replace(" ", "")
    has_bullish = (
        _contains_trend_hint(combined, _BULLISH_TREND_HINTS + _WEAK_BULLISH_TREND_HINTS)
        or "ma5>ma10>ma20" in normalized
        or (
            "ma5>ma10" in normalized
            and any(pattern in normalized for pattern in ("ma10≤ma20", "ma10<=ma20"))
        )
    )
    has_bearish = (
        _contains_trend_hint(combined, _BEARISH_TREND_HINTS + _WEAK_BEARISH_TREND_HINTS)
        or "ma5<ma10<ma20" in normalized
        or (
            "ma5<ma10" in normalized
            and any(pattern in normalized for pattern in ("ma10≥ma20", "ma10>=ma20"))
        )
    )
    if has_bullish and not has_bearish:
        return "bullish"
    if has_bearish and not has_bullish:
        return "bearish"
    return "neutral"


def _filter_conflicting_trend_items(items: List[str], conflict_hints: Tuple[str, ...]) -> List[str]:
    """Drop reasons that directly conflict with the final trend direction."""
    return [item for item in items if not _contains_trend_hint(item, conflict_hints)]


def _sanitize_trend_analysis_for_prompt(
    trend: Any,
    *,
    volume_change_ratio: Any = None,
) -> Dict[str, Any]:
    """Clean prompt-only trend hints on a derived copy without touching runtime/provider config."""
    trend_dict = dict(trend) if isinstance(trend, dict) else {}
    signal_reasons = _normalize_prompt_reason_items(trend_dict.get("signal_reasons"))
    risk_factors = _normalize_prompt_reason_items(trend_dict.get("risk_factors"))
    prompt_notes: List[str] = []
    trend_direction = _infer_trend_direction(trend_dict)

    if trend_direction == "bearish":
        filtered_signal_reasons = _filter_conflicting_trend_items(
            signal_reasons,
            _BULLISH_TREND_HINTS + _WEAK_BULLISH_TREND_HINTS,
        )
        if len(filtered_signal_reasons) != len(signal_reasons):
            prompt_notes.append("The current technical structure is bearish，Structural reasons for bullish positions that directly conflict with the primary judgment of short sellers have been eliminated.。")
        signal_reasons = filtered_signal_reasons
        prompt_notes.append(
            "If news、Performance or policy catalysts are too high，can only be expressed as“Event first、Technology to be confirmed”or“Fundamentals are bullish，But the technical aspects have not yet been confirmed”，It is strictly prohibited to write a deterministic buying point。"
        )
    elif trend_direction == "bullish":
        filtered_signal_reasons = _filter_conflicting_trend_items(
            signal_reasons,
            _BEARISH_TREND_HINTS + _WEAK_BEARISH_TREND_HINTS,
        )
        if len(filtered_signal_reasons) != len(signal_reasons):
            prompt_notes.append("The current technical structure is too much，Reasons for short positions that directly conflict with the long-term main judgment have been eliminated.。")
        signal_reasons = filtered_signal_reasons
        filtered_risk_factors = _filter_conflicting_trend_items(
            risk_factors,
            _BEARISH_TREND_HINTS + _WEAK_BEARISH_TREND_HINTS,
        )
        if len(filtered_risk_factors) != len(risk_factors):
            prompt_notes.append("The current technical structure is too much，Short structural risk statements that directly conflict with the long primary judgment have been eliminated.。")
        risk_factors = filtered_risk_factors

    parsed_volume_change = _safe_float(volume_change_ratio, default=math.nan)
    if math.isfinite(parsed_volume_change) and parsed_volume_change > 10:
        prompt_notes.append(
            f"The trading volume has changed approximately from yesterday {parsed_volume_change:.2f} times，Energy signals must be de-emphasized for interpretation；Energy signals must be de-emphasized for interpretation，Cannot be mechanically regarded as strong confirmation。"
        )

    trend_dict["signal_reasons"] = signal_reasons
    trend_dict["risk_factors"] = risk_factors
    trend_dict["prompt_consistency_notes"] = prompt_notes
    trend_dict["prompt_trend_direction"] = trend_direction
    return trend_dict


def _derive_chip_health(profit_ratio: float, concentration_90: float, language: str = "zh") -> str:
    """Derive chip_health from profit_ratio and concentration_90."""
    if profit_ratio >= 0.9:
        return localize_chip_health("Be alert", language)  # Extremely high profit margin
    if concentration_90 >= 0.25:
        return localize_chip_health("Be alert", language)  # Chips scattered
    if concentration_90 < 0.15 and 0.3 <= profit_ratio < 0.9:
        return localize_chip_health("health", language)  # Concentrated and moderate profit ratio
    return localize_chip_health("Average", language)


def _build_chip_structure_from_data(chip_data: Any, language: str = "zh") -> Dict[str, Any]:
    """Build chip_structure dict from ChipDistribution or dict."""
    if hasattr(chip_data, "profit_ratio"):
        pr = _safe_float(chip_data.profit_ratio)
        ac = chip_data.avg_cost
        c90 = _safe_float(chip_data.concentration_90)
    else:
        d = chip_data if isinstance(chip_data, dict) else {}
        pr = _safe_float(d.get("profit_ratio"))
        ac = d.get("avg_cost")
        c90 = _safe_float(d.get("concentration_90"))
    chip_health = _derive_chip_health(pr, c90, language=language)
    return {
        "profit_ratio": f"{pr:.1%}",
        "avg_cost": ac if (ac is not None and _safe_float(ac) != 0.0) else "N/A",
        "concentration": f"{c90:.2%}",
        "chip_health": chip_health,
    }


def _has_meaningful_chip_data(chip_data: Any) -> bool:
    """Return True when chip data has the core metrics required for reporting."""
    if not chip_data:
        return False
    if hasattr(chip_data, "avg_cost"):
        avg_cost = _coerce_chip_metric(getattr(chip_data, "avg_cost", None))
        concentration_90 = _coerce_chip_metric(getattr(chip_data, "concentration_90", None))
        concentration_70 = _coerce_chip_metric(getattr(chip_data, "concentration_70", None))
    else:
        d = chip_data if isinstance(chip_data, dict) else {}
        avg_cost = _coerce_chip_metric(d.get("avg_cost"))
        concentration_90_value = d.get("concentration_90")
        if concentration_90_value is None:
            concentration_90_value = d.get("concentration")
        concentration_90 = _coerce_chip_metric(concentration_90_value)
        concentration_70 = _coerce_chip_metric(d.get("concentration_70"))
    return (
        avg_cost is not None
        and avg_cost > 0
        and (
            (concentration_90 is not None and concentration_90 >= 0)
            or (concentration_70 is not None and concentration_70 >= 0)
        )
    )


def _mark_chip_structure_unavailable(result: "AnalysisResult", language: str) -> None:
    if not result or not isinstance(result.dashboard, dict):
        return
    data_perspective = result.dashboard.get("data_perspective")
    if not isinstance(data_perspective, dict):
        return
    data_perspective["chip_structure"] = {}
    data_perspective["chip_unavailable_reason"] = get_chip_unavailable_text(language)


def normalize_chip_structure_availability(result: "AnalysisResult", chip_data: Any) -> None:
    """Fill valid chip metrics or collapse placeholder-only chip fields to one fallback line."""
    if not result:
        return
    language = getattr(result, "report_language", "zh")
    if _has_meaningful_chip_data(chip_data):
        fill_chip_structure_if_needed(result, chip_data)
        return
    _mark_chip_structure_unavailable(result, language)


def fill_chip_structure_if_needed(result: "AnalysisResult", chip_data: Any) -> None:
    """When chip_data exists, fill chip_structure placeholder fields from chip_data (in-place)."""
    if not result or not _has_meaningful_chip_data(chip_data):
        return
    try:
        if not result.dashboard:
            result.dashboard = {}
        dash = result.dashboard
        # Use `or {}` rather than setdefault so that an explicit `null` from LLM is also replaced
        dp = dash.get("data_perspective") or {}
        dash["data_perspective"] = dp
        cs = dp.get("chip_structure") or {}
        filled = _build_chip_structure_from_data(
            chip_data,
            language=getattr(result, "report_language", "zh"),
        )
        # Start from a copy of cs to preserve any extra keys the LLM may have added
        merged = dict(cs)
        for k in _CHIP_KEYS:
            if _is_value_placeholder(merged.get(k)):
                merged[k] = filled[k]
        if merged != cs:
            dp["chip_structure"] = merged
            logger.info("[chip_structure] Filled placeholder chip fields from data source (Issue #589)")
    except Exception as e:
        logger.warning("[chip_structure] Fill failed, skipping: %s", e)


_PRICE_POS_KEYS = ("ma5", "ma10", "ma20", "bias_ma5", "bias_status", "current_price", "support_level", "resistance_level")


def fill_price_position_if_needed(
    result: "AnalysisResult",
    trend_result: Any = None,
    realtime_quote: Any = None,
) -> None:
    """Fill missing price_position fields from trend_result / realtime data (in-place)."""
    if not result:
        return
    try:
        if not result.dashboard:
            result.dashboard = {}
        dash = result.dashboard
        dp = dash.get("data_perspective") or {}
        dash["data_perspective"] = dp
        pp = dp.get("price_position") or {}

        computed: Dict[str, Any] = {}
        if trend_result:
            tr = trend_result if isinstance(trend_result, dict) else (
                trend_result.__dict__ if hasattr(trend_result, "__dict__") else {}
            )
            computed["ma5"] = tr.get("ma5")
            computed["ma10"] = tr.get("ma10")
            computed["ma20"] = tr.get("ma20")
            computed["bias_ma5"] = tr.get("bias_ma5")
            computed["current_price"] = tr.get("current_price")
            support_levels = tr.get("support_levels") or []
            resistance_levels = tr.get("resistance_levels") or []
            if support_levels:
                computed["support_level"] = support_levels[0]
            if resistance_levels:
                computed["resistance_level"] = resistance_levels[0]
        if realtime_quote:
            rq = realtime_quote if isinstance(realtime_quote, dict) else (
                realtime_quote.to_dict() if hasattr(realtime_quote, "to_dict") else {}
            )
            if _is_value_placeholder(computed.get("current_price")):
                computed["current_price"] = rq.get("price")

        filled = False
        for k in _PRICE_POS_KEYS:
            if _is_value_placeholder(pp.get(k)) and not _is_value_placeholder(computed.get(k)):
                pp[k] = computed[k]
                filled = True
        if filled:
            dp["price_position"] = pp
            logger.info("[price_position] Filled placeholder fields from computed data")
    except Exception as e:
        logger.warning("[price_position] Fill failed, skipping: %s", e)


def stabilize_decision_with_structure(
    result: "AnalysisResult",
    trend_result: Any = None,
    fundamental_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Calibrate aggressive buy/sell advice with price levels and capital flow.

    The LLM can overreact to one-day price movement.  This guard keeps the
    public `decision_type` enum stable while allowing richer neutral wording
    such as shock/Washing dishes and observing when support, resistance, and fund flow do not confirm
    an immediate buy/sell action.
    """
    if not result:
        return

    try:
        language = normalize_report_language(getattr(result, "report_language", "zh"))
        dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}
        data_perspective = dashboard.get("data_perspective") if isinstance(dashboard, dict) else {}
        if not isinstance(data_perspective, dict):
            data_perspective = {}
        price_position = data_perspective.get("price_position")
        if not isinstance(price_position, dict):
            price_position = {}

        trend_dict = _as_dict_for_decision_guard(trend_result)
        current_price = _first_numeric_value(
            getattr(result, "current_price", None),
            price_position.get("current_price"),
            trend_dict.get("current_price"),
        )
        support = _first_numeric_value(
            price_position.get("support_level"),
            _first_list_value(trend_dict.get("support_levels")),
        )
        resistance = _first_numeric_value(
            price_position.get("resistance_level"),
            _first_list_value(trend_dict.get("resistance_levels")),
        )
        decision_type = infer_decision_type_from_advice(
            getattr(result, "decision_type", ""),
            default=getattr(result, "decision_type", "hold") or "hold",
        )
        decision_type = decision_type if decision_type in {"buy", "hold", "sell"} else "hold"
        advice_decision_type = infer_decision_type_from_advice(
            getattr(result, "operation_advice", ""),
            default="",
        )

        flow_bias, flow_reason = _capital_flow_bias_with_status(fundamental_context)
        if flow_bias == "unavailable":
            if isinstance(fundamental_context, dict) and "capital_flow" in fundamental_context:
                if decision_type == "buy" or advice_decision_type == "buy":
                    _downgrade_buy_without_capital_flow(
                        result,
                        language,
                        current_price=current_price,
                        support=support,
                        resistance=resistance,
                        flow_status=flow_reason,
                    )
                else:
                    _set_decision_stability_unavailable(
                        result,
                        language,
                        current_price=current_price,
                        support=support,
                        resistance=resistance,
                        flow_status=flow_reason,
                    )
            return

        if current_price is None:
            return

        broke_support = support is not None and current_price < support * 0.985
        near_support = support is not None and not broke_support and current_price <= support * 1.03
        breakout = resistance is not None and current_price > resistance * 1.01
        near_resistance = (
            resistance is not None
            and not breakout
            and current_price >= resistance * 0.97
        )
        mid_range = (
            support is not None
            and resistance is not None
            and support * 1.03 < current_price < resistance * 0.97
        )

        has_significant_risk = _has_structural_risk_alert(result)

        if decision_type == "buy":
            if near_resistance and flow_bias != "inflow":
                _downgrade_to_structural_hold(
                    result,
                    language,
                    advice_key="range",
                    reason_key="buy_near_resistance",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
            elif flow_bias == "outflow" and not breakout:
                _downgrade_to_structural_hold(
                    result,
                    language,
                    advice_key="range",
                    reason_key="buy_with_outflow",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
            elif mid_range and flow_bias == "neutral":
                _downgrade_to_structural_hold(
                    result,
                    language,
                    advice_key="range",
                    reason_key="hold_mid_range",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
        elif decision_type == "sell":
            if near_support and (flow_bias != "outflow") and not has_significant_risk:
                _downgrade_to_structural_hold(
                    result,
                    language,
                    advice_key="shakeout",
                    reason_key="sell_near_support",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
            elif flow_bias == "inflow" and not broke_support and not has_significant_risk:
                _downgrade_to_structural_hold(
                    result,
                    language,
                    advice_key="hold",
                    reason_key="sell_with_inflow",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
        elif decision_type == "hold":
            change_pct = _first_numeric_value(getattr(result, "change_pct", None))
            if change_pct is not None and change_pct < 0 and near_support and flow_bias != "outflow":
                _set_structural_hold_wording(
                    result,
                    language,
                    advice_key="shakeout",
                    reason_key="hold_shakeout",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
            elif mid_range and flow_bias == "neutral":
                _set_structural_hold_wording(
                    result,
                    language,
                    advice_key="range",
                    reason_key="hold_mid_range",
                    current_price=current_price,
                    support=support,
                    resistance=resistance,
                    flow_bias=flow_bias,
                )
        _sync_stability_dashboard_fields(result)
    except Exception as exc:
        logger.warning("[decision_stability] skipped: %s", exc)


def _has_structural_risk_alert(result: "AnalysisResult") -> bool:
    dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}

    risk_text = getattr(result, "risk_warning", "")
    if _is_significant_structural_risk(risk_text):
        return True

    intelligence = dashboard.get("intelligence") if isinstance(dashboard, dict) else None
    if isinstance(intelligence, dict):
        risk_alerts = intelligence.get("risk_alerts")
        if isinstance(risk_alerts, str):
            if _is_significant_structural_risk(risk_alerts):
                return True
        elif isinstance(risk_alerts, (list, tuple, set)):
            if any(_is_significant_structural_risk(item) for item in risk_alerts):
                return True

    core_conclusion = dashboard.get("core_conclusion") if isinstance(dashboard, dict) else None
    if isinstance(core_conclusion, dict):
        signal_type = str(core_conclusion.get("signal_type", "")).strip()
        if _is_significant_structural_risk(signal_type):
            return True
    return False


def _is_significant_structural_risk(value: Any) -> bool:
    text = str(value or "").strip()
    if not _is_meaningful_text(text):
        return False

    normalized = text.lower()
    if any(keyword in normalized for keyword in _STRUCTURAL_RISK_PHRASE_HINTS):
        return True

    return "significant" in text and "risk" in normalized


def _sync_stability_dashboard_fields(result: "AnalysisResult") -> None:
    dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}
    result.dashboard = dashboard
    dashboard["sentiment_score"] = getattr(result, "sentiment_score", None)
    dashboard["operation_advice"] = getattr(result, "operation_advice", None)
    dashboard["decision_type"] = getattr(result, "decision_type", None)


def _as_dict_for_decision_guard(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            return converted if isinstance(converted, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return {}


def _first_list_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return value


def _coerce_numeric_value(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return float(value)
        return None
    text = str(value).replace(",", "").replace("，", "").strip()
    if not text or text.upper() in {"N/A", "NA", "NONE", "NULL"}:
        return None
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _first_numeric_value(*values: Any) -> Optional[float]:
    for value in values:
        if isinstance(value, (list, tuple)):
            nested = _first_numeric_value(*value)
            if nested is not None:
                return nested
            continue
        numeric = _coerce_numeric_value(value)
        if numeric is not None:
            return numeric
    return None


def _capital_flow_bias(fundamental_context: Optional[Dict[str, Any]]) -> str:
    return _capital_flow_bias_with_status(fundamental_context)[0]


def _capital_flow_bias_with_status(
    fundamental_context: Optional[Dict[str, Any]],
) -> tuple[str, str]:
    if not isinstance(fundamental_context, dict):
        return "unavailable", "invalid_context"
    block = fundamental_context.get("capital_flow")
    if not isinstance(block, dict):
        return "unavailable", "capital_flow_block_missing"
    status = str(block.get("status") or "").strip().lower()
    normalized_status = status.replace("-", " ").replace("_", " ").strip()
    if normalized_status in _CAPITAL_FLOW_UNAVAILABLE_STATUS or "not supported" in normalized_status:
        return "unavailable", status or "not_supported"
    data = block.get("data") if isinstance(block.get("data"), dict) else block
    stock_flow = data.get("stock_flow") if isinstance(data, dict) else None
    if not isinstance(stock_flow, dict) or not stock_flow:
        return "unavailable", "empty_stock_flow"

    def _flow_direction(value: Optional[float]) -> Optional[str]:
        if value is None or value == 0:
            return None
        return "inflow" if value > 0 else "outflow"

    numeric_values = [
        _coerce_numeric_value(stock_flow.get("main_net_inflow")),
        _coerce_numeric_value(stock_flow.get("inflow_5d")),
        _coerce_numeric_value(stock_flow.get("inflow_10d")),
    ]
    if all(value is None for value in numeric_values):
        return "unavailable", "missing_or_na_flow_fields"

    ordered_signals = [
        _flow_direction(value) for value in numeric_values
    ]
    directions = {signal for signal in ordered_signals if signal is not None}
    if not directions or len(directions) > 1:
        return "neutral", "conflict_or_missing"
    for signal in ordered_signals:
        if signal is not None:
            return signal, "ok"
    return "neutral", "neutral"


def _capital_flow_status_for_stability(reason: str, language: str) -> str:
    normalized = str(reason or "").strip().lower()
    if "not_supported" in normalized or "unsupported" in normalized or "not available" in normalized:
        return "Market capital flow service is not currently supported" if language == "zh" else "Capital flow source unsupported"
    if "empty_stock_flow" in normalized or "missing" in normalized:
        return "Fund flow data is missing" if language == "zh" else "capital flow data unavailable"
    return "Fund flow data is not available" if language == "zh" else "capital flow unavailable"


def _set_decision_stability_unavailable(
    result: "AnalysisResult",
    language: str,
    *,
    current_price: Optional[float],
    support: Optional[float],
    resistance: Optional[float],
    flow_status: str,
) -> None:
    dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}
    result.dashboard = dashboard
    dashboard["decision_stability"] = {
        "applied": False,
        "reason": "Funding flow unavailable，Fund flow calibration not used" if language == "zh" else "Capital flow unavailable; stability calibration not applied",
        "capital_flow_status": _capital_flow_status_for_stability(flow_status, language),
        "current_price": current_price,
        "support": support,
        "resistance": resistance,
        "capital_flow_bias": "unavailable",
    }
    _sync_stability_dashboard_fields(result)


def _record_decision_score_calibration(
    result: "AnalysisResult",
    *,
    raw_score: int,
    adjusted_score: int,
    final_action: str,
    guardrail_reason: Optional[str],
) -> None:
    dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}
    result.dashboard = dashboard
    calibration = score_band_metadata(raw_score)
    calibration.update(
        {
            "raw_score": raw_score,
            "adjusted_score": adjusted_score,
            "final_action": final_action,
        }
    )
    if guardrail_reason:
        calibration["guardrail_reason"] = guardrail_reason
    dashboard["decision_score_calibration"] = calibration


def _bound_hold_watch_sentiment_score(
    result: "AnalysisResult",
    *,
    reason: Optional[str] = None,
    final_action: str = "watch",
) -> None:
    try:
        score = int(getattr(result, "sentiment_score", 50))
    except (TypeError, ValueError):
        score = 50
    adjusted_score = min(59, max(45, score))
    result.sentiment_score = adjusted_score
    _record_decision_score_calibration(
        result,
        raw_score=score,
        adjusted_score=adjusted_score,
        final_action=final_action,
        guardrail_reason=reason,
    )


def _apply_hold_watch_dashboard(
    result: "AnalysisResult",
    language: str,
    *,
    advice: str,
    reason: str,
    current_price: Optional[float],
    support: Optional[float],
    resistance: Optional[float],
    flow_bias: str,
    no_position: str,
    has_position: str,
    capital_flow_status: Optional[str] = None,
) -> None:
    result.operation_advice = advice

    dashboard = result.dashboard if isinstance(result.dashboard, dict) else {}
    result.dashboard = dashboard
    core = dashboard.get("core_conclusion")
    if not isinstance(core, dict):
        core = {}
        dashboard["core_conclusion"] = core
    core["signal_type"] = "🟡wait and see" if language == "zh" else "🟡 Hold / Watch"
    core["one_sentence"] = f"{advice}：{reason}" if language == "zh" else f"{advice}: {reason}"

    position_advice = core.get("position_advice")
    if not isinstance(position_advice, dict):
        position_advice = {}
        core["position_advice"] = position_advice
    position_advice["no_position"] = no_position
    position_advice["has_position"] = has_position

    stability = {
        "applied": True,
        "reason": reason,
        "current_price": current_price,
        "support": support,
        "resistance": resistance,
        "capital_flow_bias": flow_bias,
    }
    if capital_flow_status is not None:
        stability["capital_flow_status"] = capital_flow_status
    score_calibration = dashboard.get("decision_score_calibration")
    if isinstance(score_calibration, dict):
        stability["raw_score"] = score_calibration.get("raw_score")
        stability["adjusted_score"] = score_calibration.get("adjusted_score")
        stability["final_action"] = score_calibration.get("final_action")
    dashboard["decision_stability"] = stability

    if reason and reason not in str(result.risk_warning or ""):
        sep = "；" if language == "zh" else "; "
        result.risk_warning = f"{result.risk_warning}{sep}{reason}" if result.risk_warning else reason
    result.buy_reason = reason or result.buy_reason


def _downgrade_buy_without_capital_flow(
    result: "AnalysisResult",
    language: str,
    *,
    current_price: Optional[float],
    support: Optional[float],
    resistance: Optional[float],
    flow_status: str,
) -> None:
    status_text = _capital_flow_status_for_stability(flow_status, language)
    if language == "zh":
        advice = "hold observation"
        reason = f"{status_text}，Buying conclusion lacks financial confirmation，Treat by observation first。"
        no_position = "Don’t buy after short positions first，Waiting for funds flow to resume、Act only after support is confirmed or has an effective breakthrough。"
        has_position = "Positions take key support as the risk control line，Wait and see in shock。"
        confidence = "Low"
    else:
        advice = "Hold and watch"
        reason = f"{status_text}; the buy call lacks capital-flow confirmation, so treat it as watch-only."
        no_position = "Do not chase; wait for capital-flow recovery, support confirmation, or a valid breakout."
        has_position = "Use key support as the risk line and keep position size controlled until capital flow recovers."
        confidence = "Low"

    result.decision_type = "hold"
    result.confidence_level = confidence
    _bound_hold_watch_sentiment_score(result, reason=reason, final_action="hold")
    _apply_hold_watch_dashboard(
        result,
        language,
        advice=advice,
        reason=reason,
        current_price=current_price,
        support=support,
        resistance=resistance,
        flow_bias="unavailable",
        no_position=no_position,
        has_position=has_position,
        capital_flow_status=status_text,
    )
    _sync_stability_dashboard_fields(result)
    logger.info("[decision_stability] Downgraded buy because capital flow is unavailable: %s", flow_status)


def _downgrade_to_structural_hold(
    result: "AnalysisResult",
    language: str,
    *,
    advice_key: str,
    reason_key: str,
    current_price: float,
    support: Optional[float],
    resistance: Optional[float],
    flow_bias: str,
) -> None:
    result.decision_type = "hold"
    _set_structural_hold_wording(
        result,
        language,
        advice_key=advice_key,
        reason_key=reason_key,
        current_price=current_price,
        support=support,
        resistance=resistance,
        flow_bias=flow_bias,
        calibrate_score=True,
    )


def _set_structural_hold_wording(
    result: "AnalysisResult",
    language: str,
    *,
    advice_key: str,
    reason_key: str,
    current_price: float,
    support: Optional[float],
    resistance: Optional[float],
    flow_bias: str,
    calibrate_score: bool = False,
) -> None:
    advice_map = {
        "zh": {
            "range": "Wait and see in shock",
            "shakeout": "Washing dishes and observing",
            "hold": "hold observation",
        },
        "en": {
            "range": "Range-bound watch",
            "shakeout": "Shakeout watch",
            "hold": "Hold and watch",
        },
        "ko": {
            "range": "박스권 관망",
            "shakeout": "흔들기 관찰",
            "hold": "보유 관찰",
        },
    }
    advice_default = {"zh": "hold observation", "en": "Hold and watch", "ko": "보유 관찰"}.get(language, "Hold and watch")
    advice = advice_map.get(language, advice_map["en"]).get(advice_key, advice_default)
    reason_templates = {
        "zh": {
            "buy_near_resistance": "The price is close to the pressure level and the inflow of main funds has not been confirmed，It is not advisable to pursue purchases just because of a short-term rebound.。",
            "buy_with_outflow": "Main capital outflow conflicts with buying conclusion，The buying point needs to wait for confirmation of support or return of funds.。",
            "sell_near_support": "Prices are close to support and no continued outflows are seen，It is not advisable to sell directly just because of a single day's decline.。",
            "sell_with_inflow": "The main capital inflow conflicts with the selling conclusion，First proceed with observation and track support failure。",
            "hold_shakeout": "Prices fall back near support but no outflows are confirmed，More suitable for washing dishes and observing。",
            "hold_mid_range": "Price is between support and pressure and funding flows are unclear，It is more feasible to maintain the shock and wait and see。",
        },
        "en": {
            "buy_near_resistance": "Price is near resistance without confirmed main-force inflow, so chasing the rebound is not actionable.",
            "buy_with_outflow": "Main-force outflow conflicts with a buy call; wait for support confirmation or capital inflow.",
            "sell_near_support": "Price is near support without sustained outflow, so a one-day drop is not enough to sell.",
            "sell_with_inflow": "Main-force inflow conflicts with a sell call; hold and watch for support failure.",
            "hold_shakeout": "Price pulled back near support without confirmed outflow, which is better treated as a shakeout watch.",
            "hold_mid_range": "Price is between support and resistance with neutral fund flow, so range-bound watch is more actionable.",
        },
        "ko": {
            "buy_near_resistance": "가격이 저항선에 근접했고 주력 자금 유입이 확인되지 않아 단기 반등만 보고 추격 매수하기 어렵습니다.",
            "buy_with_outflow": "주력 자금 유출이 매수 결론과 상충하므로 지지 확인이나 자금 재유입을 기다려야 합니다.",
            "sell_near_support": "가격이 지지선에 근접했고 지속적 유출이 없어 하루 하락만으로 매도하기 어렵습니다.",
            "sell_with_inflow": "주력 자금 유입이 매도 결론과 상충하므로 우선 보유 관찰하며 지지 이탈을 추적합니다.",
            "hold_shakeout": "가격이 지지선 부근까지 눌렸지만 유출이 확인되지 않아 흔들기 관찰로 처리하는 것이 적절합니다.",
            "hold_mid_range": "가격이 지지선과 저항선 사이이고 자금 흐름이 불명확해 박스권 관망이 더 실행 가능합니다.",
        },
    }
    reason = reason_templates.get(language, reason_templates["en"]).get(reason_key, "")
    if calibrate_score:
        final_action = "watch" if advice_key in {"range", "shakeout"} else "hold"
        _bound_hold_watch_sentiment_score(result, reason=reason, final_action=final_action)
    result.operation_advice = advice
    if advice_key == "range":
        if language == "zh" and "shock" not in str(result.trend_prediction):
            result.trend_prediction = "shock"
        elif language == "en":
            result.trend_prediction = "Sideways"
        elif language == "ko":
            result.trend_prediction = "횡보"

    if language == "zh":
        no_position = "Don’t chase the rise or kill the fall for short positions first，Waiting for support confirmation、Take action after heavy volume breakthrough or capital reflow。"
        has_position = "Positions take key support as the risk control line，Before falling below, the main focus is observation and position control in batches.。"
    elif language == "ko":
        no_position = "현금 보유 시 추격·투매를 삼가고 지지 확인·대량 돌파·자금 재유입 후 행동하세요."
        has_position = "보유 시 핵심 지지선을 리스크 관리선으로 삼고, 이탈 전까지 관찰과 분할 관리 위주로 대응하세요."
    else:
        no_position = "Do not chase or panic; wait for support confirmation, breakout, or renewed inflow."
        has_position = "Use key support as the risk line and manage position size unless support fails."
    _apply_hold_watch_dashboard(
        result,
        language,
        advice=advice,
        reason=reason,
        current_price=current_price,
        support=support,
        resistance=resistance,
        flow_bias=flow_bias,
        no_position=no_position,
        has_position=has_position,
    )
    logger.info("[decision_stability] Applied structural hold calibration: %s", reason_key)


def get_stock_name_multi_source(
    stock_code: str,
    context: Optional[Dict] = None,
    data_manager = None
) -> str:
    """
    Obtain stock Chinese names from multiple sources

    Get strategy（by priority）：
    1. from incoming context Get in（realtime data）
    2. from static mapping table STOCK_NAME_MAP get
    3. from DataFetcherManager get（Each data source）
    4. core indicators（stock+code）

    Args:
        stock_code: Stock code
        context: Analyze context（Optional）
        data_manager: DataFetcherManager Stock Chinese name（Optional）

    Returns:
        Stock Chinese name
    """
    # 1. Get from data source（Get from data source）
    if context:
        # Get from data source stock_name Get from data source
        if context.get('stock_name'):
            name = context['stock_name']
            if name and not name.startswith('stocks'):
                return name

        # Get from data source realtime Get from data source
        if 'realtime' in context and context['realtime'].get('name'):
            return context['realtime']['name']

    # 2. Get from data source
    if stock_code in STOCK_NAME_MAP:
        return STOCK_NAME_MAP[stock_code]

    # 3. Get from data source
    if data_manager is None:
        try:
            from data_provider.base import DataFetcherManager
            data_manager = DataFetcherManager()
        except Exception as e:
            logger.debug(f"Unable to initialize DataFetcherManager: {e}")

    if data_manager:
        try:
            name = data_manager.get_stock_name(stock_code)
            if name:
                # Update cache
                STOCK_NAME_MAP[stock_code] = name
                return name
        except Exception as e:
            logger.debug(f"Failed to get stock name from data source: {e}")

    # 4. core indicators
    return f'stocks{stock_code}'


@dataclass
class AnalysisResult:
    """
    AI Analysis result data class - Decision dashboard version

    encapsulation Gemini Returned analysis results，Contains decision-making dashboards and detailed analysis
    """
    code: str
    name: str

    # ========== core indicators ==========
    sentiment_score: int  # Overall rating 0-100 (>70Strongly bullish, >60long, 40-60shock, <40bearish)
    trend_prediction: str  # Trend forecast：Strongly bullish/long/shock/bearish/Strongly bearish
    operation_advice: str  # Operation suggestions：Buy/Add to position/hold/Reduce positions/sell/wait and see
    decision_type: str = "hold"  # Decision type：buy/hold/sell（for statistics）
    confidence_level: str = "middle"  # Confidence：high/middle/Low
    report_language: str = "zh"  # Report output language：zh/en
    action: Optional[str] = None  # Recommended action taxonomy：buy/add/hold/reduce/sell/watch/avoid/alert
    action_label: Optional[str] = None  # Localized suggested action tags

    # ========== Decision dashboard (New) ==========
    dashboard: Optional[Dict[str, Any]] = None  # Complete decision dashboard data

    # ========== Technical analysis ==========
    trend_analysis: str = ""  # Trend pattern analysis（support level、pressure level、trend lines etc.）
    short_term_outlook: str = ""  # short term outlook（1-3day）
    medium_term_outlook: str = ""  # medium term outlook（1-2week）

    # ========== Technical analysis ==========
    technical_analysis: str = ""  # Comprehensive analysis of technical indicators
    ma_analysis: str = ""  # Moving average analysis（long/Short arrangement，golden fork/Sicha et al.）
    volume_analysis: str = ""  # Quantitative energy analysis（Increase the volume/shrink，Main trends, etc.）
    pattern_analysis: str = ""  # KLine shape analysis

    # ========== fundamental analysis ==========
    fundamental_analysis: str = ""  # Comprehensive analysis of fundamentals
    sector_position: str = ""  # Sector status and industry trends
    company_highlights: str = ""  # risk/Risk point

    # ========== Emotional side/News analysis ==========
    news_summary: str = ""  # Recent important news/Announcement summary
    market_sentiment: str = ""  # Market Sentiment Analysis
    hot_topics: str = ""  # Related hot topics

    # ========== comprehensive analysis ==========
    analysis_summary: str = ""  # Comprehensive analysis summary
    key_points: str = ""  # Core highlights（3-5points）
    risk_warning: str = ""  # Risk warning
    buy_reason: str = ""  # Buy/Reasons to sell

    # ========== metadata ==========
    market_snapshot: Optional[Dict[str, Any]] = None  # Snapshot of the day's market trends（for display）
    raw_response: Optional[str] = None  # original response（for debugging）
    search_performed: bool = False  # Whether a web search was performed
    data_sources: str = ""  # Data source description
    success: bool = True
    error_message: Optional[str] = None

    # ========== price data（model markup）==========
    current_price: Optional[float] = None  # Stock price at time of analysis
    change_pct: Optional[float] = None     # Increase and decrease at the time of analysis(%)

    # ========== model markup（Issue #528）==========
    model_used: Optional[str] = None  # used for analysis LLM Model（full name，like gemini/gemini-2.0-flash）

    # ========== Historical comparison（Report Engine P0）==========
    query_id: Optional[str] = None  # This analysis query_id，Exclude this record for historical comparison

    # ========== fundamental context（Runtime only，Used for notification assembly；not persisted to to_dict）==========
    fundamental_context: Optional[Dict[str, Any]] = None
    market_structure_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'code': self.code,
            'name': self.name,
            'sentiment_score': self.sentiment_score,
            'trend_prediction': self.trend_prediction,
            'operation_advice': self.operation_advice,
            'decision_type': self.decision_type,
            'confidence_level': self.confidence_level,
            'report_language': self.report_language,
            'action': self.action,
            'action_label': self.action_label,
            'dashboard': self.dashboard,  # Decision dashboard data
            'trend_analysis': self.trend_analysis,
            'short_term_outlook': self.short_term_outlook,
            'medium_term_outlook': self.medium_term_outlook,
            'technical_analysis': self.technical_analysis,
            'ma_analysis': self.ma_analysis,
            'volume_analysis': self.volume_analysis,
            'pattern_analysis': self.pattern_analysis,
            'fundamental_analysis': self.fundamental_analysis,
            'sector_position': self.sector_position,
            'company_highlights': self.company_highlights,
            'news_summary': self.news_summary,
            'market_sentiment': self.market_sentiment,
            'hot_topics': self.hot_topics,
            'analysis_summary': self.analysis_summary,
            'key_points': self.key_points,
            'risk_warning': self.risk_warning,
            'buy_reason': self.buy_reason,
            'market_snapshot': self.market_snapshot,
            'search_performed': self.search_performed,
            'success': self.success,
            'error_message': self.error_message,
            'current_price': self.current_price,
            'change_pct': self.change_pct,
            'model_used': self.model_used,
            'market_structure_context': self.market_structure_context,
        }

    def get_core_conclusion(self) -> str:
        """Get core conclusions（a word）"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            return self.dashboard['core_conclusion'].get('one_sentence', self.analysis_summary)
        return self.analysis_summary

    def get_position_advice(self, has_position: bool = False) -> str:
        """Get position advice"""
        if self.dashboard and 'core_conclusion' in self.dashboard:
            pos_advice = self.dashboard['core_conclusion'].get('position_advice', {})
            if has_position:
                return pos_advice.get('has_position', self.operation_advice)
            return pos_advice.get('no_position', self.operation_advice)
        return self.operation_advice

    def get_sniper_points(self) -> Dict[str, str]:
        """Get checklist"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('sniper_points', {})
        return {}

    def get_checklist(self) -> List[str]:
        """Get checklist"""
        if self.dashboard and 'battle_plan' in self.dashboard:
            return self.dashboard['battle_plan'].get('action_checklist', [])
        return []

    def get_risk_alerts(self) -> List[str]:
        """Get risk alerts"""
        if self.dashboard and 'intelligence' in self.dashboard:
            return self.dashboard['intelligence'].get('risk_alerts', [])
        return []

    def get_emoji(self) -> str:
        """Return the response according to the operation suggestions emoji"""
        _, emoji, _ = get_signal_level(
            self.operation_advice,
            self.sentiment_score,
            self.report_language,
        )
        return emoji

    def get_confidence_stars(self) -> str:
        """Analyzer"""
        star_map = {
            "high": "⭐⭐⭐",
            "high": "⭐⭐⭐",
            "middle": "⭐⭐",
            "medium": "⭐⭐",
            "Low": "⭐",
            "low": "⭐",
        }
        return star_map.get(str(self.confidence_level or "").strip().lower(), "⭐⭐")


def populate_decision_action_fields(
    result: AnalysisResult,
    *,
    explicit_action: Any = None,
    report_type: Any = None,
    use_existing_action: bool = True,
    align_with_score: bool = True,
) -> AnalysisResult:
    """Populate optional decision action fields without changing legacy advice."""

    action_source = explicit_action
    if action_source is None and use_existing_action:
        action_source = getattr(result, "action", None)

    fields = build_action_fields(
        operation_advice=getattr(result, "operation_advice", None),
        explicit_action=action_source,
        report_type=report_type,
        report_language=getattr(result, "report_language", "zh"),
        sentiment_score=getattr(result, "sentiment_score", None),
        guardrail_reason=getattr(result, "guardrail_reason", None),
        align_with_score=align_with_score,
    )
    result.action = fields["action"]
    result.action_label = fields["action_label"]
    return result


class GeminiAnalyzer:
    """
    Gemini AI Analyzer

    Responsibilities：
    1. call Google Gemini API Perform stock analysis
    2. Generate analysis reports based on pre-searched news and technical data
    3. parse AI returned JSON format result

    Usage：
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze(context, news_context)
    """

    # ========================================
    # System prompt word - Decision dashboard v2.0
    # ========================================
    # From simple signals to decision-making dashboards：From simple signals to decision-making dashboards
    # core module：Core conclusion + Pivot data + public opinion intelligence + battle plan
    # ========================================

    LEGACY_DEFAULT_SYSTEM_PROMPT = """You are a trend trader{market_placeholder}investment analyst，Responsible for generating professional【Decision dashboard】analysis report。

{guidelines_placeholder}

""" + CORE_TRADING_SKILL_POLICY_ZH + """

""" + CANONICAL_DECISION_SCALE_PROMPT_ZH + """

## Output format：Decision dashboard JSON

Please strictly follow the following JSON format output，this is a complete【Decision dashboard】：

```json
{
    "stock_name": "Stock Chinese name",
    "sentiment_score": 0-100integer,
    "trend_prediction": "Strongly bullish/long/shock/bearish/Strongly bearish",
    "operation_advice": "Buy/Add to position/hold/Reduce positions/sell/wait and see",
    "decision_type": "buy/hold/sell",
    "action": "buy/add/hold/reduce/sell/watch/avoid/alert",
    "guardrail_reason": "When the score interval is the same as the final action Fill in the downgrade if inconsistent/Reason for upgrade，Otherwise leave blank",
    "confidence_level": "high/middle/Low",

    "dashboard": {
        "core_conclusion": {
            "one_sentence": "One sentence core conclusion（30Within words，Tell users directly what to do）",
            "signal_type": "🟢buy signal/🟡wait and see/🔴sell signal/⚠️Risk warning",
            "time_sensitivity": "Act now/within today/No rush/No rush",
            "position_advice": {
                "no_position": "Advice for short sellers：Specific operating instructions",
                "has_position": "Suggestions for position holders：Specific operating instructions"
            }
        },

        "data_perspective": {
            "trend_status": {
                "ma_alignment": "Moving average arrangement status description",
                "is_bullish": true/false,
                "trend_score": 0-100
            },
            "price_position": {
                "current_price": Current price value,
                "ma5": MA5numerical value,
                "ma10": MA10numerical value,
                "ma20": MA20numerical value,
                "bias_ma5": Deviation rate percentage value,
                "bias_status": "Safety/alert/Danger",
                "support_level": support price,
                "resistance_level": Pressure level price
            },
            "volume_analysis": {
                "volume_ratio": quantity ratio value,
                "volume_status": "Increase the volume/shrink/equal amount",
                "turnover_rate": Turnover percentage,
                "volume_meaning": "Interpretation of the meaning of quantity and energy（like：A shrinkage pullback indicates a reduction in selling pressure）"
            },
            "chip_structure": {
                "profit_ratio": Profit ratio,
                "avg_cost": average cost,
                "concentration": Chip concentration,
                "chip_health": "healthy/generally/alert"
            }
        },

        "intelligence": {
            "latest_news": "【latest news】Summary of recent important news",
            "risk_alerts": ["Risk point1：Detailed description", "Risk point2：Detailed description"],
            "positive_catalysts": ["good1：Detailed description", "good2：Detailed description"],
            "earnings_outlook": "Performance Expectation Analysis（Based on annual report forecast、Performance reports, etc.）",
            "sentiment_summary": "One sentence summary of public opinion and sentiment"
        },

        "battle_plan": {
            "sniper_points": {
                "ideal_buy": "Ideal buying point：XXYuan（existMA5Second best buying point）",
                "secondary_buy": "Second best buying point：XXYuan（existMA10Second best buying point）",
                "stop_loss": "Stop loss level：XXYuan（fell belowMA20orX%）",
                "take_profit": "Target position：XXYuan（Front high/integer gate）"
            },
            "position_strategy": {
                "suggested_position": "Recommended positions：Xbecome",
                "entry_plan": "Description of batch building strategy",
                "risk_control": "Risk control strategy description"
            },
            "action_checklist": [
                "✅/⚠️/❌ Check items1：multi-head arrangement",
                "✅/⚠️/❌ Check items2：Deviation rate is reasonable（Strong trends can be relaxed）",
                "✅/⚠️/❌ Check items3：Coordination of quantity and energy",
                "✅/⚠️/❌ Check items4：No major negative",
                "✅/⚠️/❌ Check items5：chips health",
                "✅/⚠️/❌ Check items6：PEReasonable valuation"
            ]
        },

        "phase_decision": {
            "phase_context": {"phase": "premarket/intraday/lunch_break/closing_auction/postmarket/non_trading/unknown"},
            "action_window": "Pre-market planning/intraday tracking/midday confirmation/Risk control before closing/After-hours review/Observation on non-trading days",
            "immediate_action": "Act now/Waiting for confirmation/observe/Stop loss and take profit warning/Chasing high is prohibited/No intraday action",
            "watch_conditions": ["Observation conditions1", "Observation conditions2"],
            "next_check_time": "Next checkpoint or market local time",
            "confidence_reason": "Confidence reason，Describe stage and data quality constraints",
            "data_limitations": ["Contribution of technical indicators1", "Contribution of technical indicators2"]
        },

        "signal_attribution": {
            "technical_indicators": Contribution of technical indicators(0-100),
            "news_sentiment": News and public opinion contribution(0-100),
            "fundamentals": Fundamental contribution(0-100),
            "market_conditions": Market environment contribution(0-100),
            "strongest_bullish_signal": "The name of the strongest bullish signal",
            "strongest_bearish_signal": "The name of the strongest bearish signal"
        }
    },

    "analysis_summary": "100Comprehensive word analysis summary",
    "key_points": "3-5core points，comma separated",
    "risk_warning": "Risk warning",
    "buy_reason": "Reason for operation，Quote trading concept",

    "trend_analysis": "Trend pattern analysis",
    "short_term_outlook": "short term1-3day outlook",
    "medium_term_outlook": "medium term1-2Weekly Outlook",
    "technical_analysis": "Comprehensive technical analysis",
    "ma_analysis": "Moving average system analysis",
    "volume_analysis": "Quantitative energy analysis",
    "pattern_analysis": "KLine shape analysis",
    "fundamental_analysis": "fundamental analysis",
    "sector_position": "Sector industry analysis",
    "company_highlights": "risk/risk",
    "news_summary": "news summary",
    "market_sentiment": "market sentiment",
    "hot_topics": "Related hot spots",

    "search_performed": true/false,
    "data_sources": "Data source description"
}
```

## Scoring criteria

### Strong buy（80-100point）：
- ✅ multi-head arrangement：MA5 > MA10 > MA20
- ✅ Low deviation rate：<2%，Best buy
- ✅ Volume correction or heavy volume breakthrough
- ✅ Chips focus on health
- ✅ The news is favorable and catalytic

### Buy（60-79point）：
- ✅ Long arrangement or weak long position
- ✅ deviation rate <5%
- ✅ Energy is normal
- ⚪ Allow a minor condition not to be met

### wait and see（40-59point）：
- ⚠️ deviation rate >5%（Chasing high risk）
- ⚠️ The moving average wrapping trend is unclear
- ⚠️ risky events

### Reduce positions（20-39point）：
- ⚠️ Trend weakens or falls below key moving averages
- ⚠️ funds/Quantity energy weakens，Risks are significantly higher than returns
- ⚠️ Focus on reducing positions and protecting profits

### sell（0-19point）：
- ❌ Short alignment or trend worsens significantly
- ❌ Breaking below key support/Stop loss level
- ❌ Heavy volume decline or major negative

## Decision Dashboard Core Principles

1. **Core conclusions first**：In one sentence, it is clear whether to buy or to sell.
2. **Suggestions on holding positions**：Short position holders and position holders give different advice
3. **Precise sniper point**：A specific price must be given，don't say vague words
4. **Checklist visualization**：use ✅⚠️❌ Clear display of each inspection result
5. **risk priority**：Risk points in public opinion should be clearly highlighted

## Output language

- Do not place a stock just because it rises or falls in a single day or the score crosses the line.“Buy/sell”Operation suggestions must also refer to the price position。
- Operation suggestions must also refer to the price position（support/pressure level）、chips/chips、Main capital flows and risk events。
- The stock price is between support and pressure、When the flow of funds is unclear，Prioritize output“hold/shock/wait and see/Washing dishes and observing”Waiting for executable neutral suggestions；`decision_type` remain `hold`。
- Only when close to support confirmation or effective breakthrough pressure，and capital flow/When quantity and price match，to give a buy；Do not pursue buying when approaching pressure and funds are flowing out。
- Only if it falls below key support、to sell，to sell/Reduce positions。
- Must be output `dashboard.phase_decision` seven fields；intraday/Lunch break/The current action should be given when the market close is approaching.、Observation conditions and next checkpoint。
- Suggested output optional display fields `dashboard.signal_attribution` six fields；Explain the composition of the reasons for recommendation，Includes technical indicators、News and public opinion、Fundamentals、Contribution of market environment，And the strongest bullish/bearish signal。
- Before the market、It is not allowed to forge today’s intraday trend on non-trading days or during unknown stages.；quote/daily_bars/technical exist stale、fallback、missing、fetch_failed、partial or estimated hour，`confidence_level` Not allowed to be high。"""

    SYSTEM_PROMPT = """Ideal entry position{market_placeholder}investment analyst，Responsible for generating professional【Decision dashboard】analysis report。

{guidelines_placeholder}

{default_skill_policy_section}
{skills_section}

""" + CANONICAL_DECISION_SCALE_PROMPT_ZH + """

## Output format：Decision dashboard JSON

Please strictly follow the following JSON format output，this is a complete【Decision dashboard】：

```json
{
    "stock_name": "Stock Chinese name",
    "sentiment_score": 0-100integer,
    "trend_prediction": "Strongly bullish/long/shock/bearish/Strongly bearish",
    "operation_advice": "Buy/Add to position/hold/Reduce positions/sell/wait and see",
    "decision_type": "buy/hold/sell",
    "action": "buy/add/hold/reduce/sell/watch/avoid/alert",
    "guardrail_reason": "When the score interval is the same as the final action Fill in the downgrade if inconsistent/Reason for upgrade，Otherwise leave blank",
    "confidence_level": "high/middle/Low",

    "dashboard": {
        "core_conclusion": {
            "one_sentence": "One sentence core conclusion（30Within words，Tell users directly what to do）",
            "signal_type": "🟢buy signal/🟡wait and see/🔴sell signal/⚠️Risk warning",
            "time_sensitivity": "Act now/within today/No rush/No rush",
            "position_advice": {
                "no_position": "Advice for short sellers：Specific operating instructions",
                "has_position": "Suggestions for position holders：Specific operating instructions"
            }
        },

        "data_perspective": {
            "trend_status": {
                "ma_alignment": "Moving average arrangement status description",
                "is_bullish": true/false,
                "trend_score": 0-100
            },
            "price_position": {
                "current_price": Current price value,
                "ma5": MA5numerical value,
                "ma10": MA10numerical value,
                "ma20": MA20numerical value,
                "bias_ma5": Deviation rate percentage value,
                "bias_status": "Safety/alert/Danger",
                "support_level": support price,
                "resistance_level": Pressure level price
            },
            "volume_analysis": {
                "volume_ratio": quantity ratio value,
                "volume_status": "Increase the volume/shrink/equal amount",
                "turnover_rate": Turnover percentage,
                "volume_meaning": "Interpretation of the meaning of quantity and energy（like：A shrinkage pullback indicates a reduction in selling pressure）"
            },
            "chip_structure": {
                "profit_ratio": Profit ratio,
                "avg_cost": average cost,
                "concentration": Chip concentration,
                "chip_health": "healthy/generally/alert"
            }
        },

        "intelligence": {
            "latest_news": "【latest news】Summary of recent important news",
            "risk_alerts": ["Risk point1：Detailed description", "Risk point2：Detailed description"],
            "positive_catalysts": ["good1：Detailed description", "good2：Detailed description"],
            "earnings_outlook": "Performance Expectation Analysis（Based on annual report forecast、Performance reports, etc.）",
            "sentiment_summary": "One sentence summary of public opinion and sentiment"
        },

        "battle_plan": {
            "sniper_points": {
                "ideal_buy": "Ideal entry position：XXYuan（Meet the main skill trigger conditions）",
                "secondary_buy": "Second best entry position：XXYuan（More conservative or execute after confirmation）",
                "stop_loss": "Stop loss level：XXYuan（press resistance levelX%risk）",
                "take_profit": "Target position：XXYuan（press resistance level/Risk reward ratio formulation）"
            },
            "position_strategy": {
                "suggested_position": "Recommended positions：Xbecome",
                "entry_plan": "Description of batch building strategy",
                "risk_control": "Risk control strategy description"
            },
            "action_checklist": [
                "✅/⚠️/❌ Check items1：Whether the current structure meets the conditions for skill activation",
                "✅/⚠️/❌ Check items2：Is the entry position and risk reward reasonable?",
                "✅/⚠️/❌ Check items3：Volume and price/fluctuation/Whether the chips support judgment",
                "✅/⚠️/❌ Check items4：No major negative",
                "✅/⚠️/❌ Check items5：Position and stop loss plans are clear",
                "✅/⚠️/❌ Check items6：Valuation/performance/Catalysis matches conclusion"
            ]
        },

        "phase_decision": {
            "phase_context": {"phase": "premarket/intraday/lunch_break/closing_auction/postmarket/non_trading/unknown"},
            "action_window": "Pre-market planning/intraday tracking/midday confirmation/Risk control before closing/After-hours review/Observation on non-trading days",
            "immediate_action": "Act now/Waiting for confirmation/observe/Stop loss and take profit warning/Chasing high is prohibited/No intraday action",
            "watch_conditions": ["Observation conditions1", "Observation conditions2"],
            "next_check_time": "Next checkpoint or market local time",
            "confidence_reason": "Confidence reason，Describe stage and data quality constraints",
            "data_limitations": ["Contribution of technical indicators1", "Contribution of technical indicators2"]
        },

        "signal_attribution": {
            "technical_indicators": Contribution of technical indicators(0-100),
            "news_sentiment": News and public opinion contribution(0-100),
            "fundamentals": Fundamental contribution(0-100),
            "market_conditions": Market environment contribution(0-100),
            "strongest_bullish_signal": "The name of the strongest bullish signal",
            "strongest_bearish_signal": "The name of the strongest bearish signal"
        }
    },

    "analysis_summary": "100Comprehensive word analysis summary",
    "key_points": "3-5core points，comma separated",
    "risk_warning": "Risk warning",
    "buy_reason": "Reason for operation，Multiple activation skills simultaneously support positive conclusions",

    "trend_analysis": "Trend pattern analysis",
    "short_term_outlook": "short term1-3day outlook",
    "medium_term_outlook": "medium term1-2Weekly Outlook",
    "technical_analysis": "Comprehensive technical analysis",
    "ma_analysis": "Moving average system analysis",
    "volume_analysis": "Quantitative energy analysis",
    "pattern_analysis": "KLine shape analysis",
    "fundamental_analysis": "fundamental analysis",
    "sector_position": "Sector industry analysis",
    "company_highlights": "risk/risk",
    "news_summary": "news summary",
    "market_sentiment": "market sentiment",
    "hot_topics": "Related hot spots",

    "search_performed": true/false,
    "data_sources": "Data source description"
}
```

## Scoring criteria

### Strong buy（80-100point）：
- ✅ Multiple activation skills simultaneously support positive conclusions
- ✅ Upside、Trigger conditions and risk rewards are clear
- ✅ Key risks have been checked，Position and stop loss plans are clear
- ✅ Important data and intelligence conclusions are consistent with each other

### Buy（60-79point）：
- ✅ The main signal is positive，But there are still a few items to be confirmed
- ✅ Allow for controllable risks or sub-optimal entry points
- ✅ Additional observation conditions need to be clearly stated in the report

### wait and see（40-59point）：
- ⚠️ Signal divergence is large，or lack of sufficient confirmation
- ⚠️ Risks and opportunities are roughly balanced
- ⚠️ Better to wait for trigger conditions or avoid uncertainty

### Reduce positions（20-39point）：
- ⚠️ Main conclusions weaken，Risks are significantly higher than returns
- ⚠️ Partial failure conditions triggered，Existing positions need to reduce exposure
- ⚠️ Better suited to protecting gains than attacking

### sell（0-19point）：
- ❌ Stop loss triggered/Failure conditions or major disadvantages
- ❌ Significant deterioration in trends or risks
- ❌ Existing positions should be exited first

## Decision Dashboard Core Principles

1. **Core conclusions first**：In one sentence, it is clear whether to buy or to sell.
2. **Suggestions on holding positions**：Short position holders and position holders give different advice
3. **Precise sniper point**：A specific price must be given，don't say vague words
4. **Checklist visualization**：use ✅⚠️❌ Clear display of each inspection result
5. **risk priority**：Risk points in public opinion should be clearly highlighted

## Output language

- Do not place a stock just because it rises or falls in a single day or the score crosses the line.“Buy/sell”Operation suggestions must also refer to the price position。
- Operation suggestions must also refer to the price position（support/pressure level）、chips/chips、Main capital flows and risk events。
- The stock price is between support and pressure、When the flow of funds is unclear，Prioritize output“hold/shock/wait and see/Washing dishes and observing”Waiting for executable neutral suggestions；`decision_type` remain `hold`。
- Only when close to support confirmation or effective breakthrough pressure，and capital flow/When quantity and price match，to give a buy；Do not pursue buying when approaching pressure and funds are flowing out。
- Only if it falls below key support、to sell，to sell/Reduce positions。
- Must be output `dashboard.phase_decision` seven fields；intraday/Lunch break/The current action should be given when the market close is approaching.、Observation conditions and next checkpoint。
- Suggested output optional display fields `dashboard.signal_attribution` six fields；Explain the composition of the reasons for recommendation，Includes technical indicators、News and public opinion、Fundamentals、Contribution of market environment，And the strongest bullish/bearish signal。
- Before the market、It is not allowed to forge today’s intraday trend on non-trading days or during unknown stages.；quote/daily_bars/technical exist stale、fallback、missing、fetch_failed、partial or estimated hour，`confidence_level` Not allowed to be high。"""

    TEXT_SYSTEM_PROMPT = """You are a professional stock analysis assistant。

- Answers must be based on user-provided data and context
- If there is insufficient information，Be clear about uncertainty
- Don't make up prices、Financial reports or news facts
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        config: Optional[Config] = None,
        skills: Optional[List[str]] = None,
        skill_instructions: Optional[str] = None,
        default_skill_policy: Optional[str] = None,
        use_legacy_default_prompt: Optional[bool] = None,
    ):
        """Initialize LLM Analyzer via LiteLLM.

        Args:
            api_key: Ignored (kept for backward compatibility). Keys are loaded from config.
        """
        self._config_override = config
        self._requested_skills = list(skills) if skills is not None else None
        self._skill_instructions_override = skill_instructions
        self._default_skill_policy_override = default_skill_policy
        self._use_legacy_default_prompt_override = use_legacy_default_prompt
        self._resolved_prompt_state: Optional[Dict[str, Any]] = None
        self._router = None
        self._legacy_router_model_list: List[Dict[str, Any]] = []
        self._litellm_available = False
        self._init_litellm()
        if not self._litellm_available:
            try:
                backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            except GenerationError:
                backend_id = ""
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.info(
                    "Analyzer generation backend: %s configured; LiteLLM API keys are not "
                    "required for stock analysis generation",
                    backend_id,
                )
            else:
                logger.warning("No LLM configured (LITELLM_MODEL / API keys), AI analysis will be unavailable")

    def _get_runtime_config(self) -> Config:
        """Return the runtime config, honoring injected overrides for tests/pipeline."""
        return getattr(self, "_config_override", None) or get_config()

    def _get_skill_prompt_sections(self) -> tuple[str, str, bool]:
        """Resolve skill instructions + default baseline + prompt mode."""
        skill_instructions = getattr(self, "_skill_instructions_override", None)
        default_skill_policy = getattr(self, "_default_skill_policy_override", None)
        use_legacy_default_prompt = getattr(self, "_use_legacy_default_prompt_override", None)

        if skill_instructions is not None and default_skill_policy is not None:
            return (
                skill_instructions,
                default_skill_policy,
                bool(use_legacy_default_prompt) if use_legacy_default_prompt is not None else False,
            )

        resolved_state = getattr(self, "_resolved_prompt_state", None)
        if resolved_state is None:
            from src.agent.factory import resolve_skill_prompt_state

            prompt_state = resolve_skill_prompt_state(
                self._get_runtime_config(),
                skills=getattr(self, "_requested_skills", None),
            )
            resolved_state = {
                "skill_instructions": prompt_state.skill_instructions,
                "default_skill_policy": prompt_state.default_skill_policy,
                "use_legacy_default_prompt": bool(getattr(prompt_state, "use_legacy_default_prompt", False)),
            }
            self._resolved_prompt_state = resolved_state

        return (
            skill_instructions if skill_instructions is not None else resolved_state.get("skill_instructions", ""),
            default_skill_policy if default_skill_policy is not None else resolved_state.get("default_skill_policy", ""),
            (
                use_legacy_default_prompt
                if use_legacy_default_prompt is not None
                else bool(resolved_state.get("use_legacy_default_prompt", False))
            ),
        )

    def _get_analysis_system_prompt(self, report_language: str, stock_code: str = "") -> str:
        """Build the analyzer system prompt with output-language guidance."""
        lang = normalize_report_language(report_language)
        market_role = get_market_role(stock_code, lang)
        market_guidelines = get_market_guidelines(stock_code, lang)
        skill_instructions, default_skill_policy, use_legacy_default_prompt = self._get_skill_prompt_sections()
        if use_legacy_default_prompt:
            base_prompt = self.LEGACY_DEFAULT_SYSTEM_PROMPT.replace(
                "{market_placeholder}", market_role
            ).replace(
                "{guidelines_placeholder}", market_guidelines
            )
        else:
            skills_section = ""
            if skill_instructions:
                skills_section = f"## wait before requesting\n\n{skill_instructions}\n"
            default_skill_policy_section = ""
            if default_skill_policy:
                default_skill_policy_section = f"{default_skill_policy}\n"
            base_prompt = (
                self.SYSTEM_PROMPT.replace("{market_placeholder}", market_role)
                .replace("{guidelines_placeholder}", market_guidelines)
                .replace("{default_skill_policy_section}", default_skill_policy_section)
                .replace("{skills_section}", skills_section)
            )
        if lang == "en":
            return base_prompt + """

## Output Language (highest priority)

- Keep all JSON keys unchanged.
- `decision_type` must remain `buy|hold|sell`.
- All human-readable JSON values must be written in English.
- Use the common English company name when you are confident; otherwise keep the original listed company name instead of inventing one.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, nested dashboard text, checklist items, and all narrative summaries.
"""
        if lang == "ko":
            return base_prompt + """

## Output Language (highest priority)

- Keep all JSON keys unchanged.
- `decision_type` must remain `buy|hold|sell`.
- All human-readable JSON values must be written in Korean (한국어).
- Use the common Korean or original listed company name when confident; do not invent one.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, nested dashboard text, checklist items, and all narrative summaries.
"""
        return base_prompt + """

## Output language（highest priority）

- all JSON Key names remain unchanged。
- `decision_type` must remain as `buy|hold|sell`。
- All user-facing human-readable text values ​​must be in Chinese。
"""

    def _has_channel_config(self, config: Config) -> bool:
        """Check if multi-channel config (channels / YAML / legacy model_list) is active."""
        return bool(config.llm_model_list) and not all(
            e.get('model_name', '').startswith('__legacy_') for e in config.llm_model_list
        )

    @staticmethod
    def _legacy_router_provider_alias(model: str) -> str:
        provider = model.split("/", 1)[0] if "/" in model else "openai"
        return f"__legacy_{provider}__"

    @staticmethod
    def _build_legacy_router_model_list_from_config(
        model: str,
        model_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build legacy-router candidates from configured legacy llm_model_list entries."""
        if not model:
            return []
        target_model = model
        target_legacy_alias = GeminiAnalyzer._legacy_router_provider_alias(model)
        legacy_entries: List[Dict[str, Any]] = []
        for entry in model_list or []:
            if not isinstance(entry, dict):
                continue
            model_name = str(entry.get("model_name") or "").strip()
            if model_name != target_legacy_alias:
                continue

            params = entry.get("litellm_params")
            if not isinstance(params, dict):
                continue

            api_key = str(params.get("api_key") or "").strip()
            if not api_key or len(api_key) < 8:
                continue

            deployed_params = dict(params)
            deployed_params["model"] = target_model
            deployed_params["api_key"] = api_key
            legacy_entries.append({
                "model_name": target_model,
                "litellm_params": deployed_params,
            })

        return legacy_entries

    def _init_litellm(self) -> None:
        """Initialize litellm Router from channels / YAML / legacy keys."""
        config = self._get_runtime_config()
        if self._get_hermes_config_error(config) is not None:
            logger.error("Analyzer LLM: Hermes channel configuration blocks legacy fallback")
            return
        litellm_model = config.litellm_model
        if not litellm_model:
            backend_id = ""
            try:
                backend_id = resolve_generation_backend_id(config)
            except GenerationError:
                pass
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.info(
                    "Analyzer LiteLLM: LITELLM_MODEL not configured; using %s generation backend",
                    backend_id,
                )
            else:
                logger.warning("Analyzer LLM: LITELLM_MODEL not configured")
            return

        self._litellm_available = True

        # --- Channel / YAML path: build Router from pre-built model_list ---
        if self._has_channel_config(config):
            model_list = config.llm_model_list
            if self._get_mixed_hermes_route_error(config, litellm_model) is not None:
                self._litellm_available = False
                logger.error("Analyzer LLM: mixed Hermes/non-Hermes route requires deployment-level no-proxy support")
                return
            router_model_list = model_list
            if route_has_hermes(model_list, litellm_model):
                # Hermes-only routes are dispatched directly with a request-scoped
                # no-proxy OpenAI client. Keeping them out of Router prevents the
                # default proxy-aware transport from seeing the Hermes bearer key.
                router_model_list = filter_non_hermes_deployments(model_list)
                if not router_model_list:
                    self._litellm_available = True
                    logger.info("Analyzer LLM: Hermes-only route will use direct no-proxy completion")
                    return
            try:
                self._router = Router(
                    model_list=router_model_list,
                    routing_strategy="simple-shuffle",
                    num_retries=2,
                )
            except TypeError:
                logger.debug("Analyzer LLM: Router constructor signature not compatible; fallback to direct mode")
                self._router = None
            else:
                unique_models = list(dict.fromkeys(
                    e['litellm_params']['model'] for e in model_list
                ))
                logger.info(
                    f"Analyzer LLM: Router initialized from channels/YAML — "
                    f"{len(router_model_list)} deployment(s), models: {unique_models}"
                )
                return

        # --- Legacy path: build Router for multi-key, or use single key ---
        keys = get_api_keys_for_model(litellm_model, config)
        legacy_model_list = self._build_legacy_router_model_list_from_config(
            litellm_model,
            config.llm_model_list,
        )
        if len(legacy_model_list) <= 1 and keys:
            extra_params = extra_litellm_params(litellm_model, config)
            configured_model_list = [
                {
                    "model_name": litellm_model,
                    "litellm_params": {
                        "model": litellm_model,
                        "api_key": k,
                        **extra_params,
                    },
                }
                for k in keys
            ]
            if not legacy_model_list:
                legacy_model_list = configured_model_list
            elif len(legacy_model_list) < len(configured_model_list):
                legacy_model_list = configured_model_list

        if len(legacy_model_list) > 1:
            self._legacy_router_model_list = legacy_model_list
            try:
                self._router = Router(
                    model_list=legacy_model_list,
                    routing_strategy="simple-shuffle",
                    num_retries=2,
                )
            except TypeError:
                logger.debug("Analyzer LLM: Legacy Router constructor signature not compatible; using legacy model_list fallback")
                self._router = None
            else:
                logger.info(
                    f"Analyzer LLM: Legacy Router initialized with {len(legacy_model_list)} keys "
                    f"for {litellm_model}"
                )
                return

        if keys:
            logger.info(f"Analyzer LLM: litellm initialized (model={litellm_model})")
        else:
            logger.info(
                f"Analyzer LLM: litellm initialized (model={litellm_model}, "
                f"API key from environment)"
            )

    def is_available(self) -> bool:
        """Check whether the configured generation backend is available."""
        backend_error = self.get_generation_backend_config_error()
        if backend_error is not None:
            return self._can_use_generation_fallback(backend_error)
        backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
        if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
            return True
        return self._litellm_runtime_available()

    def _litellm_runtime_available(self) -> bool:
        return self._router is not None or self._litellm_available

    def _can_use_generation_fallback(self, backend_error: GenerationError) -> bool:
        if not backend_error.fallbackable:
            return False
        try:
            _backend_id, fallback_backend_id = self._resolve_generation_backend_config()
        except GenerationError:
            return False
        return (
            fallback_backend_id == LITELLM_BACKEND_ID
            and self._litellm_runtime_available()
        )

    def _resolve_generation_backend_config(self) -> Tuple[str, Optional[str]]:
        """Resolve and validate generation backend ids."""
        config = self._get_runtime_config()
        backend_id = resolve_generation_backend_id(config)
        fallback_backend_id = resolve_generation_fallback_backend_id(config)
        return backend_id, fallback_backend_id

    def get_generation_backend_config_error(self) -> Optional[GenerationError]:
        """Return a structured backend config error, if the backend cannot run."""
        try:
            backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            config = self._get_runtime_config()
            hermes_error = self._get_hermes_config_error(config)
            if hermes_error is not None:
                return hermes_error
            for model in [getattr(config, "litellm_model", "")] + list(getattr(config, "litellm_fallback_models", []) or []):
                mixed_error = self._get_mixed_hermes_route_error(config, model)
                if mixed_error is not None:
                    return mixed_error
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                backend = self._get_generation_backend(backend_id)
                get_config_error = getattr(backend, "get_config_error", None)
                if callable(get_config_error):
                    return get_config_error()
        except GenerationError as exc:
            return exc
        return None

    def _get_hermes_config_error(self, config: Config) -> Optional[GenerationError]:
        issues = list(getattr(config, "llm_channel_config_issues", []) or [])
        if not getattr(config, "llm_blocks_legacy_fallback", False) or not issues:
            return None
        blocked_routes = set(getattr(config, "llm_blocked_hermes_routes", []) or [])
        selected_models = [
            ("LITELLM_MODEL", getattr(config, "litellm_model", "") or ""),
            *[
                ("LITELLM_FALLBACK_MODELS", fallback_model)
                for fallback_model in list(getattr(config, "litellm_fallback_models", []) or [])
            ],
        ]
        selected_blocked_route = ""
        selected_field = ""
        for field_name, model in selected_models:
            raw_model = str(model or "").strip()
            if not raw_model:
                continue
            candidates = hermes_blocked_route_candidates(raw_model)
            candidates.add(raw_model)
            try:
                candidates.add(canonicalize_hermes_model_ref(raw_model).route_model)
            except (TypeError, ValueError) as exc:
                logger.debug("Failed to canonicalize selected Hermes route candidate %r: %s", raw_model, exc)
            matched = candidates & blocked_routes
            if matched:
                selected_blocked_route = sorted(matched)[0]
                selected_field = field_name
                break
        if blocked_routes and not selected_blocked_route and getattr(config, "llm_model_list", None):
            return None
        first = issues[0]
        code = (
            "explicit_hermes_route_invalid"
            if selected_blocked_route
            else first.get("code", "invalid_hermes_channel")
        )
        return GenerationError(
            error_code=GenerationErrorCode.UNSAFE_CONFIG,
            stage="configuration",
            retryable=False,
            fallbackable=False,
            backend=LITELLM_BACKEND_ID,
            provider=HERMES_CHANNEL_NAME,
            details={
                "field": selected_field or first.get("field", "LLM_HERMES_API_KEY"),
                "code": code,
                "reason": code,
                "message": first.get("message", "Hermes channel configuration is invalid"),
                "issues": issues,
                "route_name": selected_blocked_route or None,
            },
        )

    def _get_mixed_hermes_route_error(self, config: Config, model: str) -> Optional[GenerationError]:
        if not model:
            return None
        origins = route_deployment_origins(getattr(config, "llm_model_list", []) or [], model)
        if not origins.is_mixed:
            return None
        return GenerationError(
            error_code=GenerationErrorCode.UNSAFE_CONFIG,
            stage="configuration",
            retryable=False,
            fallbackable=False,
            backend=LITELLM_BACKEND_ID,
            provider=HERMES_CHANNEL_NAME,
            details={
                "field": "LLM_CHANNELS",
                "code": "mixed_hermes_route_unsupported",
                "reason": "router_deployment_no_proxy_unavailable",
                "route_name": model,
            },
        )

    def _hermes_redaction_values_for_model(self, config: Config, model: str = "") -> set[str]:
        redactions: set[str] = set()
        deployments = list(getattr(config, "llm_model_list", []) or [])
        selected_deployments = deployments
        if model:
            origins = route_deployment_origins(deployments, model)
            selected_deployments = list(origins.hermes_deployments or [])
            if not selected_deployments and not origins.has_hermes:
                return redactions
        for deployment in selected_deployments:
            if not isinstance(deployment, dict):
                continue
            if not route_has_hermes([deployment], str(deployment.get("model_name") or "")):
                continue
            params = deployment.get("litellm_params") or {}
            if isinstance(params, dict):
                redactions.update(build_hermes_redaction_values(params.get("api_key")))
        return redactions

    def _sanitize_hermes_exception_text(
        self,
        exc: Any,
        *,
        config: Optional[Config] = None,
        model: str = "",
    ) -> str:
        runtime_config = config or self._get_runtime_config()
        redactions = self._hermes_redaction_values_for_model(runtime_config, model)
        if not redactions:
            return str(exc)
        return sanitize_hermes_error_text(exc, redaction_values=redactions)

    def _litellm_redaction_values_for_model(self, config: Config, model: str = "") -> set[str]:
        redactions = self._hermes_redaction_values_for_model(config, model)
        try:
            redactions.update(build_hermes_redaction_values(*get_api_keys_for_model(model, config)))
        except Exception:
            pass
        origins = route_deployment_origins(getattr(config, "llm_model_list", []) or [], model)
        for deployment in (*origins.hermes_deployments, *origins.non_hermes_deployments):
            params = deployment.get("litellm_params") if isinstance(deployment, dict) else None
            if isinstance(params, dict):
                redactions.update(build_hermes_redaction_values(params.get("api_key")))
        return redactions

    def _sanitize_litellm_exception_text(
        self,
        exc: Any,
        *,
        config: Optional[Config] = None,
        model: str = "",
    ) -> str:
        runtime_config = config or self._get_runtime_config()
        redactions = self._litellm_redaction_values_for_model(runtime_config, model)
        sanitized = sanitize_hermes_error_text(exc, redaction_values=redactions)
        return redact_diagnostic_text(sanitized, limit=500)

    def _dispatch_litellm_completion(
        self,
        model: str,
        call_kwargs: Dict[str, Any],
        *,
        config: Config,
        use_channel_router: bool,
        router_model_names: set[str],
    ) -> Any:
        """Dispatch a LiteLLM completion through router or direct fallback."""
        origins = route_deployment_origins(config.llm_model_list, model)
        if origins.is_mixed:
            raise RuntimeError("Hermes/non-Hermes mixed generation route is not supported without deployment-level no-proxy client support")
        if origins.is_hermes_only:
            deployment = origins.hermes_deployments[0]
            params = dict(deployment.get("litellm_params") or {})
            api_key = str(params.get("api_key") or "").strip()
            base_url = str(params.get("api_base") or "").strip()
            if is_masked_secret_placeholder(api_key):
                raise RuntimeError("Hermes API key is a masked placeholder and cannot be used for generation")
            timeout = float(call_kwargs.get("timeout") or 30.0)
            hermes_kwargs = dict(call_kwargs)
            hermes_kwargs["model"] = str(params.get("model") or model)
            hermes_kwargs["stream"] = False
            hermes_kwargs.pop("api_key", None)
            hermes_kwargs.pop("api_base", None)
            with open_hermes_no_proxy_client(api_key=api_key, base_url=base_url, timeout=timeout) as client:
                hermes_kwargs["client"] = client
                return litellm.completion(**hermes_kwargs)

        wire_models = resolve_fallback_litellm_wire_models(model, config.llm_model_list)
        register_fallback_model_pricing(wire_models)
        effective_kwargs = dict(call_kwargs)
        if use_channel_router and self._router and model in router_model_names:
            return self._router.completion(**effective_kwargs)
        if self._router and model == config.litellm_model and not use_channel_router:
            return self._router.completion(**effective_kwargs)

        keys = get_api_keys_for_model(model, config)
        if keys:
            effective_kwargs["api_key"] = keys[0]
        effective_kwargs.update(extra_litellm_params(model, config))
        return litellm.completion(**effective_kwargs)

    def _normalize_usage(
        self,
        usage_obj: Any,
        *,
        model: str = "",
        provider: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Normalize usage objects from LiteLLM responses/chunks."""
        if not usage_obj:
            usage = attach_message_hmacs({}, messages) if messages is not None else {}
            return filter_prompt_cache_telemetry(usage, self._get_runtime_config())
        usage = normalize_litellm_usage(usage_obj, model=model, provider=provider)
        if messages is not None:
            usage = attach_message_hmacs(usage, messages)
        return filter_prompt_cache_telemetry(usage, self._get_runtime_config())

    @staticmethod
    def _get_response_field(obj: Any, key: str) -> Any:
        """Read a field from dict-like or object-like LiteLLM payloads."""
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _extract_text_blocks(self, blocks: Any, *, strip: bool = True) -> str:
        """Extract final-answer text from OpenAI-compatible content blocks.

        Some reasoning models (including MiniMax) expose thinking and final
        answer blocks in the same list.  Thinking blocks can also carry a
        ``text`` field, so concatenating every block corrupts structured output
        by prefixing the JSON answer with chain-of-thought text.
        """
        if not blocks:
            return ""

        parts: List[str] = []
        for block in blocks:
            if isinstance(block, str):
                parts.append(block)
                continue

            block_type = ""
            text = None
            if isinstance(block, dict):
                block_type = str(block.get("type") or "").strip().lower()
                text = block.get("text")
                if text is None:
                    text = block.get("content")
            else:
                block_type = str(getattr(block, "type", "") or "").strip().lower()
                text = getattr(block, "text", None)
                if text is None:
                    text = getattr(block, "content", None)

            # Keep untyped legacy blocks for compatibility, but typed blocks
            # must explicitly represent final output text.
            if block_type and block_type not in {"text", "output_text"}:
                continue
            if isinstance(text, str) and text:
                parts.append(text)

        result = "".join(parts)
        return result.strip() if strip else result

    def _extract_completion_text(self, response: Any) -> str:
        """Extract text from non-stream LiteLLM completion responses."""
        choices = self._get_response_field(response, "choices")
        if not choices:
            return ""

        choice = choices[0]
        message = self._get_response_field(choice, "message")

        content_blocks = self._get_response_field(choice, "content_blocks")
        if content_blocks is None and message is not None:
            content_blocks = self._get_response_field(message, "content_blocks")
        block_text = self._extract_text_blocks(content_blocks)
        if block_text:
            return strip_leading_think_wrapper(block_text)

        content = None
        if message is not None:
            content = self._get_response_field(message, "content")
        if content is None:
            content = self._get_response_field(choice, "content")

        if isinstance(content, list):
            return strip_leading_think_wrapper(self._extract_text_blocks(content))
        if isinstance(content, str):
            return strip_leading_think_wrapper(content)
        return str(content).strip() if content is not None else ""

    def _extract_stream_text(self, chunk: Any) -> str:
        """Extract provider-agnostic text delta from a LiteLLM streaming chunk."""
        choices = chunk.get("choices") if isinstance(chunk, dict) else getattr(chunk, "choices", None)
        if not choices:
            return ""

        choice = choices[0]
        delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
        message = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)

        content: Any = None
        if isinstance(delta, dict):
            content = delta.get("content")
        elif isinstance(delta, str):
            content = delta
        elif delta is not None:
            content = getattr(delta, "content", None)

        if content is None:
            if isinstance(message, dict):
                content = message.get("content")
            elif message is not None:
                content = getattr(message, "content", None)

        if isinstance(content, list):
            return self._extract_text_blocks(content, strip=False)

        return content if isinstance(content, str) else ""

    def _consume_litellm_stream(
        self,
        stream_response: Any,
        *,
        model: str,
        usage_model: Optional[str] = None,
        provider: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Consume a LiteLLM stream into a single text payload."""
        chunks: List[str] = []
        usage: Dict[str, Any] = {}
        chars_received = 0
        next_emit_at = 1

        try:
            for chunk in stream_response:
                chunk_usage = extract_usage_payload(chunk)
                normalized_usage = self._normalize_usage(
                    chunk_usage,
                    model=usage_model or model,
                    provider=provider,
                )
                if normalized_usage:
                    usage = normalized_usage

                delta_text = self._extract_stream_text(chunk)
                if not delta_text:
                    continue

                chunks.append(delta_text)
                chars_received += len(delta_text)
                if progress_callback and chars_received >= next_emit_at:
                    progress_callback(chars_received)
                    next_emit_at = chars_received + 160
        except Exception as exc:
            raise _LiteLLMStreamError(
                f"{model} stream interrupted: {exc}",
                partial_received=chars_received > 0,
            ) from exc

        response_text = strip_leading_think_wrapper("".join(chunks))
        if not response_text:
            raise _LiteLLMStreamError(
                f"{model} stream returned empty response",
                partial_received=False,
            )

        if progress_callback and chars_received > 0:
            progress_callback(chars_received)

        return response_text, usage

    def _get_generation_backend(self, backend_id: Optional[str] = None) -> GenerationBackend:
        """Return the configured generation backend."""
        config = self._get_runtime_config()
        resolved_backend_id = backend_id or self._resolve_generation_backend_config()[0]
        return create_generation_backend(
            resolved_backend_id,
            config=config,
            litellm_completion_callable=self._call_litellm_impl,
        )

    def _call_litellm(
        self,
        prompt: str,
        generation_config: dict,
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        response_validator: Optional[Callable[[str], None]] = None,
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Compatibility wrapper around the configured generation backend."""
        preflight_error = self.get_generation_backend_config_error()
        if preflight_error is not None and not self._can_use_generation_fallback(preflight_error):
            raise preflight_error
        backend_id, fallback_backend_id = self._resolve_generation_backend_config()
        try:
            result = self._get_generation_backend(backend_id).generate(
                prompt,
                generation_config,
                system_prompt=system_prompt,
                stream=stream,
                stream_progress_callback=stream_progress_callback,
                response_validator=response_validator,
                audit_context=audit_context,
            )
        except GenerationError as exc:
            if not exc.fallbackable or not fallback_backend_id:
                raise
            try:
                fallback_backend = self._get_generation_backend(fallback_backend_id)
            except GenerationError as fallback_exc:
                raise GenerationError(
                    error_code=fallback_exc.error_code,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_exc.provider,
                    details={
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": fallback_exc.details,
                    },
                ) from fallback_exc
            try:
                result = fallback_backend.generate(
                    prompt,
                    generation_config,
                    system_prompt=system_prompt,
                    stream=stream,
                    stream_progress_callback=stream_progress_callback,
                    response_validator=response_validator,
                    audit_context=audit_context,
                )
            except _AllModelsFailedError:
                raise
            except GenerationError as fallback_exc:
                raise GenerationError(
                    error_code=fallback_exc.error_code,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_exc.provider,
                    details={
                        "reason": "fallback_backend_failed",
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": {
                            "error_code": fallback_exc.error_code.value,
                            "backend": fallback_exc.backend,
                            "provider": fallback_exc.provider,
                            "stage": fallback_exc.stage,
                            "details": fallback_exc.details,
                        },
                    },
                ) from fallback_exc
            except Exception as fallback_exc:
                raise GenerationError(
                    error_code=GenerationErrorCode.UNKNOWN_BACKEND_ERROR,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_backend_id,
                    details={
                        "reason": "fallback_backend_failed",
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": str(fallback_exc),
                    },
                ) from fallback_exc
        return result.text, result.model, result.usage

    def _call_litellm_impl(
        self,
        prompt: str,
        generation_config: dict,
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        response_validator: Optional[Callable[[str], None]] = None,
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Call LLM via litellm with fallback across configured models.

        When channels/YAML are configured, every model goes through the Router
        (which handles per-model key selection, load balancing, and retries).
        In legacy mode, the primary model may use the Router while fallback
        models fall back to direct litellm.completion().

        Args:
            prompt: User prompt text.
            generation_config: Dict with optional keys: temperature, max_output_tokens, max_tokens.
            response_validator: Optional callable that accepts the raw response text and raises
                an exception if the response is unacceptable (e.g. not valid JSON).  When it
                raises, the current model is treated as failed and the next fallback model is
                tried.  If all models fail validation, :class:`_AllModelsFailedError` is raised
                with ``last_response_text`` set to the last raw response received.

        Returns:
            Tuple of (response text, model_used, usage). On success model_used is the full model
            name and usage is a dict with prompt_tokens, completion_tokens, total_tokens.
        """
        config = self._get_runtime_config()
        max_tokens = (
            generation_config.get('max_output_tokens')
            or generation_config.get('max_tokens')
            or 8192
        )
        requested_temperature = generation_config.get('temperature', 0.7)
        requested_timeout = generation_config.get("timeout")

        models_to_try = [config.litellm_model] + (config.litellm_fallback_models or [])
        models_to_try = [m for m in models_to_try if m]

        use_channel_router = self._has_channel_config(config)

        last_error = None
        last_response_text: Optional[str] = None
        last_model: Optional[str] = None
        last_usage: Dict[str, Any] = {}
        effective_system_prompt = system_prompt or self.TEXT_SYSTEM_PROMPT
        router_model_names = set(get_configured_llm_models(config.llm_model_list))
        for model in models_to_try:
            origins = route_deployment_origins(config.llm_model_list, model)
            model_stream = bool(stream and not origins.has_hermes)
            recovery_model_list = config.llm_model_list
            legacy_router_model_list = getattr(self, "_legacy_router_model_list", None) or []
            if legacy_router_model_list and model == config.litellm_model and not use_channel_router:
                recovery_model_list = legacy_router_model_list
            usage_model, usage_provider = resolved_model_provider_identity(model, recovery_model_list)

            try:
                def _attach_usage_audit(
                    usage: Dict[str, Any],
                    messages: List[Dict[str, Any]],
                ) -> Dict[str, Any]:
                    if audit_context is None:
                        return filter_prompt_cache_telemetry(
                            attach_message_hmacs(usage, messages),
                            config,
                        )
                    effective_audit_context = dict(audit_context)
                    effective_audit_context["provider"] = usage_provider
                    effective_audit_context["transport"] = (
                        effective_audit_context.get("transport") or "litellm"
                    )
                    return filter_prompt_cache_telemetry(
                        attach_legacy_message_stability_audit(
                            usage,
                            messages,
                            effective_audit_context,
                        ),
                        config,
                    )

                model_short = model.split("/")[-1] if "/" in model else model
                extra = get_thinking_extra_body(model_short)
                call_kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": effective_system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                }
                if requested_timeout not in (None, ""):
                    call_kwargs["timeout"] = requested_timeout
                if extra:
                    call_kwargs["extra_body"] = extra
                uses_router = (
                    (use_channel_router and self._router and model in router_model_names)
                    or (self._router and model == config.litellm_model and not use_channel_router)
                )
                if not uses_router:
                    try:
                        keys = get_api_keys_for_model(model, config)
                    except AttributeError:
                        keys = []
                    if keys:
                        call_kwargs["api_key"] = keys[0]
                    try:
                        call_kwargs.update(extra_litellm_params(model, config))
                    except AttributeError:
                        pass
                call_kwargs = apply_litellm_generation_params(
                    call_kwargs,
                    model,
                    requested_temperature,
                    model_list=recovery_model_list,
                )
                route_context = build_provider_cache_route_context(
                    model=model,
                    provider=usage_provider,
                    call_kwargs=call_kwargs,
                    model_list=recovery_model_list,
                    call_type="analysis",
                )
                hint_result = apply_prompt_cache_hints(call_kwargs, route_context, config)
                call_kwargs = hint_result.call_kwargs
                if requested_timeout not in (None, ""):
                    call_kwargs["timeout"] = requested_timeout
                if hint_result.diagnostics:
                    logger.debug("[PromptCache] %s", hint_result.diagnostics)

                _stream_text: Optional[str] = None
                _stream_usage: Dict[str, Any] = {}

                if model_stream:
                    try:
                        stream_response = call_litellm_with_param_recovery(
                            lambda kwargs: self._dispatch_litellm_completion(
                                model,
                                kwargs,
                                config=config,
                                use_channel_router=use_channel_router,
                                router_model_names=router_model_names,
                            ),
                            model=model,
                            call_kwargs={**call_kwargs, "stream": True},
                            model_list=recovery_model_list,
                            cache_recovery=False,
                            logger=logger,
                        )
                        _stream_text, _stream_usage = self._consume_litellm_stream(
                            stream_response,
                            model=model,
                            usage_model=usage_model,
                            provider=usage_provider,
                            progress_callback=stream_progress_callback,
                        )
                    except _LiteLLMStreamError as exc:
                        safe_error = self._sanitize_litellm_exception_text(exc, config=config, model=model)
                        if exc.partial_received:
                            logger.warning(
                                "[LiteLLM] %s stream failed after partial output, retrying non-stream for same model: %s",
                                model,
                                safe_error,
                            )
                        else:
                            logger.warning(
                                "[LiteLLM] %s stream unavailable before first chunk, falling back to non-stream: %s",
                                model,
                                safe_error,
                            )
                        last_error = RuntimeError(f"{type(exc).__name__}: {safe_error}")
                    except Exception as exc:
                        safe_error = self._sanitize_litellm_exception_text(exc, config=config, model=model)
                        logger.warning(
                            "[LiteLLM] %s stream request failed before first chunk, falling back to non-stream: %s",
                            model,
                            safe_error,
                        )

                if _stream_text is not None:
                    last_response_text = _stream_text
                    last_model = model
                    _stream_usage = _attach_usage_audit(_stream_usage, call_kwargs["messages"])
                    last_usage = _stream_usage
                    if response_validator is not None:
                        response_validator(_stream_text)
                    return _stream_text, model, _stream_usage

                response = call_litellm_with_param_recovery(
                    lambda kwargs: self._dispatch_litellm_completion(
                        model,
                        kwargs,
                        config=config,
                        use_channel_router=use_channel_router,
                        router_model_names=router_model_names,
                    ),
                    model=model,
                    call_kwargs=call_kwargs,
                    model_list=recovery_model_list,
                    logger=logger,
                )

                content = self._extract_completion_text(response)
                if content:
                    usage_messages = None if audit_context is not None else call_kwargs["messages"]
                    usage = self._normalize_usage(
                        extract_usage_payload(response),
                        model=usage_model or model,
                        provider=usage_provider,
                        messages=usage_messages,
                    )
                    if audit_context is not None:
                        usage = _attach_usage_audit(usage, call_kwargs["messages"])
                    last_response_text = content
                    last_model = model
                    last_usage = usage
                    if response_validator is not None:
                        response_validator(content)
                    return (content, model, usage)
                raise ValueError("LLM returned empty response")

            except Exception as e:
                safe_error = self._sanitize_litellm_exception_text(e, config=config, model=model)
                logger.warning("[LiteLLM] %s failed: %s", model, safe_error)
                last_error = RuntimeError(f"{type(e).__name__}: {safe_error}")
                continue

        raise _AllModelsFailedError(
            f"All LLM models failed (tried {len(models_to_try)} model(s)). Last error: {last_error}",
            last_response_text=last_response_text,
            last_model=last_model,
            last_usage=last_usage,
        )

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Public entry point for free-form text generation.

        External callers (e.g. MarketAnalyzer) must use this method instead of
        calling _call_litellm() directly or accessing private attributes such as
        _litellm_available, _router, _model, _use_openai, or _use_anthropic.

        Args:
            prompt:      Text prompt to send to the LLM.
            max_tokens:  Maximum tokens in the response (default 2048).
            temperature: Sampling temperature (default 0.7).

        Returns:
            Response text, or None if the LLM call fails (error is logged).
        """
        try:
            result = self._call_litellm(
                prompt,
                generation_config={"max_tokens": max_tokens, "temperature": temperature},
            )
            if isinstance(result, tuple):
                text, model_used, usage = result
                if should_persist_usage_telemetry(usage):
                    persist_llm_usage(usage, model_used, call_type="market_review")
                return text
            return result
        except GenerationError:
            raise
        except Exception as exc:
            logger.error("[generate_text] LLM call failed: %s", exc)
            return None

    def analyze(
        self, 
        context: Dict[str, Any],
        news_context: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        analysis_context_pack_summary: Optional[str] = None,
    ) -> AnalysisResult:
        """
        Analyze individual stocks
        
        process：
        1. Format input data（technical aspect + news）
        2. call Gemini API（With retries and model switching）
        3. parse JSON response
        4. Return structured results
        
        Args:
            context: from storage.get_analysis_context() Get context data
            news_context: Pre-searched news content（Optional）

        Returns:
            AnalysisResult object
        """
        def _emit_progress(progress: int, message: str) -> None:
            if progress_callback is None:
                return
            try:
                progress_callback(progress, message)
            except Exception as exc:
                logger.debug("[analyzer] progress callback skipped: %s", exc)

        code = context.get('code', 'Unknown')
        config = self._get_runtime_config()
        report_language = normalize_report_language(getattr(config, "report_language", "zh"))
        system_prompt = self._get_analysis_system_prompt(report_language, stock_code=code)
        skill_instructions, default_skill_policy, use_legacy_default_prompt = self._get_skill_prompt_sections()
        
        # Add delay before request（Prevent continuous requests from triggering current limiting）
        request_delay = config.gemini_request_delay
        if request_delay > 0:
            logger.debug(f"[LLM] wait before requesting {request_delay:.1f} Second...")
            _emit_progress(65, f"{code}：LLM wait before requesting {request_delay:.1f} seconds")
            time.sleep(request_delay)
        
        # Get stock name from context first（Depend on main.py incoming）
        name = context.get('stock_name')
        if not name or name.startswith('stocks'):
            # alternative：from realtime Get in
            if 'realtime' in context and context['realtime'].get('name'):
                name = context['realtime']['name']
            else:
                # Finally get from the mapping table
                name = STOCK_NAME_MAP.get(code, f'stocks{code}')

        backend_error = self.get_generation_backend_config_error()
        if backend_error is not None and not self._can_use_generation_fallback(backend_error):
            details = backend_error.details or {}
            field = str(details.get("field") or "GENERATION_BACKEND")
            requested_backend = str(details.get("requested_backend") or backend_error.backend)
            reason = str(details.get("reason") or backend_error.error_code.value)
            if report_language == "en":
                summary = (
                    "AI analysis is unavailable because the generation backend "
                    f"cannot start: {backend_error.error_code.value}."
                )
                risk_warning = (
                    f"Check {field}={requested_backend} ({reason}) or set a valid "
                    "backend/fallback before retrying."
                )
            elif report_language == "ko":
                summary = (
                    "생성 백엔드를 시작할 수 없어 AI 분석을 사용할 수 없습니다: "
                    f"{backend_error.error_code.value}."
                )
                risk_warning = (
                    f"{field}={requested_backend} ({reason})를 확인하거나 유효한 "
                    "백엔드/폴백을 설정한 뒤 다시 시도하세요."
                )
            else:
                summary = (
                    "AI Analysis function is not available：Check, please，"
                    f"{backend_error.error_code.value}。"
                )
                risk_warning = (
                    f"Check, please {field}={requested_backend}（{reason}），"
                    "Or configure a valid backend/Go back and try again。"
                )
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('shock', report_language),
                operation_advice=localize_operation_advice('hold', report_language),
                confidence_level=localize_confidence_level('low', report_language),
                analysis_summary=summary,
                risk_warning=risk_warning,
                success=False,
                error_message=(
                    f"{backend_error.error_code.value}: {field}={requested_backend}"
                ),
                model_used=None,
                report_language=report_language,
            )

        # If the model is not available，Return default results
        if not self.is_available():
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('shock', report_language),
                operation_advice=localize_operation_advice('hold', report_language),
                confidence_level=localize_confidence_level('low', report_language),
                analysis_summary=_localized_text(
                    report_language,
                    en='AI analysis is unavailable because no API key is configured.',
                    zh='AI Analysis is not enabled（Not configured API Key）',
                    ko='API 키가 설정되지 않아 AI 분석을 사용할 수 없습니다.',
                ),
                risk_warning=_localized_text(
                    report_language,
                    en='Configure an LLM API key (GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY) and retry.',
                    zh='Please configure LLM API Key（GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY）Try again later',
                    ko='LLM API 키(GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY)를 설정한 뒤 다시 시도하세요.',
                ),
                success=False,
                error_message=_localized_text(
                    report_language,
                    en='LLM API key is not configured',
                    zh='LLM API Key Not configured',
                    ko='LLM API 키가 설정되지 않았습니다',
                ),
                model_used=None,
                report_language=report_language,
            )
        
        try:
            # Formatted input（Contains technical data and news）
            prompt = self._format_prompt(
                context,
                name,
                news_context,
                report_language=report_language,
                analysis_context_pack_summary=analysis_context_pack_summary,
            )
            legacy_audit_context = {
                "language": report_language,
                "market_group": _legacy_market_group(code),
                "analysis_mode": "stock_analysis",
                "legacy_prompt_mode": "legacy_default" if use_legacy_default_prompt else "skill_aware",
                "skill_config": {
                    "skill_instructions": skill_instructions,
                    "default_skill_policy": default_skill_policy,
                    "use_legacy_default_prompt": use_legacy_default_prompt,
                },
                "transport": "litellm",
                "dynamic_markers": _legacy_audit_marker_specs(
                    context,
                    code=code,
                    stock_name=name,
                    report_language=report_language,
                    news_context=news_context,
                    analysis_context_pack_summary=analysis_context_pack_summary,
                ),
            }
            
            config = self._get_runtime_config()
            backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            model_name = config.litellm_model or "unknown"
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                model_name = backend_id
                legacy_audit_context["transport"] = backend_id
            logger.info(f"========== AI analyze {name}({code}) ==========")
            logger.info(f"[LLMConfiguration] Model: {model_name}")
            logger.info(f"[LLMConfiguration] Prompt length: {len(prompt)} character")
            logger.info(f"[LLMConfiguration] Whether to include news: {'Yes' if news_context else 'No'}")

            # Is the process execution capability CLI backend Is the process execution capability，Not complete record prompt。
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                prompt_preview = redact_diagnostic_text(prompt, limit=500)
            else:
                prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.info(f"[LLM Prompt Preview]\n{prompt_preview}")
            if backend_id not in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.debug(f"=== whole Prompt ({len(prompt)}character) ===\n{prompt}\n=== End Prompt ===")

            # Set build configuration
            generation_config = {
                "temperature": config.llm_temperature,
                "max_output_tokens": 8192,
            }

            logger.info(f"[LLMcall] Start calling {model_name}...")
            _emit_progress(68, f"{name}：LLM Request received，Waiting for response")

            # use litellm call（Support integrity check retry）
            current_prompt = prompt
            retry_count = 0
            max_retries = config.report_integrity_retry if config.report_integrity_enabled else 0

            while True:
                start_time = time.time()
                try:
                    response_text, model_used, llm_usage = self._call_litellm(
                        current_prompt,
                        generation_config,
                        system_prompt=system_prompt,
                        stream=True,
                        stream_progress_callback=stream_progress_callback,
                        response_validator=self._validate_json_response,
                        audit_context=legacy_audit_context,
                    )
                except _AllModelsFailedError as exc:
                    if exc.last_response_text is not None:
                        logger.warning(
                            "[LLM JSON] %s(%s): all models returned invalid JSON, using text fallback",
                            name,
                            code,
                        )
                        response_text = exc.last_response_text
                        model_used = exc.last_model
                        llm_usage = exc.last_usage
                    else:
                        raise
                elapsed = time.time() - start_time

                # Record response information
                logger.info(
                    f"[LLMreturn] {model_name} Response successful, time consuming {elapsed:.2f}s, response length {len(response_text)} character"
                )
                if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                    response_preview = redact_diagnostic_text(response_text, limit=300)
                else:
                    response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
                logger.info(f"[LLMreturn Preview]\n{response_preview}")
                if backend_id not in LOCAL_CLI_GENERATION_BACKEND_IDS:
                    logger.debug(
                        f"=== {model_name} full response ({len(response_text)}character) ===\n{response_text}\n=== End Response ==="
                    )
                # Keep parser/retry progress monotonic so task progress/message never "goes backward".
                parse_progress = min(99, 93 + retry_count * 2)
                _emit_progress(parse_progress, f"{name}：LLM Return to completion，Parsing JSON")

                # Parse response
                result = self._parse_response(response_text, code, name)
                result.raw_response = response_text
                result.search_performed = bool(news_context)
                result.market_snapshot = self._build_market_snapshot(context)
                result.model_used = model_used
                result.report_language = report_language
                normalize_chip_structure_availability(result, context.get("chip"))

                # Content integrity check（Optional）
                if not config.report_integrity_enabled:
                    break
                require_phase_decision = isinstance(context.get("market_phase_context"), dict)
                pass_integrity, missing_fields = self._check_content_integrity(
                    result,
                    require_phase_decision=require_phase_decision,
                )
                if pass_integrity:
                    break
                if retry_count < max_retries:
                    current_prompt = self._build_integrity_retry_prompt(
                        prompt,
                        response_text,
                        missing_fields,
                        report_language=report_language,
                    )
                    retry_count += 1
                    logger.info(
                        "[LLMintegrity] Required fields are missing %s，No. %d completion retries",
                        missing_fields,
                        retry_count,
                    )
                    retry_progress = min(99, 92 + retry_count * 2)
                    _emit_progress(
                        retry_progress,
                        f"{name}：Report fields are incomplete，Completing and retrying（{retry_count}/{max_retries}）",
                    )
                else:
                    self._apply_placeholder_fill(result, missing_fields)
                    logger.warning(
                        "[LLMintegrity] Required fields are missing %s，Filled in place，Does not block the process",
                        missing_fields,
                    )
                    break

            if should_persist_usage_telemetry(llm_usage):
                persist_llm_usage(llm_usage, model_used, call_type="analysis", stock_code=code)

            logger.info(f"[LLMparse] {name}({code}) Analysis completed: {result.trend_prediction}, score {result.sentiment_score}")

            return result
            
        except Exception as e:
            safe_error = self._sanitize_hermes_exception_text(e)
            logger.error("AI analyze %s(%s) fail: %s", name, code, safe_error)
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('shock', report_language),
                operation_advice=localize_operation_advice('hold', report_language),
                confidence_level=localize_confidence_level('low', report_language),
                analysis_summary=_localized_text(
                    report_language,
                    en=f'Analysis failed: {safe_error[:100]}',
                    zh=f'An error occurred during analysis: {safe_error[:100]}',
                    ko=f'분석 중 오류가 발생했습니다: {safe_error[:100]}',
                ),
                risk_warning=_localized_text(
                    report_language,
                    en='Analysis failed. Please retry later or review manually.',
                    zh='Analysis failed，Please try again later or analyze manually',
                    ko='분석에 실패했습니다. 잠시 후 다시 시도하거나 수동으로 검토하세요.',
                ),
                success=False,
                error_message=safe_error,
                model_used=None,
                report_language=report_language,
            )
    
    def _format_prompt(
        self, 
        context: Dict[str, Any], 
        name: str,
        news_context: Optional[str] = None,
        report_language: str = "zh",
        analysis_context_pack_summary: Optional[str] = None,
    ) -> str:
        """
        Format analysis prompt words（Decision dashboard v2.0）
        
        Include：Technical indicators、Real-time quotes（Quantity ratio/turnover rate）、Chip distribution、trend analysis、news
        
        Args:
            context: Technical data context（Contains enhanced data）
            name: Stock name（default value，May be overridden by context）
            news_context: Pre-searched news content
        """
        code = context.get('code', 'Unknown')
        report_language = normalize_report_language(report_language)
        _, _, use_legacy_default_prompt = self._get_skill_prompt_sections()
        
        # Prefer stock names in context（from realtime_quote get）
        stock_name = context.get('stock_name', name)
        if not stock_name or stock_name == f'stocks{code}':
            stock_name = STOCK_NAME_MAP.get(code, f'stocks{code}')
            
        today = context.get('today', {})
        unknown_text = get_unknown_text(report_language)
        no_data_text = get_no_data_text(report_language)
        quote_section_title, close_price_label = _phase_aware_quote_labels(context)
        hide_regular_session_ohlc = _should_hide_regular_session_ohlc(context)
        realtime_overlay_quote = hide_regular_session_ohlc and _today_has_realtime_overlay(today)
        pct_chg_label = "Real-time price increase and decrease" if realtime_overlay_quote else "Increase or decrease"
        volume_label = "Real-time trading volume" if realtime_overlay_quote else "Volume"
        amount_label = "Real-time trading volume" if realtime_overlay_quote else "Turnover"
        quote_rows = [
            f"| {close_price_label} | {today.get('close', 'N/A')} Yuan |",
        ]
        if not hide_regular_session_ohlc:
            quote_rows.extend(
                [
                    f"| opening price | {today.get('open', 'N/A')} Yuan |",
                    f"| highest price | {today.get('high', 'N/A')} Yuan |",
                    f"| lowest price | {today.get('low', 'N/A')} Yuan |",
                ]
            )
        quote_rows.extend(
            [
                f"| {pct_chg_label} | {today.get('pct_chg', 'N/A')}% |",
                f"| {volume_label} | {self._format_volume(today.get('volume'))} |",
                f"| {amount_label} | {self._format_amount(today.get('amount'))} |",
            ]
        )
        quote_rows_text = "\n".join(quote_rows)
        
        # ========== Inputs for building decision dashboard formats ==========
        prompt = f"""# Decision Dashboard Analysis Request

## 📊 Basic stock information
| project | data |
|------|------|
| Stock code | **{code}** |
| Stock name | **{stock_name}** |
| Analysis date | {context.get('date', unknown_text)} |

---
"""
        prompt += format_market_phase_prompt_section(
            context.get("market_phase_context"),
            report_language=report_language,
        )
        daily_market_context_section = format_daily_market_context_prompt_section(
            context.get("daily_market_context"),
            report_language=report_language,
        )
        if daily_market_context_section:
            prompt += daily_market_context_section
        market_structure_section = format_market_structure_prompt_section(
            context.get("market_structure_context"),
            report_language=report_language,
        )
        if market_structure_section:
            prompt += market_structure_section
        if isinstance(analysis_context_pack_summary, str) and analysis_context_pack_summary:
            prompt += analysis_context_pack_summary
        prompt += f"""

## 📈 Technical data

### {quote_section_title}
| index | numerical value |
|------|------|
{quote_rows_text}

### moving average system（key judgment indicators）
| moving average | numerical value | illustrate |
|------|------|------|
| MA5 | {today.get('ma5', 'N/A')} | short term trend line |
| MA10 | {today.get('ma10', 'N/A')} | Short to medium term trend line |
| MA20 | {today.get('ma20', 'N/A')} | mid-term trend line |
| moving average pattern | {context.get('ma_status', unknown_text)} | long/short/twine |
"""
        
        # Add real-time market data（Quantity ratio、Turnover rate, etc.）
        if 'realtime' in context:
            rt = context['realtime']
            prompt += f"""
### Real-time market enhanced data
| index | numerical value | Interpretation |
|------|------|------|
| current price | {rt.get('price', 'N/A')} Yuan | |
| **Quantity ratio** | **{rt.get('volume_ratio', 'N/A')}** | {rt.get('volume_ratio_desc', '')} |
| **turnover rate** | **{rt.get('turnover_rate', 'N/A')}%** | |
| P/E ratio(dynamic) | {rt.get('pe_ratio', 'N/A')} | |
| price to book ratio | {rt.get('pb_ratio', 'N/A')} | |
| total market capitalization | {self._format_amount(rt.get('total_mv'))} | |
| Circulation market value | {self._format_amount(rt.get('circ_mv'))} | |
| 60daily increase or decrease | {rt.get('change_60d', 'N/A')}% | mid-term performance |
"""

        # Add financial reports and dividends（Value investment caliber）
        fundamental_context = context.get("fundamental_context") if isinstance(context, dict) else None
        earnings_block = (
            fundamental_context.get("earnings", {})
            if isinstance(fundamental_context, dict)
            else {}
        )
        earnings_data = (
            earnings_block.get("data", {})
            if isinstance(earnings_block, dict)
            else {}
        )
        financial_report = (
            earnings_data.get("financial_report", {})
            if isinstance(earnings_data, dict)
            else {}
        )
        dividend_metrics = (
            earnings_data.get("dividend", {})
            if isinstance(earnings_data, dict)
            else {}
        )
        if isinstance(financial_report, dict) or isinstance(dividend_metrics, dict):
            financial_report = financial_report if isinstance(financial_report, dict) else {}
            dividend_metrics = dividend_metrics if isinstance(dividend_metrics, dict) else {}
            ttm_yield = dividend_metrics.get("ttm_dividend_yield_pct", "N/A")
            ttm_cash = dividend_metrics.get("ttm_cash_dividend_per_share", "N/A")
            ttm_count = dividend_metrics.get("ttm_event_count", "N/A")
            report_date = financial_report.get("report_date", "N/A")
            prompt += f"""
### Financial reporting and dividends（Value investment caliber）
| index | numerical value | illustrate |
|------|------|------|
| most recent reporting period | {report_date} | From structured financial report fields |
| operating income | {financial_report.get('revenue', 'N/A')} | |
| Net profit attributable to parent company | {financial_report.get('net_profit_parent', 'N/A')} | |
| operating cash flow | {financial_report.get('operating_cash_flow', 'N/A')} | |
| ROE | {financial_report.get('roe', 'N/A')} | |
| close12Monthly cash dividend per share | {ttm_cash} | Cash dividends only、Pre-tax caliber |
| TTM dividend yield | {ttm_yield} | formula：close12Monthly cash dividend per share / current price × 100% |
| TTM If the above field is | {ttm_count} | |

> If the above field is N/A or missing，Please write clearly“missing data，Unable to judge”，Fabrication is prohibited。
"""

        capital_flow_block = (
            fundamental_context.get("capital_flow", {})
            if isinstance(fundamental_context, dict)
            else {}
        )
        capital_flow_data = (
            capital_flow_block.get("data", {})
            if isinstance(capital_flow_block, dict)
            else {}
        )
        stock_flow = (
            capital_flow_data.get("stock_flow", {})
            if isinstance(capital_flow_data, dict)
            else {}
        )
        sector_flow = (
            capital_flow_data.get("sector_rankings", {})
            if isinstance(capital_flow_data, dict)
            else {}
        )
        has_capital_flow = (
            isinstance(stock_flow, dict)
            and any(v is not None for v in stock_flow.values())
        ) or (
            isinstance(sector_flow, dict)
            and (sector_flow.get("top") or sector_flow.get("bottom"))
        )
        if has_capital_flow:
            top_sectors = sector_flow.get("top", []) if isinstance(sector_flow, dict) else []
            bottom_sectors = sector_flow.get("bottom", []) if isinstance(sector_flow, dict) else []
            top_sector_text = "、".join(
                str(item.get("name", "")).strip()
                for item in top_sectors[:3]
                if isinstance(item, dict) and str(item.get("name", "")).strip()
            ) or "N/A"
            bottom_sector_text = "、".join(
                str(item.get("name", "")).strip()
                for item in bottom_sectors[:3]
                if isinstance(item, dict) and str(item.get("name", "")).strip()
            ) or "N/A"
            prompt += f"""
### Main flow of funds（Action suggestions filter）
| index | numerical value | Main net inflow |
|------|------|----------|
| Main net inflow | {stock_flow.get('main_net_inflow', 'N/A')} | Positive value partial support，Negative bias suppression |
| 5daily net inflow | {stock_flow.get('inflow_5d', 'N/A')} | Used to determine the sustainability of funds |
| 10daily net inflow | {stock_flow.get('inflow_10d', 'N/A')} | Used to determine the sustainability of funds |
| Funds flow into the top sectors | {top_sector_text} | Top sectors with capital outflows |
| Top sectors with capital outflows | {bottom_sector_text} | Sector risk reference |

> Money flow can only serve as a filter for price position：When the pressure is close and the main force flows out, no additional buying is allowed.；When it is close to support and falls below it without heavy volume，Prioritize judgment as holding observation、Shake or wash and observe。
"""

        # Added three major corporate trends（Taiwan Stock Chip Filter）— tw-only；only if institution block status='ok'
        # Inject when there is a net amount，will skip status='not_supported' will skip，strict additive。
        institution_block = (
            fundamental_context.get("institution", {})
            if isinstance(fundamental_context, dict)
            else {}
        )
        institution_data = (
            institution_block.get("data", {})
            if isinstance(institution_block, dict)
            else {}
        )
        if (
            isinstance(institution_block, dict)
            and institution_block.get("status") == "ok"
            and isinstance(institution_data, dict)
            and all(
                institution_data.get(key) is not None
                for key in ("foreign_net", "trust_net", "dealer_net", "total_net")
            )
        ):
            prompt += f"""
### Net sales exceeded（Taiwan Stock Chip Filter，Net sales exceeded，unit:share）
| legal person | Net sales exceeded | Main net inflow |
|------|------|----------|
| foreign investment | {institution_data.get('foreign_net', 'N/A')} | Positive value=Net buy over bias support，negative value=Net selling over bias suppression |
| Put a letter | {institution_data.get('trust_net', 'N/A')} | Investment trust continues to buy abnormally with the midline going long |
| proprietor | {institution_data.get('dealer_net', 'N/A')} | Short-term hedging/Self-operated direction reference |
| Total of three major legal persons | {institution_data.get('total_net', 'N/A')} | The most watched chip signals for Taiwan stocks |
| Data date | {institution_data.get('date', 'N/A')} | source {institution_data.get('source', 'N/A')} |

> The three major legal persons are the chip filters for Taiwan stocks（Equivalent to A Main stock capital/Role in Dragon Tiger List，But the caliber is different、Not to be mixed）：Foreign capital and investment credit buy support price in the same direction、Net selling in the same direction suppresses the price。Please judge the chip structure of Taiwan stocks based on this，Do not write when this data is available“Chip structure：missing data”。
"""

        # Add chip distribution data
        if 'chip' in context:
            chip = context['chip']
            profit_ratio = chip.get('profit_ratio', 0)
            prompt += f"""
### Chip distribution data（efficiency index）
| index | numerical value | health standards |
|------|------|----------|
| **Profit ratio** | **{profit_ratio:.1%}** | 70-90%Always be vigilant |
| average cost | {chip.get('avg_cost', 'N/A')} Yuan | The current price should be higher than5-15% |
| 90%Chip concentration | {chip.get('concentration_90', 0):.2%} | <15%to concentrate |
| 70%Chip concentration | {chip.get('concentration_70', 0):.2%} | |
| Chip status | {chip.get('chip_status', unknown_text)} | |
"""
        else:
            chip_unavailable_text = get_chip_unavailable_text(report_language)
            chip_instruction = (
                "Do not fabricate profit ratio, average cost, or concentration. Mention chip data "
                "unavailability only once in the report; do not repeat per-field no-data text in `chip_structure`."
                if report_language in ("en", "ko")
                else "Don’t make up profit ratios、The report only states once that chip data is unavailable；The report only states once that chip data is unavailable，don't put“missing data，Unable to judge”Write repeatedly field by field `chip_structure`。"
            )
            prompt += f"""
### Chip distribution data（efficiency index）
> {chip_unavailable_text}
> {chip_instruction}
"""
        
        # Add trend analysis results（Only implicit built-ins bull_trend Default fallback to retain the old caliber）
        if 'trend_analysis' in context:
            trend = _sanitize_trend_analysis_for_prompt(
                context['trend_analysis'],
                volume_change_ratio=context.get('volume_change_ratio'),
            )
            consistency_notes = trend.get('prompt_consistency_notes', [])
            if use_legacy_default_prompt:
                bias_warning = "🚨 exceed5%，It is strictly forbidden to chase high！" if trend.get('bias_ma5', 0) > 5 else "✅ safety range"
                prompt += f"""
### Trend analysis and prediction（Based on trading concept）
| index | numerical value | determination |
|------|------|------|
| trend status | {trend.get('trend_status', unknown_text)} | |
| moving average arrangement | {trend.get('ma_alignment', unknown_text)} | MA5>MA10>MA20for long |
| state of energy | {trend.get('trend_strength', 0)}/100 | |
| **deviation rate(MA5)** | **{trend.get('bias_ma5', 0):+.2f}%** | {bias_warning} |
| deviation rate(MA10) | {trend.get('bias_ma10', 0):+.2f}% | |
| state of energy | {trend.get('volume_status', unknown_text)} | {trend.get('volume_trend', '')} |
| system signal | {trend.get('buy_signal', unknown_text)} | |
| System rating | {trend.get('signal_score', 0)}/100 | |

#### Reasons for system analysis
**Reasons to buy**：
{chr(10).join('- ' + r for r in trend.get('signal_reasons', ['None'])) if trend.get('signal_reasons') else '- None'}

**risk factors**：
{chr(10).join('- ' + r for r in trend.get('risk_factors', ['None'])) if trend.get('risk_factors') else '- None'}
"""
                if consistency_notes:
                    prompt += f"""

**consistency constraint**：
{chr(10).join('- ' + note for note in consistency_notes)}
"""
            else:
                bias_warning = (
                    "🚨 Large deviation，Risks need to be carefully assessed"
                    if trend.get('bias_ma5', 0) > 5
                    else "✅ The location is relatively controllable"
                )
                prompt += f"""
### Technical and Structural Analysis（For reference when judging activation skills）
| index | numerical value | illustrate |
|------|------|------|
| trend status | {trend.get('trend_status', unknown_text)} | |
| moving average arrangement | {trend.get('ma_alignment', unknown_text)} | Combined with activated skills to determine the strength of the structure |
| state of energy | {trend.get('trend_strength', 0)}/100 | |
| **price position(MA5)** | **{trend.get('bias_ma5', 0):+.2f}%** | {bias_warning} |
| price position(MA10) | {trend.get('bias_ma10', 0):+.2f}% | |
| state of energy | {trend.get('volume_status', unknown_text)} | {trend.get('volume_trend', '')} |
| system signal | {trend.get('buy_signal', unknown_text)} | |
| System rating | {trend.get('signal_score', 0)}/100 | |

#### Reasons for system analysis
**Supporting factors**：
{chr(10).join('- ' + r for r in trend.get('signal_reasons', ['None'])) if trend.get('signal_reasons') else '- None'}

**risk factors**：
{chr(10).join('- ' + r for r in trend.get('risk_factors', ['None'])) if trend.get('risk_factors') else '- None'}
"""
                if consistency_notes:
                    prompt += f"""

**consistency constraint**：
{chr(10).join('- ' + note for note in consistency_notes)}
"""
        
        # Add yesterday's comparison data
        if 'yesterday' in context:
            volume_change = context.get('volume_change_ratio', 'N/A')
            prompt += f"""
### Volume and price changes
- Changes in trading volume compared with yesterday：{volume_change}times
- Price changes from yesterday：{context.get('price_change_ratio', 'N/A')}%
"""
            parsed_volume_change = _safe_float(volume_change, default=math.nan)
            if math.isfinite(parsed_volume_change) and parsed_volume_change > 10:
                prompt += """
- ⚠️ Energy abnormality prompt：Trading volume increased by more than yesterday10times，Interpretation that must be reduced，Interpretation that must be reduced，It cannot be mechanically regarded as a strong confirmation signal.
"""
        
        # Add news search results（key areas）
        news_window_days: Optional[int] = None
        context_window = context.get("news_window_days")
        try:
            if context_window is not None:
                parsed_window = int(context_window)
                if parsed_window > 0:
                    news_window_days = parsed_window
        except (TypeError, ValueError):
            news_window_days = None

        if news_window_days is None:
            prompt_config = self._get_runtime_config()
            news_window_days = resolve_news_window_days(
                news_max_age_days=getattr(prompt_config, "news_max_age_days", 3),
                news_strategy_profile=getattr(prompt_config, "news_strategy_profile", "short"),
            )
        prompt += """
---

## 📰 public opinion intelligence
"""
        if news_context:
            prompt += f"""
The following is **{stock_name}({code})** close{news_window_days}News search results for the day，Please focus on extracting：
1. 🚨 **Risk alert**：Reduce holdings、punishment、Bad
2. 🎯 **Good catalyst**：performance、contract、policy
3. 📊 **performance expectations**：Annual report preview、Performance report
4. 🕒 **time rules（Output to）**：
   - Output to `risk_alerts` / `positive_catalysts` / `latest_news` Each entry must have a specific date（YYYY-MM-DD）
   - beyond near{news_window_days}News in the Japanese window will be ignored
   - Time unknown、News whose publication date cannot be determined will be ignored.

```
{news_context}
```
"""
        else:
            prompt += """
No recent news related to this stock was found.。missing data warning。
"""

        # Inject missing data warning
        if context.get('data_missing'):
            prompt += """
⚠️ **missing data warning**
Due to interface restrictions，Complete real-time market and technical indicator data are currently unavailable。
please **Ignore the N/A data**，Key basis **【📰 public opinion intelligence】** Conduct fundamental and emotional analysis of news in。
Answering technical questions（Such as moving average、deviation rate）hour，Please explain directly“missing data，Unable to judge”，**Fabricating data is strictly prohibited**。
"""

        # clear output requirements
        prompt += f"""
---

## ✅ Analysis tasks

please for **{stock_name}({code})** generate【Decision dashboard】，strictly follow JSON format output。
"""
        if context.get('is_index_etf'):
            prompt += """
> ⚠️ **index/ETF analysis constraints**：The subject is an index tracking type ETF or market index。
> - Risk analysis only focuses on：**Index trend、market liquidity、market liquidity**
> - It is strictly prohibited to bring lawsuits against fund companies、reputation、Executive changes included in risk alerts
> - Performance expectations are based on**Overall performance of index constituents**，Rather than fund company financial reports
> - `risk_alerts` There shall be no corporate operating risks related to the fund manager.

"""
        prompt += f"""
### ⚠️ important：Output the correct stock name format
The correct stock name format is“Stock name（Stock code）”，For example“Kweichow Moutai（600519）”。
If the stock name shown above is"stock{code}"or incorrect，Please start your analysis with**Clearly output the correct full Chinese name of the stock**。
"""
        if use_legacy_default_prompt:
            prompt += f"""

### focus on（Must answer clearly）：
1. ❓ Are you satisfied? MA5>MA10>MA20 multi-head arrangement？
2. ❓ Is the current deviation rate within a safe range?（<5%）？—— Exceed5%Must be marked"It is strictly forbidden to chase high"
3. ❓ Does the quantity and energy match?（Taper callback/Heavy volume breakthrough）？
4. ❓ Is the chip structure healthy?？
5. ❓ Is there any major negative news?？（Reduce holdings、punishment、Performance changes, etc.）
"""
        else:
            prompt += f"""

### focus on（Must answer clearly）：
1. ❓ Is the current entry position and risk reward reasonable?？
2. ❓ Is the current entry position and risk reward reasonable?？If the deviation is too large，Please clearly state the waiting conditions
3. ❓ chips、Do the fluctuations and chip structure support the current conclusion?？
4. ❓ Is there any information that is materially negative or conflicts with technical conclusions?？
5. ❓ If the conclusion is established，Specific trigger conditions、Stop loss level、What are the observation points?？
"""
        prompt += f"""

### Decision Dashboard Requirements：
- **Stock name**：The correct full Chinese name must be output（like"Kweichow Moutai"rather than"stock600519"）
- **Core conclusion**：In one sentence, it is clear whether you should buy it or not./Should sell/Such
- **Position classification suggestions**：What to do if you are short vs What do position holders do?
- **Bid price**：Bid price、Stop loss price、target price（Accurate to the minute）
- **Checklist**：Each item is used ✅/⚠️/❌ mark
- **Message surface time compliance**：`latest_news`、`risk_alerts`、`positive_catalysts` must not contain more than nearly{news_window_days}Information with unknown day or time
- **technical consistency**：Strictly prohibited“Short arrangement”and“multi-head arrangement”mutually exclusive conclusions simultaneously as valid evidence；If fundamentals/Conflict between event side and technical side，must be clearly written“Event first、Technology to be confirmed”or“Fundamentals are bullish，But the technical aspects have not yet been confirmed”
 
Please output the complete JSON Format Decision Dashboard。"""

        if report_language == "en":
            prompt += """

### Output language requirements (highest priority)
- Keep every JSON key exactly as defined above; do not translate keys.
- `decision_type` must remain `buy`, `hold`, or `sell`.
- All human-readable JSON values must be in English.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, all nested dashboard text, checklist items, and every summary field.
- Use the common English company name when you are confident. If not, keep the listed company name rather than inventing one.
- When data is missing, explain it in English instead of Chinese.
"""
        elif report_language == "ko":
            prompt += """

### Output language requirements (highest priority)
- Keep every JSON key exactly as defined above; do not translate keys.
- `decision_type` must remain `buy`, `hold`, or `sell`.
- All human-readable JSON values must be in Korean (한국어).
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, all nested dashboard text, checklist items, and every summary field.
- Use the common Korean or original listed company name when you are confident. If not, keep the listed company name rather than inventing one.
- When data is missing, explain it in Korean instead of Chinese.
"""
        else:
            prompt += f"""

### Output language requirements（highest priority）
- all JSON Key names must remain unchanged，Don't translate key names。
- `decision_type` must remain as `buy`、`hold`、`sell`。
- All user-facing human-readable text values ​​must be in Chinese。
- when data is missing，Please explain directly in Chinese“{no_data_text}，Unable to judge”。
"""
        
        return prompt
    
    def _format_volume(self, volume: Optional[float]) -> str:
        """Formatted turnover display"""
        if volume is None:
            return 'N/A'
        if volume >= 1e8:
            return f"{volume / 1e8:.2f} 100 million shares"
        elif volume >= 1e4:
            return f"{volume / 1e4:.2f} 10,000 shares"
        else:
            return f"{volume:.0f} shares"
    
    def _format_amount(self, amount: Optional[float]) -> str:
        """Formatted turnover display"""
        if amount is None:
            return 'N/A'
        if amount >= 1e8:
            return f"{amount / 1e8:.2f} billion"
        elif amount >= 1e4:
            return f"{amount / 1e4:.2f} Ten thousand yuan"
        else:
            return f"{amount:.0f} Yuan"

    def _format_percent(self, value: Optional[float]) -> str:
        """Format percentage display"""
        if value is None:
            return 'N/A'
        try:
            return f"{float(value):.2f}%"
        except (TypeError, ValueError):
            return 'N/A'

    def _format_price(self, value: Optional[float]) -> str:
        """Format price display"""
        if value is None:
            return 'N/A'
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return 'N/A'

    def _build_market_snapshot(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Construct a snapshot of the day’s market trends（for display）"""
        today = context.get('today', {}) or {}
        realtime = context.get('realtime', {}) or {}
        yesterday = context.get('yesterday', {}) or {}

        prev_close = yesterday.get('close')
        close = today.get('close')
        high = today.get('high')
        low = today.get('low')

        amplitude = None
        change_amount = None
        if prev_close not in (None, 0) and high is not None and low is not None:
            try:
                amplitude = (float(high) - float(low)) / float(prev_close) * 100
            except (TypeError, ValueError, ZeroDivisionError):
                amplitude = None
        if prev_close is not None and close is not None:
            try:
                change_amount = float(close) - float(prev_close)
            except (TypeError, ValueError):
                change_amount = None

        snapshot = {
            "date": context.get('date', 'unknown'),
            "close": self._format_price(close),
            "open": self._format_price(today.get('open')),
            "high": self._format_price(high),
            "low": self._format_price(low),
            "prev_close": self._format_price(prev_close),
            "pct_chg": self._format_percent(today.get('pct_chg')),
            "change_amount": self._format_price(change_amount),
            "amplitude": self._format_percent(amplitude),
            "volume": self._format_volume(today.get('volume')),
            "amount": self._format_amount(today.get('amount')),
        }

        if realtime:
            snapshot.update({
                "price": self._format_price(realtime.get('price')),
                "volume_ratio": realtime.get('volume_ratio', 'N/A'),
                "turnover_rate": self._format_percent(realtime.get('turnover_rate')),
                "source": getattr(realtime.get('source'), 'value', realtime.get('source', 'N/A')),
            })

        return snapshot

    def _check_content_integrity(
        self,
        result: AnalysisResult,
        *,
        require_phase_decision: bool = False,
    ) -> Tuple[bool, List[str]]:
        """Delegate to module-level check_content_integrity."""
        return check_content_integrity(result, require_phase_decision=require_phase_decision)

    def _build_integrity_complement_prompt(self, missing_fields: List[str], report_language: str = "zh") -> str:
        """Build complement instruction for missing mandatory fields."""
        report_language = normalize_report_language(report_language)
        if report_language in ("en", "ko"):
            lines = ["### Completion requirements: fill the missing mandatory fields below and output the full JSON again:"]
            for f in missing_fields:
                if f == "sentiment_score":
                    lines.append("- sentiment_score: integer score from 0 to 100")
                elif f == "operation_advice":
                    lines.append("- operation_advice: localized action advice")
                elif f == "analysis_summary":
                    lines.append("- analysis_summary: concise analysis summary")
                elif f == "dashboard.core_conclusion.one_sentence":
                    lines.append("- dashboard.core_conclusion.one_sentence: one-line decision")
                elif f == "dashboard.intelligence.risk_alerts":
                    lines.append("- dashboard.intelligence.risk_alerts: risk alert list (can be empty)")
                elif f == "dashboard.battle_plan.sniper_points.stop_loss":
                    lines.append("- dashboard.battle_plan.sniper_points.stop_loss: stop-loss level")
                elif f == "dashboard.phase_decision.phase_context":
                    lines.append("- dashboard.phase_decision.phase_context: public market phase summary subset")
                elif f == "dashboard.phase_decision.action_window":
                    lines.append("- dashboard.phase_decision.action_window: phase-aware action window")
                elif f == "dashboard.phase_decision.immediate_action":
                    lines.append("- dashboard.phase_decision.immediate_action: act now / wait / watch / no intraday action")
                elif f == "dashboard.phase_decision.watch_conditions":
                    lines.append("- dashboard.phase_decision.watch_conditions: list of watch conditions")
                elif f == "dashboard.phase_decision.next_check_time":
                    lines.append("- dashboard.phase_decision.next_check_time: next check point or market-local time")
                elif f == "dashboard.phase_decision.confidence_reason":
                    lines.append("- dashboard.phase_decision.confidence_reason: confidence rationale and data limits")
                elif f == "dashboard.phase_decision.data_limitations":
                    lines.append("- dashboard.phase_decision.data_limitations: list of phase/data quality limitations")
            return "\n".join(lines)

        lines = ["### Completion requirements：Please add the following required content based on the above analysis.，and output complete JSON："]
        for f in missing_fields:
            if f == "sentiment_score":
                lines.append("- sentiment_score: 0-100 Overall rating")
            elif f == "operation_advice":
                lines.append("- operation_advice: Buy/Add to position/hold/Reduce positions/sell/wait and see")
            elif f == "analysis_summary":
                lines.append("- analysis_summary: Comprehensive analysis summary")
            elif f == "dashboard.core_conclusion.one_sentence":
                lines.append("- dashboard.core_conclusion.one_sentence: One sentence decision")
            elif f == "dashboard.intelligence.risk_alerts":
                lines.append("- dashboard.intelligence.risk_alerts: Risk alert list（nullable array）")
            elif f == "dashboard.battle_plan.sniper_points.stop_loss":
                lines.append("- dashboard.battle_plan.sniper_points.stop_loss: Stop loss price")
            elif f == "dashboard.phase_decision.phase_context":
                lines.append("- dashboard.phase_decision.phase_context: Publicly available hypoallergenic market stage summary subsets")
            elif f == "dashboard.phase_decision.action_window":
                lines.append("- dashboard.phase_decision.action_window: Staged action window")
            elif f == "dashboard.phase_decision.immediate_action":
                lines.append("- dashboard.phase_decision.immediate_action: Act now/Waiting for confirmation/observe/No intraday action")
            elif f == "dashboard.phase_decision.watch_conditions":
                lines.append("- dashboard.phase_decision.watch_conditions: Observation condition array")
            elif f == "dashboard.phase_decision.next_check_time":
                lines.append("- dashboard.phase_decision.next_check_time: Next checkpoint or market local time")
            elif f == "dashboard.phase_decision.confidence_reason":
                lines.append("- dashboard.phase_decision.confidence_reason: Confidence reasons and data limitations")
            elif f == "dashboard.phase_decision.data_limitations":
                lines.append("- dashboard.phase_decision.data_limitations: stage/Data quality limit array")
        return "\n".join(lines)

    def _build_integrity_retry_prompt(
        self,
        base_prompt: str,
        previous_response: str,
        missing_fields: List[str],
        report_language: str = "zh",
    ) -> str:
        """Build retry prompt using the previous response as the complement baseline."""
        complement = self._build_integrity_complement_prompt(missing_fields, report_language=report_language)
        previous_output = previous_response.strip()
        if normalize_report_language(report_language) in ("en", "ko"):
            prefix = "### The previous output is below. Complete the missing fields based on that output and return the full JSON again. Do not omit existing fields:"
        else:
            prefix = "### The last output was as follows，Please fill in the missing fields based on this output，and re-output the complete JSON。Don't omit existing fields："
        return "\n\n".join([
            base_prompt,
            prefix,
            previous_output,
            complement,
        ])

    def _apply_placeholder_fill(self, result: AnalysisResult, missing_fields: List[str]) -> None:
        """Delegate to module-level apply_placeholder_fill."""
        apply_placeholder_fill(result, missing_fields)

    def _extract_analysis_json_object(self, response_text: str) -> Tuple[str, Dict[str, Any]]:
        """Extract the single allowed JSON object from an LLM response."""

        text = response_text or ""
        stripped = text.strip()
        if not stripped:
            raise ValueError("empty_response")

        fence_pattern = re.compile(
            r"```[ \t]*(?P<lang>[A-Za-z0-9_-]*)[ \t]*\n?(?P<body>.*?)```",
            flags=re.DOTALL,
        )
        fenced_matches = list(fence_pattern.finditer(text))
        if len(fenced_matches) > 1:
            raise ValueError("ambiguous_json")
        if len(fenced_matches) == 1:
            match = fenced_matches[0]
            outside = (text[:match.start()] + text[match.end():]).strip()
            if outside:
                raise ValueError("ambiguous_json")
            fence_lang = (match.group("lang") or "").strip().lower()
            if fence_lang not in {"", "json"}:
                raise ValueError("ambiguous_json")
            json_str = match.group("body").strip()
            data = self._load_analysis_json_candidate(json_str)
            return json_str, data
        if "```" in text:
            raise ValueError("ambiguous_json")

        try:
            data = self._load_analysis_json_candidate(stripped)
        except json.JSONDecodeError as exc:
            if self._contains_embedded_json_object(text):
                raise ValueError("ambiguous_json") from exc
            raise
        return stripped, data

    def _load_analysis_json_candidate(self, json_str: str) -> Dict[str, Any]:
        """Parse one already-selected JSON candidate, repairing common LLM JSON drift."""
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            stripped = (json_str or "").strip()
            try:
                _obj, end = json.JSONDecoder().raw_decode(stripped)
            except json.JSONDecodeError:
                pass
            else:
                if stripped[end:].strip():
                    raise
            if not (stripped.startswith("{") and stripped.endswith("}")):
                raise
            repaired = self._fix_json_string(stripped)
            data = json.loads(repaired)
        if not isinstance(data, dict):
            raise TypeError("json_root_not_object")
        return data

    @staticmethod
    def _contains_embedded_json_object(text: str) -> bool:
        decoder = json.JSONDecoder()
        count = 0
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                _obj, end = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            count += 1
            before = text[:index].strip()
            after = text[index + end:].strip()
            if count > 1 or before or after:
                return True
        return False

    def _validate_analysis_minimal_contract(self, data: Dict[str, Any]) -> None:
        try:
            AnalysisReportSchema.model_validate(data)
        except Exception as exc:
            logger.warning(
                "AnalysisReportSchema validation failed; continuing with raw parser contract: %s",
                str(exc)[:200],
            )
        minimal_keys = {
            "sentiment_score",
            "trend_prediction",
            "operation_advice",
            "analysis_summary",
            "dashboard",
        }
        if not any(key in data for key in minimal_keys):
            raise self._generation_validation_error(
                GenerationErrorCode.SCHEMA_VALIDATION_FAILED,
                reason="minimal_contract_failed",
                message="analysis JSON does not contain any minimal parser field",
            )
        if "sentiment_score" in data:
            try:
                int(data.get("sentiment_score", 50))
            except (TypeError, ValueError) as exc:
                raise self._generation_validation_error(
                    GenerationErrorCode.SCHEMA_VALIDATION_FAILED,
                    reason="parser_contract_failed",
                    message="sentiment_score must be integer-compatible",
                ) from exc

    def _generation_validation_error(
        self,
        error_code: GenerationErrorCode,
        *,
        reason: str,
        message: str,
    ) -> GenerationError:
        try:
            backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
        except GenerationError:
            backend_id = "generation_backend"
        return GenerationError(
            error_code=error_code,
            stage="validation",
            retryable=True,
            fallbackable=True,
            backend=backend_id,
            provider=backend_id,
            details={
                "reason": reason,
                "message": message,
            },
        )

    def _parse_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """
        parse Gemini response（Decision dashboard version）
        
        Try to extract from the response JSON format analysis results，Include dashboard If parsing fails
        If parsing fails，Try smart extraction or return default results
        """
        try:
            report_language = normalize_report_language(
                getattr(self._get_runtime_config(), "report_language", "zh")
            )
            try:
                _json_str, data = self._extract_analysis_json_object(response_text)
                self._validate_analysis_minimal_contract(data)
            except Exception as exc:
                logger.warning("Unable to extract unique valid from response JSON，Marked as parsing failure: %s", exc)
                return self._parse_text_response(response_text, code, name)

            # extract dashboard data
            dashboard = data.get('dashboard', None)
            guardrail_reason = data.get("guardrail_reason") or data.get("downgrade_reason")
            if guardrail_reason and isinstance(dashboard, dict):
                score_calibration = dashboard.get("decision_score_calibration")
                if not isinstance(score_calibration, dict):
                    score_calibration = {}
                    dashboard["decision_score_calibration"] = score_calibration
                score_calibration.setdefault("guardrail_reason", str(guardrail_reason).strip())
            # normalization signal_attribution（LLM May return string/negative number/sum≠100）
            normalize_report_signal_attribution(dashboard)

            # priority use AI Returned stock name（If the original name is invalid or contains code）
            ai_stock_name = data.get('stock_name')
            if ai_stock_name and (name.startswith('stocks') or name == code or 'Unknown' in name):
                name = ai_stock_name

            # Parse all fields，Use default values ​​to prevent missing
            # parse decision_type，If not then based on operation_advice infer
            decision_type = data.get('decision_type', '')
            if not decision_type:
                op = data.get('operation_advice', localize_operation_advice('hold', report_language))
                decision_type = infer_decision_type_from_advice(op, default='hold')

            explicit_action = data.get("action")
            if explicit_action is None and isinstance(dashboard, dict):
                explicit_action = dashboard.get("action")

            result = AnalysisResult(
                code=code,
                name=name,
                # core indicators
                sentiment_score=int(data.get('sentiment_score', 50)),
                trend_prediction=data.get('trend_prediction', localize_trend_prediction('shock', report_language)),
                operation_advice=data.get('operation_advice', localize_operation_advice('hold', report_language)),
                decision_type=decision_type,
                confidence_level=localize_confidence_level(
                    data.get('confidence_level', localize_confidence_level('in', report_language)),
                    report_language,
                ),
                report_language=report_language,
                # Decision dashboard
                dashboard=dashboard,
                # Technical analysis
                trend_analysis=data.get('trend_analysis', ''),
                short_term_outlook=data.get('short_term_outlook', ''),
                medium_term_outlook=data.get('medium_term_outlook', ''),
                # technical aspect
                technical_analysis=data.get('technical_analysis', ''),
                ma_analysis=data.get('ma_analysis', ''),
                volume_analysis=data.get('volume_analysis', ''),
                pattern_analysis=data.get('pattern_analysis', ''),
                # Fundamentals
                fundamental_analysis=data.get('fundamental_analysis', ''),
                sector_position=data.get('sector_position', ''),
                company_highlights=data.get('company_highlights', ''),
                # Emotional side/news side
                news_summary=data.get('news_summary', ''),
                market_sentiment=data.get('market_sentiment', ''),
                hot_topics=data.get('hot_topics', ''),
                # comprehensive
                analysis_summary=data.get('analysis_summary', _localized_text(
                    report_language, en='Analysis completed', zh='Analysis completed', ko='분석 완료')),
                key_points=data.get('key_points', ''),
                risk_warning=data.get('risk_warning', ''),
                buy_reason=data.get('buy_reason', ''),
                # metadata
                search_performed=data.get('search_performed', False),
                data_sources=data.get('data_sources', _localized_text(
                    report_language, en='Technical data', zh='Technical data', ko='기술적 데이터')),
                success=True,
            )
            return populate_decision_action_fields(
                result,
                explicit_action=explicit_action,
                align_with_score=False,
            )
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON Parsing failed: {e}，Marked as parsing failure")
            return self._parse_text_response(response_text, code, name)
    
    def _fix_json_string(self, json_str: str) -> str:
        """Fix common JSON Format problem"""
        import re
        
        # Remove comments
        json_str = re.sub(r'//.*?\n', '\n', json_str)
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
        
        # Fix trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Make sure boolean values ​​are lowercase
        json_str = json_str.replace('True', 'true').replace('False', 'false')
        
        # fix by json-repair
        json_str = repair_json(json_str)
        
        return json_str

    def _validate_json_response(self, text: str) -> None:
        """Validate that *text* contains one parser-compatible JSON object.

        Used as the ``response_validator`` argument to :meth:`_call_litellm` so
        that a JSON-less or unparseable reply from the primary model is treated
        as a model failure and triggers fallback to the next configured model.

        Raises:
            GenerationError: if the response has no unique parser-compatible
                JSON object, the selected JSON candidate cannot be parsed, or
                the parsed object cannot satisfy the minimal parser contract.
        """
        try:
            _json_str, data = self._extract_analysis_json_object(text)
        except ValueError as exc:
            reason = str(exc) or "invalid_json"
            if reason == "ambiguous_json":
                message = "JSON source is ambiguous"
            else:
                message = "No unique JSON object found in LLM response"
            raise self._generation_validation_error(
                GenerationErrorCode.INVALID_JSON,
                reason=reason,
                message=message,
            ) from exc
        except json.JSONDecodeError as exc:
            raise self._generation_validation_error(
                GenerationErrorCode.INVALID_JSON,
                reason="invalid_json",
                message=str(exc)[:200],
            ) from exc
        except Exception as exc:
            raise self._generation_validation_error(
                GenerationErrorCode.INVALID_JSON,
                reason="invalid_json",
                message=str(exc)[:200],
            ) from exc

        self._validate_analysis_minimal_contract(data)
    
    def _parse_text_response(
        self, 
        response_text: str, 
        code: str, 
        name: str
    ) -> AnalysisResult:
        """to avoid"""
        report_language = normalize_report_language(
            getattr(self._get_runtime_config(), "report_language", "zh")
        )
        # Try to identify keywords to determine sentiment
        sentiment_score = 50
        trend = localize_trend_prediction('shock', report_language)
        advice = localize_operation_advice('hold', report_language)
        
        text_lower = response_text.lower()
        
        # Simple emotion recognition
        positive_keywords = ['long', 'Buy', 'rise', 'breakthrough', 'Strong', 'good', 'Add to position', 'bullish', 'buy']
        negative_keywords = ['bearish', 'sell', 'fall', 'fell below', 'Weak', 'Bad', 'Reduce positions', 'bearish', 'sell']
        
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if positive_count > negative_count + 1:
            sentiment_score = 65
            trend = localize_trend_prediction('long', report_language)
            advice = localize_operation_advice('Buy', report_language)
            decision_type = 'buy'
        elif negative_count > positive_count + 1:
            sentiment_score = 35
            trend = localize_trend_prediction('bearish', report_language)
            advice = localize_operation_advice('sell', report_language)
            decision_type = 'sell'
        else:
            decision_type = 'hold'
        
        # before interception500characters as summary
        summary = response_text[:500] if response_text else _localized_text(
            report_language, en='No analysis result', zh='No analysis results', ko='분석 결과 없음')
        
        result = AnalysisResult(
            code=code,
            name=name,
            sentiment_score=sentiment_score,
            trend_prediction=trend,
            operation_advice=advice,
            decision_type=decision_type,
            confidence_level=localize_confidence_level('low', report_language),
            analysis_summary=summary,
            key_points=_localized_text(
                report_language,
                en='JSON parsing failed; treat this as best-effort output.',
                zh='JSONParsing failed，For reference only',
                ko='JSON 파싱에 실패했습니다. 참고용으로만 사용하세요.',
            ),
            risk_warning=_localized_text(
                report_language,
                en='The result may be inaccurate. Cross-check with other information.',
                zh='Analysis results may be inaccurate，It is recommended to judge based on other information',
                ko='결과가 부정확할 수 있습니다. 다른 정보와 교차 확인하세요.',
            ),
            raw_response=response_text,
            success=False,
            error_message='LLM response is not valid JSON; analysis result will not be persisted',
            report_language=report_language,
        )
        return populate_decision_action_fields(result, align_with_score=False)
    
    def batch_analyze(
        self, 
        contexts: List[Dict[str, Any]],
        delay_between: float = 2.0
    ) -> List[AnalysisResult]:
        """
        to avoid
        
        Notice：to avoid API rate limit，There will be a delay between each analysis
        
        Args:
            contexts: context data list
            delay_between: Delay between each analysis（Second）
            
        Returns:
            AnalysisResult list
        """
        results = []
        
        for i, context in enumerate(contexts):
            if i > 0:
                logger.debug(f"wait {delay_between} Continue in seconds...")
                time.sleep(delay_between)
            
            result = self.analyze(context)
            results.append(result)
        
        return results


# Convenience function
def get_analyzer() -> GeminiAnalyzer:
    """get LLM Analyzer instance"""
    return GeminiAnalyzer()


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.DEBUG)
    
    # Simulate context data
    test_context = {
        'code': '600519',
        'date': '2026-01-09',
        'today': {
            'open': 1800.0,
            'high': 1850.0,
            'low': 1780.0,
            'close': 1820.0,
            'volume': 10000000,
            'amount': 18200000000,
            'pct_chg': 1.5,
            'ma5': 1810.0,
            'ma10': 1800.0,
            'ma20': 1790.0,
            'volume_ratio': 1.2,
        },
        'ma_status': 'multi-head arrangement 📈',
        'volume_change_ratio': 1.3,
        'price_change_ratio': 1.5,
    }
    
    analyzer = GeminiAnalyzer()
    
    if analyzer.is_available():
        print("=== AI Analytical testing ===")
        result = analyzer.analyze(test_context)
        print(f"Analyze results: {result.to_dict()}")
    else:
        print("Gemini API Not configured，skip test")
