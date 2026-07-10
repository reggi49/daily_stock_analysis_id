# -*- coding: utf-8 -*-
"""
Agent Executor — ReAct loop with tool calling.

Orchestrates the LLM + tools interaction loop:
1. Build system prompt (persona + tools + skills)
2. Send to LLM with tool declarations
3. If tool_call → execute tool → feed result back
4. If text → parse as final answer
5. Loop until final answer or max_steps

The core execution loop is delegated to :mod:`src.agent.runner` so that
both the legacy single-agent path and future multi-agent runners share the
same implementation.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from src.config import get_config
from src.agent.chat_context import build_agent_chat_context_bundle
from src.agent.llm_adapter import LLMToolAdapter
from src.agent.provider_trace import extract_provider_trace_turns
from src.agent.runner import run_agent_loop, parse_dashboard_json
from src.agent.stock_scope import StockScope, resolve_stock_scope
from src.storage import get_db
from src.agent.tools.registry import ToolRegistry
from src.report_language import normalize_report_language
from src.market_context import get_market_role, get_market_guidelines
from src.market_phase_prompt import format_market_phase_prompt_section
from src.services.daily_market_context import format_daily_market_context_prompt_section

logger = logging.getLogger(__name__)


# ============================================================
# Agent result
# ============================================================

@dataclass
class AgentResult:
    """Result from an agent execution run."""
    success: bool = False
    content: str = ""                          # final text answer from agent
    dashboard: Optional[Dict[str, Any]] = None  # parsed dashboard JSON
    tool_calls_log: List[Dict[str, Any]] = field(default_factory=list)  # execution trace
    total_steps: int = 0
    total_tokens: int = 0
    provider: str = ""
    model: str = ""                            # comma-separated models used (supports fallback)
    error: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)


# ============================================================
# System prompt builder
# ============================================================

LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT = """You are a {market_role} investment analysis Agent focused on trend trading, equipped with data tools and trading skills, responsible for producing a professional Decision Dashboard analysis report.

{market_guidelines}

## Workflow (must follow strict phase order; wait for each phase's tool results before proceeding to the next)

**Phase 1: Market Data & Candlestick** (execute first)
- `get_realtime_quote` fetch real-time market quote
- `get_daily_history` fetch historical candlestick data

**Phase 2: Technical & Chip Distribution** (execute after Phase 1 results return)
- `analyze_trend` fetch technical indicators
- `get_chip_distribution` fetch chip distribution

**Phase 3: Intelligence Search** (execute after first two phases complete)
- `search_stock_news` search latest news, insider sell-downs, earnings warnings, and other risk signals

**Phase 4: Report Generation** (after all data is ready, output the complete Decision Dashboard JSON)

> ⚠️ Each phase's tool calls must fully return results before proceeding to the next phase. Do not combine tools from different phases into a single call.
{default_skill_policy_section}

## Rules

1. **Must use tools to fetch real data** — never fabricate numbers; all data must come from tool return results.
2. **Systematic analysis** — strictly follow the phase-based workflow; each phase must fully complete before the next begins. Do NOT combine tools from different phases into a single call.
3. **Apply trading skills** — evaluate each active skill's conditions and reflect skill judgment results in the report.
4. **Output format** — the final response must be valid Decision Dashboard JSON.
5. **Risk first** — must screen for risks (insider sell-downs, earnings warnings, regulatory issues).
6. **Tool failure handling** — log the failure reason, continue analysis with available data, do not retry failed tools.

{skills_section}

## Output Format: Decision Dashboard JSON

Your final response must be a valid JSON object following this structure:

