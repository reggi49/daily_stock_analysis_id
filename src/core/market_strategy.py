# -*- coding: utf-8 -*-
"""Market strategy blueprints for CN/HK/US daily market recap."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StrategyDimension:
    """Single strategy dimension used by market recap prompts."""

    name: str
    objective: str
    checkpoints: List[str]


@dataclass(frozen=True)
class MarketStrategyBlueprint:
    """Region specific market strategy blueprint."""

    region: str
    title: str
    positioning: str
    principles: List[str]
    dimensions: List[StrategyDimension]
    action_framework: List[str]

    def to_prompt_block(self) -> str:
        """Render blueprint as prompt instructions."""
        principles_text = "\n".join([f"- {item}" for item in self.principles])
        action_text = "\n".join([f"- {item}" for item in self.action_framework])

        dims = []
        for dim in self.dimensions:
            checkpoints = "\n".join([f"  - {cp}" for cp in dim.checkpoints])
            dims.append(f"- {dim.name}: {dim.objective}\n{checkpoints}")
        dimensions_text = "\n".join(dims)

        return (
            f"## Strategy Blueprint: {self.title}\n"
            f"{self.positioning}\n\n"
            f"### Strategy Principles\n{principles_text}\n\n"
            f"### Analysis Dimensions\n{dimensions_text}\n\n"
            f"### Action Framework\n{action_text}"
        )

    def to_markdown_block(self) -> str:
        """Render blueprint as markdown section for template fallback report."""
        dims = "\n".join([f"- **{dim.name}**: {dim.objective}" for dim in self.dimensions])
        section_title = "### VI. Strategy Framework" if self.region == "us" else "### VI. Strategy Framework"
        return f"{section_title}\n{dims}\n"


CN_BLUEPRINT = MarketStrategyBlueprint(
    region="cn",
    title="A-Share Three-Phase Market Review Strategy",
    positioning="Focus on index trend, capital flow dynamics, and sector rotation to form next-day trading plans.",
    principles=[
        "Read index direction first, then volume structure, and finally sector persistence.",
        "Conclusions must map to position sizing, pacing, and risk control actions.",
        "Use current-day data and recent 3-day news for judgments; do not speculate on unverified information.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Structure",
            objective="Classify the market as uptrend, sideways, or defensive phase.",
            checkpoints=["Are Shanghai/Shenzhen/ChiNext aligned directionally", "Did volume confirm the move", "Are key support/resistance levels breached"],
        ),
        StrategyDimension(
            name="Capital Sentiment",
            objective="Identify short-term risk appetite and sentiment temperature.",
            checkpoints=["Advance/decline counts and limit up/down structure", "Whether trading volume is expanding", "Whether high-flying stocks are showing divergence"],
        ),
        StrategyDimension(
            name="Core Sectors",
            objective="Distill tradeable themes and avoidance directions.",
            checkpoints=["Are leading sectors backed by event catalysts", "Is there a leader driving the sector internally", "Are lagging sectors broadening"],
        ),
    ],
    action_framework=[
        "Offense: Index alignment upward + expanding volume + strengthening themes.",
        "Neutral: Mixed index signals or low-volume sideways; control positions and wait for confirmation.",
        "Defense: Weakening indices + broadening laggards; prioritize risk control and reduce positions.",
    ],
)

US_BLUEPRINT = MarketStrategyBlueprint(
    region="us",
    title="US Market Regime Strategy",
    positioning="Focus on index trend, macro narrative, and sector rotation to define next-session risk posture.",
    principles=[
        "Read market regime from S&P 500, Nasdaq, and Dow alignment first.",
        "Separate beta move from theme-driven alpha rotation.",
        "Translate recap into actionable risk-on/risk-off stance with clear invalidation points.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Regime",
            objective="Classify the market as momentum, range, or risk-off.",
            checkpoints=[
                "Are SPX/NDX/DJI directionally aligned",
                "Did volume confirm the move",
                "Are key index levels reclaimed or lost",
            ],
        ),
        StrategyDimension(
            name="Macro & Flows",
            objective="Map policy/rates narrative into equity risk appetite.",
            checkpoints=[
                "Treasury yield and USD implications",
                "Breadth and leadership concentration",
                "Defensive vs growth factor rotation",
            ],
        ),
        StrategyDimension(
            name="Sector Themes",
            objective="Identify persistent leaders and vulnerable laggards.",
            checkpoints=[
                "AI/semiconductor/software trend persistence",
                "Energy/financials sensitivity to macro data",
                "Volatility signals from VIX and large-cap earnings",
            ],
        ),
    ],
    action_framework=[
        "Risk-on: broad index breakout with expanding participation.",
        "Neutral: mixed index signals; focus on selective relative strength.",
        "Risk-off: failed breakouts and rising volatility; prioritize capital preservation.",
    ],
)

HK_BLUEPRINT = MarketStrategyBlueprint(
    region="hk",
    title="HK Market Three-Phase Review Strategy",
    positioning="Focus on Hang Seng Index trend, southbound capital dynamics, and sector rotation to form next-day trading plans.",
    principles=[
        "Read HSI/Hang Seng Tech/HSCEI direction first, then southbound capital sentiment, and finally sector persistence.",
        "Conclusions must map to position sizing, pacing, and risk control actions.",
        "Use current-day data and recent 3-day news for judgments; do not speculate on unverified information.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Structure",
            objective="Classify the market as uptrend, sideways, or defensive phase.",
            checkpoints=["Are HSI/Hang Seng Tech/HSCEI aligned", "Did volume confirm the move", "Are key support/resistance levels breached"],
        ),
        StrategyDimension(
            name="Capital Sentiment",
            objective="Identify southbound capital risk appetite and sentiment temperature.",
            checkpoints=["Southbound net inflow direction and scale", "HKD exchange rate and mainland policy implications", "Market breadth and leadership concentration"],
        ),
        StrategyDimension(
            name="Core Sectors",
            objective="Distill tradeable themes and avoidance directions.",
            checkpoints=["Tech/internet platform trend persistence", "Financials/real estate sensitivity to policy shifts", "Defensive vs growth factor rotation"],
        ),
    ],
    action_framework=[
        "Offense: HSI alignment upward + persistent southbound inflows + strengthening themes.",
        "Neutral: Mixed index signals or low-volume sideways; control positions and wait for confirmation.",
        "Defense: Weakening indices + rising volatility; prioritize risk control and reduce positions.",
    ],
)


JP_BLUEPRINT = MarketStrategyBlueprint(
    region="jp",
    title="Japan Market Three-Phase Review Strategy",
    positioning="Focus on Nikkei 225, TOPIX, exchange rates, and global risk appetite to form next-day trading plans.",
    principles=[
        "Check if Nikkei 225 and TOPIX are aligned, then look at yen, semiconductor/export chain, and financial stock performance.",
        "Map index conclusions to position sizing, pacing, and risk control actions.",
        "Base judgments only on available indices, news, and price action; do not fabricate market breadth or sector statistics.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Structure",
            objective="Classify the Japanese market as uptrend, sideways, or defensive phase.",
            checkpoints=["Are Nikkei 225/TOPIX aligned", "Has the index broken out of or below a key range", "Are large-cap weights and growth chain aligned"],
        ),
        StrategyDimension(
            name="Macro and FX",
            objective="Identify the impact of yen, interest rates, and global risk appetite on the equity market.",
            checkpoints=["Yen direction impact on export chain", "BOJ and US Treasury yield narrative", "Overseas tech and semiconductor chain mapping"],
        ),
        StrategyDimension(
            name="Theme Clues",
            objective="Distill persistent themes and crowded directions to avoid.",
            checkpoints=["Semiconductor/automation/auto chain persistence", "Are financials and domestic demand stocks rotating", "Do news catalysts support price action"],
        ),
    ],
    action_framework=[
        "Offense: Major index alignment + improving external risk appetite + strengthening themes.",
        "Neutral: Index divergence or FX disturbance; reduce chasing and wait for confirmation.",
        "Defense: Major indices weakening or rising external risks; prioritize position control.",
    ],
)

KR_BLUEPRINT = MarketStrategyBlueprint(
    region="kr",
    title="Korea Market Three-Phase Review Strategy",
    positioning="Focus on KOSPI, KOSDAQ, semiconductor weights, and global tech risk appetite to form next-day trading plans.",
    principles=[
        "Check if KOSPI/KOSDAQ are aligned, then look at Samsung Electronics, SK Hynix, and other heavyweight signals.",
        "Separate the contributions of index beta, semiconductor cycle, and growth stock risk appetite.",
        "Base judgments only on available indices, news, and price action; do not fabricate market breadth or sector statistics.",
    ],
    dimensions=[
        StrategyDimension(
            name="Trend Structure",
            objective="Classify the Korean market as uptrend, sideways, or defensive phase.",
            checkpoints=["Are KOSPI/KOSDAQ aligned", "Are heavyweight stocks supporting the index", "Are key support/resistance levels breached"],
        ),
        StrategyDimension(
            name="Tech Cycle",
            objective="Identify how semiconductors, AI hardware, and global tech stocks map to the Korean market.",
            checkpoints=["Memory/semiconductor chain news catalysts", "US tech direction linkage", "Foreign capital risk appetite shifts"],
        ),
        StrategyDimension(
            name="Theme Clues",
            objective="Distill persistent themes and crowded directions to avoid.",
            checkpoints=["Are batteries/autos/internet rotating", "KOSDAQ growth stock risk appetite", "Do news catalysts support price action"],
        ),
    ],
    action_framework=[
        "Offense: KOSPI/KOSDAQ alignment upward + tech heavyweight confirmation + improving external risk appetite.",
        "Neutral: Index or heavyweight divergence; control positions and wait for confirmation.",
        "Defense: Tech weights weakening or rising external risks; prioritize drawdown control.",
    ],
)

def get_market_strategy_blueprint(region: str) -> MarketStrategyBlueprint:
    """Return strategy blueprint by market region."""
    if region == "us":
        return US_BLUEPRINT
    if region == "hk":
        return HK_BLUEPRINT
    if region == "jp":
        return JP_BLUEPRINT
    if region == "kr":
        return KR_BLUEPRINT
    return CN_BLUEPRINT
