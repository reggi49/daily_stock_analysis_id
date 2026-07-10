# Trading Strategies Directory

This directory stores **natural-language trading strategy files** (YAML format). All `.yaml` files in this directory are automatically loaded at system startup.

For users and documentation, we continue to refer to these capabilities as "strategies"; in code, configuration, and API fields, they are uniformly named `skill`, which can be understood as a "reusable strategy capability pack."

## How to Write a Custom Strategy (Strategy Skill)

Simply create a `.yaml` file describing your trading strategy in natural language (any language). **No code is required.**

### Minimal Template

```yaml
name: my_strategy          # Unique identifier (English, underscore-separated)
display_name: My Strategy  # Display name
description: Brief description of the strategy's purpose

instructions: |
  Your strategy description...
  Write entry criteria, entry conditions, exit conditions, etc. in natural language.
  You can reference tool names (e.g. get_daily_history, analyze_trend) to guide which data the AI uses.
```

### Full Template

```yaml
name: my_strategy
display_name: My Strategy
description: Brief description of the market scenarios the strategy is suited for

# Strategy category: trend, pattern, reversal, framework
category: trend

# Associated core trading rule numbers (1-7), optional
core_rules: [1, 2]

# List of tools the strategy requires, optional
# Available tools: get_daily_history, analyze_trend, get_realtime_quote,
#                 get_sector_rankings, search_stock_news, get_stock_info
required_tools:
  - get_daily_history
  - analyze_trend

# Optional aliases (for natural-language skill selection such as /ask)
aliases: [My Method, My Model]

# The following metadata drives default behavior (optional)
# default_active: Whether this is part of the default active skill set
# default_router: Whether this is part of the router fallback skill set
# default_priority: Default display/sort priority (lower number = higher priority)
# market_regimes: Market regime tags this skill is best suited for
default_active: true
default_router: false
default_priority: 100
market_regimes: [trending_up]

# Detailed strategy description (natural language, supports Markdown)
instructions: |
  **My Strategy Name**

  Criteria:

  1. **Condition 1**:
     - Use `analyze_trend` to check moving average alignment.
     - Describe the trend characteristics you expect to see...

  2. **Condition 2**:
     - Describe the volume requirements...

  Score adjustment:
  - Suggested sentiment_score adjustment when conditions are met
  - Note the strategy name in `buy_reason`
```

### Core Trading Rules Reference

| Number | Rule |
|------|------|
| 1 | Strict entry: Only consider entry when deviation rate < 5% |
| 2 | Trend trading: MA5 > MA10 > MA20 bullish alignment |
| 3 | Efficiency first: Volume confirms trend validity |
| 4 | Entry preference: Prefer pullback to moving average support |
| 5 | Risk screening: Negative news has veto power |
| 6 | Volume-price coordination: Volume validates price movement |
| 7 | Relaxed rules for strong trend stocks: Leading stocks may have relaxed criteria |

## Custom Strategy Directories

In addition to this directory (built-in strategies), you can specify additional custom strategy directories via environment variable:

```env
AGENT_SKILL_DIR=./my_skills
```

The system will load both built-in and custom strategies. If names conflict, custom strategies override built-in ones.

The environment variable name remains `AGENT_SKILL_DIR`; this is the unified internal configuration entry point. In product semantics, it still represents "custom strategy directory."