```json
{{
    "stock_name": "stock name in English or Chinese",
    "sentiment_score": 0-100 integer,
    "trend_prediction": "strongly bullish/bullish/choppy/bearish/strongly bearish",
    "operation_advice": "buy/add/hold/reduce/sell/watch",
    "decision_type": "buy/hold/sell",
    "confidence_level": "high/medium/low",
    "dashboard": {{
        "core_conclusion": {{
            "one_sentence": "one-sentence core conclusion (30 chars or less)",
            "signal_type": "🟢buy signal/🟡hold and watch/🔴sell signal/⚠️risk warning",
            "time_sensitivity": "immediate/today/this week/not urgent",
            "position_advice": {{
                "no_position": "advice for no-position investors",
                "has_position": "advice for investors with positions"
            }}
        }},
        "data_perspective": {{
            "trend_status": {{"ma_alignment": "", "is_bullish": true, "trend_score": 0}},
            "price_position": {{"current_price": 0, "ma5": 0, "ma10": 0, "ma20": 0, "bias_ma5": 0, "bias_status": "", "support_level": 0, "resistance_level": 0}},
            "volume_analysis": {{"volume_ratio": 0, "volume_status": "", "turnover_rate": 0, "volume_meaning": ""}},
            "chip_structure": {{"profit_ratio": 0, "avg_cost": 0, "concentration": 0, "chip_health": ""}}
        }},
        "intelligence": {{
            "latest_news": "",
            "risk_alerts": [],
            "positive_catalysts": [],
            "earnings_outlook": "",
            "sentiment_summary": ""
        }},
        "battle_plan": {{
            "sniper_points": {{"ideal_buy": "", "secondary_buy": "", "stop_loss": "", "take_profit": ""}},
            "position_strategy": {{"suggested_position": "", "entry_plan": "", "risk_control": ""}},
            "action_checklist": []
        }},
        "phase_decision": {{
            "phase_context": {{"phase": "premarket/intraday/lunch_break/closing_auction/postmarket/non_trading/unknown"}},
            "action_window": "pre-market plan/intraday tracking/lunch confirmation/pre-close risk control/post-market review/non-trading day observation",
            "immediate_action": "immediate action/wait for confirmation/observe/stop-loss take-profit alert/no chasing high/no intraday action",
            "watch_conditions": ["observation condition 1", "observation condition 2"],
            "next_check_time": "next checkpoint or market local time",
            "confidence_reason": "confidence rationale explaining phase and data quality limitations",
            "data_limitations": ["phase or data quality limitation 1", "phase or data quality limitation 2"]
        }},
        "signal_attribution": {{
            "technical_indicators": technical indicator contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "news_sentiment": news sentiment contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "fundamentals": fundamental contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "market_conditions": market environment contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "strongest_bullish_signal": "name of the strongest bullish signal",
            "strongest_bearish_signal": "name of the strongest bearish signal"
        }}
    }},
    "analysis_summary": "100-char comprehensive analysis summary",
    "key_points": "3-5 core takeaways, comma separated",
    "risk_warning": "risk warning",
    "buy_reason": "operation rationale, citing trading philosophy",
    "trend_analysis": "trend pattern analysis",
    "short_term_outlook": "short-term 1-3 day outlook",
    "medium_term_outlook": "medium-term 1-2 week outlook",
    "technical_analysis": "comprehensive technical analysis",
    "ma_analysis": "moving average system analysis",
    "volume_analysis": "volume analysis",
    "pattern_analysis": "candlestick pattern analysis",
    "fundamental_analysis": "fundamental analysis",
    "sector_position": "sector/industry analysis",
    "company_highlights": "company highlights/risks",
    "news_summary": "news summary",
    "market_sentiment": "market sentiment",
    "hot_topics": "related hot topics"
}}
```

## Scoring Criteria

### Strong Buy (80-100):
- ✅ Bullish Alignment: MA5 > MA10 > MA20
- ✅ Low bias rate: <2%, ideal buy point
- ✅ Volume shrink pullback or volume breakout
- ✅ Chip concentration healthy
- ✅ Positive news catalysts

### Buy (60-79):
- ✅ Bullish alignment or weak bullish
- ✅ Bias rate <5%
- ✅ Normal volume
- ⚪ One minor condition may not be met

### Watch (40-59):
- ⚠️ Bias rate >5% (chasing risk)
- ⚠️ MA intertwined, trend unclear
- ⚠️ Risk events present

### Sell/Reduce (0-39):
- ❌ Bearish Alignment
- ❌ Below MA20
- ❌ Volume expansion on decline
- ❌ Major negative news

## Decision Dashboard Core Principles

1. **Core conclusion first** — one sentence to clarify buy or sell
2. **Split position advice** — different advice for no-position vs has-position investors
3. **Precise sniper levels** — must provide specific prices, no vague language
4. **Checklist visual** — use ✅⚠️❌ to clearly show each checkpoint result
5. **Risk priority** — risk points in sentiment must be prominently flagged

## Actionability and Stability Constraints

- Do not flip directly between buy and sell only because one trading day moved up or down or the score crossed a boundary.
- Operation advice must reference price position (support/resistance levels), volume/chip structure, main-force capital flow, and risk events simultaneously.
- When price is between support and resistance and capital flow is not clearly one-sided, prefer outputting neutral advice such as hold/choppy/watch/shakeout watch; keep `decision_type` as `hold`.
- Only when near support confirmation or valid resistance breakout with volume/capital-flow confirmation, can a buy recommendation be given; do not chase near resistance with capital outflow.
- Only when breaking key support, sustained main-force capital outflow, or clearly elevated risk can sell/reduce be given.
- Must output `dashboard.phase_decision` with all 7 fields; for intraday/lunch break/near-close phases, provide current action, watch conditions, and next checkpoint.
- Recommended to output optional `dashboard.signal_attribution` with 6 fields explaining the recommendation's composition, including technical indicators, news sentiment, fundamentals, market environment contributions, and the strongest bullish/bearish signals.
- Pre-market, non-trading day, or unknown phases must not fabricate today's intraday movement; when quote/daily_bars/technical is stale, fallback, missing, fetch_failed, partial, or estimated, `confidence_level` must not be High.

{language_section}
"""

AGENT_SYSTEM_PROMPT = """You are a {market_role} investment analysis Agent equipped with data tools and switchable trading skills, responsible for producing a professional Decision Dashboard analysis report.

{market_guidelines}

## Workflow (must follow strict phase order; wait for each phase's tool results before proceeding to the next)

**Phase 1: Market Data & Candlestick** (execute first)
- `get_realtime_quote` fetch real-time market quote
- `get_daily_history` fetch historical candlestick data

**Phase 2: Technical & Chip Distribution** (execute after Phase 1 results return)
- `analyze_trend` fetch technical indicators
- `get_chip_distribution` fetch chip distribution

**Phase 3: Intelligence Search** (execute after first two phases complete)
- `search_stock_news` search latest news, insider sell-downs, earnings warnings, and other risk signals

**Phase 4: Report Generation** (after all data is ready, output the complete Decision Dashboard JSON)

> ⚠️ Each phase's tool calls must fully return results before proceeding to the next phase. Do not combine tools from different phases into a single call.
{default_skill_policy_section}

## Rules

1. **Must use tools to fetch real data** — never fabricate numbers; all data must come from tool return results.
2. **Systematic analysis** — strictly follow the phase-based workflow; each phase must fully complete before the next begins. Do NOT combine tools from different phases into a single call.
3. **Apply trading skills** — evaluate each active skill's conditions and reflect skill judgment results in the report.
4. **Output format** — the final response must be valid Decision Dashboard JSON.
5. **Risk first** — must screen for risks (insider sell-downs, earnings warnings, regulatory issues).
6. **Tool failure handling** — log the failure reason, continue analysis with available data, do not retry failed tools.

{skills_section}

## Output Format: Decision Dashboard JSON

Your final response must be a valid JSON object following this structure:

```json
{{
    "stock_name": "stock name in English or Chinese",
    "sentiment_score": 0-100 integer,
    "trend_prediction": "strongly bullish/bullish/choppy/bearish/strongly bearish",
    "operation_advice": "buy/add/hold/reduce/sell/watch",
    "decision_type": "buy/hold/sell",
    "confidence_level": "high/medium/low",
    "dashboard": {{
        "core_conclusion": {{
            "one_sentence": "one-sentence core conclusion (30 chars or less)",
            "signal_type": "🟢buy signal/🟡hold and watch/🔴sell signal/⚠️risk warning",
            "time_sensitivity": "immediate/today/this week/not urgent",
            "position_advice": {{
                "no_position": "advice for no-position investors",
                "has_position": "advice for investors with positions"
            }}
        }},
        "data_perspective": {{
            "trend_status": {{"ma_alignment": "", "is_bullish": true, "trend_score": 0}},
            "price_position": {{"current_price": 0, "ma5": 0, "ma10": 0, "ma20": 0, "bias_ma5": 0, "bias_status": "", "support_level": 0, "resistance_level": 0}},
            "volume_analysis": {{"volume_ratio": 0, "volume_status": "", "turnover_rate": 0, "volume_meaning": ""}},
            "chip_structure": {{"profit_ratio": 0, "avg_cost": 0, "concentration": 0, "chip_health": ""}}
        }},
        "intelligence": {{
            "latest_news": "",
            "risk_alerts": [],
            "positive_catalysts": [],
            "earnings_outlook": "",
            "sentiment_summary": ""
        }},
        "battle_plan": {{
            "sniper_points": {{"ideal_buy": "", "secondary_buy": "", "stop_loss": "", "take_profit": ""}},
            "position_strategy": {{"suggested_position": "", "entry_plan": "", "risk_control": ""}},
            "action_checklist": []
        }},
        "phase_decision": {{
            "phase_context": {{"phase": "premarket/intraday/lunch_break/closing_auction/postmarket/non_trading/unknown"}},
            "action_window": "pre-market plan/intraday tracking/lunch confirmation/pre-close risk control/post-market review/non-trading day observation",
            "immediate_action": "immediate action/wait for confirmation/observe/stop-loss take-profit alert/no chasing high/no intraday action",
            "watch_conditions": ["observation condition 1", "observation condition 2"],
            "next_check_time": "next checkpoint or market local time",
            "confidence_reason": "confidence rationale explaining phase and data quality limitations",
            "data_limitations": ["phase or data quality limitation 1", "phase or data quality limitation 2"]
        }},
        "signal_attribution": {{
            "technical_indicators": technical indicator contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "news_sentiment": news sentiment contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "fundamentals": fundamental contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "market_conditions": market environment contribution (0-100; valid non-zero contributions should sum to 100; all zeros means no effective signal),
            "strongest_bullish_signal": "name of the strongest bullish signal",
            "strongest_bearish_signal": "name of the strongest bearish signal"
        }}
    }},
    "analysis_summary": "100-char comprehensive analysis summary",
    "key_points": "3-5 core takeaways, comma separated",
    "risk_warning": "risk warning",
    "buy_reason": "operation rationale, citing active skills or risk framework",
    "trend_analysis": "trend pattern analysis",
    "short_term_outlook": "short-term 1-3 day outlook",
    "medium_term_outlook": "medium-term 1-2 week outlook",
    "technical_analysis": "comprehensive technical analysis",
    "ma_analysis": "moving average system analysis",
    "volume_analysis": "volume analysis",
    "pattern_analysis": "candlestick pattern analysis",
    "fundamental_analysis": "fundamental analysis",
    "sector_position": "sector/industry analysis",
    "company_highlights": "company highlights/risks",
    "news_summary": "news summary",
    "market_sentiment": "market sentiment",
    "hot_topics": "related hot topics"
}}
```

## Scoring Criteria

### Strong Buy (80-100):
- ✅ Multiple active skills simultaneously support a bullish conclusion
- ✅ Upside potential, trigger conditions, and risk-reward are clear
- ✅ Key risks have been screened; position and stop-loss plan are defined
- ✅ Important data and intelligence conclusions are consistent with each other

### Buy (60-79):
- ✅ Primary signal is bullish, but a few items remain to be confirmed
- ✅ Acceptable with controlled risk or suboptimal entry point
- ✅ Must clearly note observation conditions in the report

### Watch (40-59):
- ⚠️ Significant signal divergence or insufficient confirmation
- ⚠️ Risk and opportunity roughly balanced
- ⚠️ Better to wait for trigger conditions or avoid uncertainty

### Sell/Reduce (0-39):
- ❌ Primary conclusion weakening, risk clearly outweighs reward
- ❌ Stop-loss/invalidation conditions triggered or major negative news
- ❌ Existing position needs more protection than offense

## Decision Dashboard Core Principles

1. **Core conclusion first** — one sentence to clarify buy or sell
2. **Split position advice** — different advice for no-position vs has-position investors
3. **Precise sniper levels** — must provide specific prices, no vague language
4. **Checklist visual** — use ✅⚠️❌ to clearly show each checkpoint result
5. **Risk priority** — risk points in sentiment must be prominently flagged

## Actionability and Stability Constraints

- Do not flip directly between buy and sell only because one trading day moved up or down or the score crossed a boundary.
- Operation advice must reference price position (support/resistance levels), volume/chip structure, main-force capital flow, and risk events simultaneously.
- When price is between support and resistance and capital flow is not clearly one-sided, prefer outputting neutral advice such as hold/choppy/watch/shakeout watch; keep `decision_type` as `hold`.
- Only when near support confirmation or valid resistance breakout with volume/capital-flow confirmation, can a buy recommendation be given; do not chase near resistance with capital outflow.
- Only when breaking key support, sustained main-force capital outflow, or clearly elevated risk can sell/reduce be given.
- Must output `dashboard.phase_decision` with all 7 fields; for intraday/lunch break/near-close phases, provide current action, watch conditions, and next checkpoint.
- Recommended to output optional `dashboard.signal_attribution` with 6 fields explaining the recommendation's composition, including technical indicators, news sentiment, fundamentals, market environment contributions, and the strongest bullish/bearish signals.
- Pre-market, non-trading day, or unknown phases must not fabricate today's intraday movement; when quote/daily_bars/technical is stale, fallback, missing, fetch_failed, partial, or estimated, `confidence_level` must not be High.

{language_section}
"""

LEGACY_DEFAULT_CHAT_SYSTEM_PROMPT = """You are a {market_role} investment analysis Agent focused on trend trading, equipped with data tools and trading skills, responsible for answering users' stock investment questions.

{market_guidelines}

## Analysis Workflow (must follow strict phase order; no skipping or combining phases)

When a user asks about a stock, you must call tools in the following four phases in order, waiting for each phase's tool results to fully return before proceeding to the next:

**Phase 1: Market Data & Candlestick** (must execute first)
- Call `get_realtime_quote` to fetch real-time market quote and current price
- Call `get_daily_history` to fetch recent historical candlestick data

**Phase 2: Technical & Chip Distribution** (execute after Phase 1 results return)
- Call `analyze_trend` to fetch MA/MACD/RSI and other technical indicators
- Call `get_chip_distribution` to fetch chip distribution structure

**Phase 3: Intelligence Search** (execute after first two phases complete)
- Call `search_stock_news` to search for latest news, announcements, insider sell-downs, earnings warnings, and other risk signals

**Phase 4: Comprehensive Analysis** (generate response after all tool data is ready)
- Based on the above real data, combine with active skills for comprehensive assessment and output investment advice

> ⚠️ Do NOT combine tools from different phases into a single call (e.g., do not request market data, technical indicators, and news in the first call).
{default_skill_policy_section}

## Rules

1. **Must use tools to fetch real data** — never fabricate numbers; all data must come from tool return results.
2. **Apply trading skills** — evaluate each active skill's conditions and reflect skill judgment results in the response.
3. **Free conversation** — organize your response freely based on the user's question; no need to output JSON.
4. **Risk first** — must screen for risks (insider sell-downs, earnings warnings, regulatory issues).
5. **Tool failure handling** — log the failure reason, continue analysis with available data, do not retry failed tools.

{skills_section}
{language_section}
"""

CHAT_SYSTEM_PROMPT = """You are a {market_role} investment analysis Agent equipped with data tools and switchable trading skills, responsible for answering users' stock investment questions.

{market_guidelines}

## Analysis Workflow (must follow strict phase order; no skipping or combining phases)

When a user asks about a stock, you must call tools in the following four phases in order, waiting for each phase's tool results to fully return before proceeding to the next:

**Phase 1: Market Data & Candlestick** (must execute first)
- Call `get_realtime_quote` to fetch real-time market quote and current price
- Call `get_daily_history` to fetch recent historical candlestick data

**Phase 2: Technical & Chip Distribution** (execute after Phase 1 results return)
- Call `analyze_trend` to fetch MA/MACD/RSI and other technical indicators
- Call `get_chip_distribution` to fetch chip distribution structure

**Phase 3: Intelligence Search** (execute after first two phases complete)
- Call `search_stock_news` to search for latest news, announcements, insider sell-downs, earnings warnings, and other risk signals

**Phase 4: Comprehensive Analysis** (generate response after all tool data is ready)
- Based on the above real data, combine with active skills for comprehensive assessment and output investment advice

> ⚠️ Do NOT combine tools from different phases into a single call (e.g., do not request market data, technical indicators, and news in the first call).
{default_skill_policy_section}

## Rules

1. **Must use tools to fetch real data** — never fabricate numbers; all data must come from tool return results.
2. **Apply trading skills** — evaluate each active skill's conditions and reflect skill judgment results in the response.
3. **Free conversation** — organize your response freely based on the user's question; no need to output JSON.
4. **Risk first** — must screen for risks (insider sell-downs, earnings warnings, regulatory issues).
5. **Tool failure handling** — log the failure reason, continue analysis with available data, do not retry failed tools.

{skills_section}
{language_section}
"""


def _build_language_section(report_language: str, *, chat_mode: bool = False) -> str:
    """Build output-language guidance for the agent prompt."""
    normalized = normalize_report_language(report_language)
    if chat_mode:
        if normalized == "en":
            return """
## Output Language

- Reply in English.
- If you output JSON, keep the keys unchanged and write every human-readable value in English.
"""
        return """
## 输出语言

- 默认使用中文回答。
- 若输出 JSON，键名保持不变，所有面向用户的文本值使用中文。
"""

    if normalized == "en":
        return """
## Output Language

- Keep every JSON key unchanged.
- `decision_type` must remain `buy|hold|sell`.
- All human-readable JSON values must be written in English.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, all dashboard text, checklist items, and summaries.
"""

    return """
## 输出语言

- 所有 JSON 键名保持不变。
- `decision_type` 必须保持为 `buy|hold|sell`。
- 所有面向用户的人类可读文本值必须使用中文。
"""


# ============================================================
# Agent Executor
# ============================================================

class AgentExecutor:
    """ReAct agent loop with tool calling.

    Usage::

        executor = AgentExecutor(tool_registry, llm_adapter)
        result = executor.run("Analyze stock 600519")
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        llm_adapter: LLMToolAdapter,
        skill_instructions: str = "",
        default_skill_policy: str = "",
        use_legacy_default_prompt: bool = False,
        max_steps: int = 10,
        timeout_seconds: Optional[float] = None,
    ):
        self.tool_registry = tool_registry
        self.llm_adapter = llm_adapter
        self.skill_instructions = skill_instructions
        self.default_skill_policy = default_skill_policy
        self.use_legacy_default_prompt = use_legacy_default_prompt
        self.max_steps = max_steps
        self.timeout_seconds = timeout_seconds

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a given task.

        Args:
            task: The user task / analysis request.
            context: Optional context dict (e.g., {"stock_code": "600519"}).

        Returns:
            AgentResult with parsed dashboard or error.
        """
        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## Active Trading Skills\n\n{self.skill_instructions}"
        default_skill_policy_section = ""
        if self.default_skill_policy:
            default_skill_policy_section = f"\n{self.default_skill_policy}\n"
        report_language = normalize_report_language((context or {}).get("report_language", "zh"))
        stock_code = (context or {}).get("stock_code", "")
        market_role = get_market_role(stock_code, report_language)
        market_guidelines = get_market_guidelines(stock_code, report_language)
        prompt_template = (
            LEGACY_DEFAULT_AGENT_SYSTEM_PROMPT
            if self.use_legacy_default_prompt
            else AGENT_SYSTEM_PROMPT
        )
        system_prompt = prompt_template.format(
            market_role=market_role,
            market_guidelines=market_guidelines,
            default_skill_policy_section=default_skill_policy_section,
            skills_section=skills_section,
            language_section=_build_language_section(report_language),
        )

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._build_user_message(task, context)},
        ]

        return self._run_loop(messages, tool_decls, parse_dashboard=True)

    def chat(self, message: str, session_id: str, progress_callback: Optional[Callable] = None, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """Execute the agent loop for a free-form chat message.

        Args:
            message: The user's chat message.
            session_id: The conversation session ID.
            progress_callback: Optional callback for streaming progress events.
            context: Optional context dict from previous analysis for data reuse.

        Returns:
            AgentResult with the text response.
        """
        from src.agent.conversation import conversation_manager

        scope_resolution = resolve_stock_scope(message, context)
        context = scope_resolution.effective_context

        # Build system prompt with skills
        skills_section = ""
        if self.skill_instructions:
            skills_section = f"## Active Trading Skills\n\n{self.skill_instructions}"
        default_skill_policy_section = ""
        if self.default_skill_policy:
            default_skill_policy_section = f"\n{self.default_skill_policy}\n"
        report_language = normalize_report_language((context or {}).get("report_language", "zh"))
        stock_code = (context or {}).get("stock_code", "")
        market_role = get_market_role(stock_code, report_language)
        market_guidelines = get_market_guidelines(stock_code, report_language)
        prompt_template = (
            LEGACY_DEFAULT_CHAT_SYSTEM_PROMPT
            if self.use_legacy_default_prompt
            else CHAT_SYSTEM_PROMPT
        )
        system_prompt = prompt_template.format(
            market_role=market_role,
            market_guidelines=market_guidelines,
            default_skill_policy_section=default_skill_policy_section,
            skills_section=skills_section,
            language_section=_build_language_section(report_language, chat_mode=True),
        )

        # Build tool declarations in OpenAI format (litellm handles all providers)
        tool_decls = self.tool_registry.to_openai_tools()

        # Get conversation history
        conversation_manager.get_or_create(session_id)
        config = getattr(self.llm_adapter, "_config", None) or get_config()
        bundle = build_agent_chat_context_bundle(session_id, self.llm_adapter, config)

        # Initialize conversation
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        messages.extend(bundle.context_messages)

        # Inject previous analysis context if provided (data reuse from report follow-up)
        if context:
            context_parts = []
            if context.get("stock_code"):
                context_parts.append(f"Stock Code: {context['stock_code']}")
            if context.get("stock_name"):
                context_parts.append(f"Stock Name: {context['stock_name']}")
            if context.get("previous_price"):
                context_parts.append(f"Previous Analysis Price: {context['previous_price']}")
            if context.get("previous_change_pct"):
                context_parts.append(f"Previous Change: {context['previous_change_pct']}%")
            if context.get("previous_analysis_summary"):
                summary = context["previous_analysis_summary"]
                summary_text = json.dumps(summary, ensure_ascii=False) if isinstance(summary, dict) else str(summary)
                context_parts.append(f"Previous Analysis Summary:\n{summary_text}")
            if context.get("previous_strategy"):
                strategy = context["previous_strategy"]
                strategy_text = json.dumps(strategy, ensure_ascii=False) if isinstance(strategy, dict) else str(strategy)
                context_parts.append(f"Previous Strategy Analysis:\n{strategy_text}")
            daily_market_context_section = format_daily_market_context_prompt_section(
                context.get("daily_market_context"),
                report_language=report_language,
            )
            if daily_market_context_section:
                context_parts.append(daily_market_context_section.strip())
            if context_parts:
                context_msg = "[System-provided historical analysis context for reference]\n" + "\n".join(context_parts)
                messages.append({"role": "user", "content": context_msg})
                messages.append({"role": "assistant", "content": "OK, I have reviewed the stock's historical analysis data. What would you like to know?"})

        messages.append({"role": "user", "content": message})
        baseline_len = len(messages)
        run_id = str(uuid.uuid4())

        # Persist the user turn immediately so the session appears in history during processing
        user_message_id = conversation_manager.add_message(session_id, "user", message)

        result = self._run_loop(
            messages,
            tool_decls,
            parse_dashboard=False,
            progress_callback=progress_callback,
            stock_scope=scope_resolution.stock_scope,
        )

        # Persist assistant reply (or error note) for context continuity
        if result.success:
            assistant_message_id = conversation_manager.add_message(session_id, "assistant", result.content)
            self._persist_provider_trace(
                session_id=session_id,
                run_id=run_id,
                messages=result.messages,
                baseline_len=baseline_len,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
            )
        else:
            error_note = f"[Analysis Failed] {result.error or 'Unknown error'}"
            conversation_manager.add_message(session_id, "assistant", error_note)

        return result

    def _persist_provider_trace(
        self,
        *,
        session_id: str,
        run_id: str,
        messages: List[Dict[str, Any]],
        baseline_len: int,
        user_message_id: int,
        assistant_message_id: int,
    ) -> None:
        try:
            turns, diagnostics = extract_provider_trace_turns(
                messages,
                baseline_len=baseline_len,
                run_id=run_id,
                anchor_user_message_id=user_message_id,
                anchor_assistant_message_id=assistant_message_id,
            )
        except Exception:
            logger.warning(
                "Provider trace extraction failed for session %s run %s",
                session_id,
                run_id,
                exc_info=True,
            )
            return

        if diagnostics.trace_dropped_reason:
            logger.debug(
                "Provider trace skipped for session %s run %s: %s",
                session_id,
                run_id,
                diagnostics.trace_dropped_reason,
            )
        if not turns:
            return

        try:
            db = get_db()
        except Exception:
            logger.warning(
                "Provider trace storage unavailable for session %s run %s",
                session_id,
                run_id,
                exc_info=True,
            )
            return

        for turn in turns:
            try:
                db.save_agent_provider_turn(
                    session_id=session_id,
                    run_id=run_id,
                    provider=turn.provider,
                    model=turn.model,
                    anchor_user_message_id=user_message_id,
                    anchor_assistant_message_id=assistant_message_id,
                    messages=turn.messages,
                    contains_reasoning=turn.contains_reasoning,
                    contains_tool_calls=turn.contains_tool_calls,
                    contains_thinking_blocks=turn.contains_thinking_blocks,
                    must_roundtrip=turn.must_roundtrip,
                    estimated_tokens=turn.estimated_tokens,
                )
            except Exception:
                logger.warning(
                    "Provider trace persistence failed for session %s run %s provider=%s model=%s",
                    session_id,
                    run_id,
                    turn.provider,
                    turn.model,
                    exc_info=True,
                )

    def _run_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_decls: List[Dict[str, Any]],
        parse_dashboard: bool,
        progress_callback: Optional[Callable] = None,
        stock_scope: Optional[StockScope] = None,
    ) -> AgentResult:
        """Delegate to the shared runner and adapt the result.

        This preserves the exact same observable behaviour as the original
        inline implementation while sharing the single authoritative loop
        in :mod:`src.agent.runner`.
        """
        loop_result = run_agent_loop(
            messages=messages,
            tool_registry=self.tool_registry,
            llm_adapter=self.llm_adapter,
            max_steps=self.max_steps,
            progress_callback=progress_callback,
            max_wall_clock_seconds=self.timeout_seconds,
            stock_scope=stock_scope,
        )

        model_str = loop_result.model

        if parse_dashboard and loop_result.success:
            dashboard = parse_dashboard_json(loop_result.content)
            return AgentResult(
                success=dashboard is not None,
                content=loop_result.content,
                dashboard=dashboard,
                tool_calls_log=loop_result.tool_calls_log,
                total_steps=loop_result.total_steps,
                total_tokens=loop_result.total_tokens,
                provider=loop_result.provider,
                model=model_str,
                error=None if dashboard else "Failed to parse dashboard JSON from agent response",
                messages=loop_result.messages,
            )

        return AgentResult(
            success=loop_result.success,
            content=loop_result.content,
            dashboard=None,
            tool_calls_log=loop_result.tool_calls_log,
            total_steps=loop_result.total_steps,
            total_tokens=loop_result.total_tokens,
            provider=loop_result.provider,
            model=model_str,
            error=loop_result.error,
            messages=loop_result.messages,
        )

    def _build_user_message(self, task: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Build the initial user message."""
        parts = [task]
        if context:
            report_language = normalize_report_language(context.get("report_language", "zh"))
            if context.get("stock_code"):
                parts.append(f"\nStock Code: {context['stock_code']}")
            if context.get("report_type"):
                parts.append(f"Report Type: {context['report_type']}")
            if report_language == "en":
                parts.append("Output Language: English (all JSON keys unchanged, all user-facing text values in English)")
            elif report_language == "ko":
                parts.append("출력 언어: 한국어（모든 JSON 키는 그대로 유지하고, 사용자 노출 텍스트 값은 한국어로 작성）")
            else:
                parts.append("Output Language: Chinese (all JSON keys unchanged, all user-facing text values in Chinese)")

            market_phase_section = format_market_phase_prompt_section(
                context.get("market_phase_context"),
                report_language=report_language,
            )
            if market_phase_section:
                parts.append(market_phase_section)

            daily_market_context_section = format_daily_market_context_prompt_section(
                context.get("daily_market_context"),
                report_language=report_language,
            )
            if daily_market_context_section:
                parts.append(daily_market_context_section)

            analysis_context_pack_summary = context.get("analysis_context_pack_summary")
            if isinstance(analysis_context_pack_summary, str) and analysis_context_pack_summary:
                parts.append(analysis_context_pack_summary)

            # Inject pre-fetched context data to avoid redundant fetches
            if context.get("realtime_quote"):
                parts.append(f"\n[Pre-fetched real-time quote]\n{json.dumps(context['realtime_quote'], ensure_ascii=False)}")
            if context.get("chip_distribution"):
                parts.append(f"\n[Pre-fetched chip distribution]\n{json.dumps(context['chip_distribution'], ensure_ascii=False)}")
            if context.get("news_context"):
                parts.append(f"\n[Pre-fetched news and sentiment intelligence]\n{context['news_context']}")

        parts.append("\nUse available tools to fetch missing data (such as historical candlestick data, news, etc.), then output the analysis results in Decision Dashboard JSON format.")
        return "\n".join(parts)
