# -*- coding: utf-8 -*-
"""
===================================
History Record Models
===================================

Responsibilities:
1. Define history list and detail models
2. Define complete analysis report models
"""

from typing import Optional, List, Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.v1.schemas.market_phase import MarketPhaseSummary
from src.schemas.decision_action import DecisionAction


class HistoryItem(BaseModel):
    """History record summary (for list display)."""

    id: Optional[int] = Field(None, description="Analysis history record primary key ID")
    query_id: str = Field(..., description="Analysis record associated query_id (duplicated in batch analysis)")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    report_type: Optional[str] = Field(None, description="Report type")
    trend_prediction: Optional[str] = Field(None, description="Trend prediction")
    analysis_summary: Optional[str] = Field(None, description="Analysis summary")
    sentiment_score: Optional[int] = Field(
        None,
        description="Sentiment score (historical data may exceed 0-100 range, no constraint on read)",
    )
    operation_advice: Optional[str] = Field(None, description="Operation advice")
    action: Optional[DecisionAction] = Field(None, description="Structured advice action taxonomy")
    action_label: Optional[str] = Field(None, description="Advice action display label")
    current_price: Optional[float] = Field(None, description="Stock price at analysis time")
    change_pct: Optional[float] = Field(None, description="Price change at analysis time (%)")
    volume_ratio: Optional[float] = Field(None, description="Volume ratio at analysis time")
    turnover_rate: Optional[float] = Field(None, description="Turnover rate at analysis time")
    model_used: Optional[str] = Field(
        None,
        description="Model snapshot in analysis history, for historical metadata display only; does not participate in model config or runtime routing",
    )
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="Low-sensitivity market phase summary for this analysis",
    )
    created_at: Optional[str] = Field(None, description="Creation time")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1234,
            "query_id": "abc123",
            "stock_code": "600519",
            "stock_name": "Technically good",
            "report_type": "detailed",
            "sentiment_score": 75,
            "operation_advice": "Recommended to hold",
            "created_at": "2024-01-01T12:00:00"
        }
    })


class HistoryListResponse(BaseModel):
    """History record list response."""
    
    total: int = Field(..., description="Total record count")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    items: List[HistoryItem] = Field(default_factory=list, description="Record list")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 100,
            "page": 1,
            "limit": 20,
            "items": []
        }
    })


class DeleteHistoryRequest(BaseModel):
    """Delete history records request."""

    record_ids: List[int] = Field(default_factory=list, description="List of history record primary key IDs to delete")


class DeleteHistoryResponse(BaseModel):
    """Delete history records response."""

    deleted: int = Field(..., description="Number of history records actually deleted")


class NewsIntelItem(BaseModel):
    """News intelligence item."""

    title: str = Field(..., description="News title")
    snippet: str = Field("", description="News snippet (max 200 characters)")
    url: str = Field(..., description="News link")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Recommended to hold，Recommended to hold 20%",
            "snippet": "Recommended to hold，Recommended to hold 20%...",
            "url": "https://example.com/news/123"
        }
    })


class NewsIntelResponse(BaseModel):
    """News intelligence response."""

    total: int = Field(..., description="Number of news items")
    items: List[NewsIntelItem] = Field(default_factory=list, description="News list")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 2,
            "items": []
        }
    })


class ReportMeta(BaseModel):
    """Report metadata."""

    model_config = ConfigDict(protected_namespaces=("model_validate", "model_dump"))

    id: Optional[int] = Field(None, description="Analysis history record primary key ID (only in history reports)")
    query_id: str = Field(..., description="Analysis record associated query_id (duplicated in batch analysis)")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    report_type: Optional[str] = Field(None, description="Report type")
    report_language: Optional[str] = Field(None, description="Report output language (zh/en)")
    created_at: Optional[str] = Field(None, description="Creation time")
    current_price: Optional[float] = Field(None, description="Stock price at analysis time")
    change_pct: Optional[float] = Field(None, description="Price change at analysis time (%)")
    model_used: Optional[str] = Field(
        None,
        description="历史报告元数据中的模型快照，仅用于展示；不参与运行时模型调用路径或配置路由",
    )
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="Low-sensitivity market phase summary for this analysis",
    )


class ReportSummary(BaseModel):
    """Report overview section."""
    
    analysis_summary: Optional[str] = Field(None, description="Key conclusions")
    operation_advice: Optional[str] = Field(None, description="Operation advice")
    action: Optional[DecisionAction] = Field(None, description="Structured advice action taxonomy")
    action_label: Optional[str] = Field(None, description="Advice action display label")
    trend_prediction: Optional[str] = Field(None, description="Trend prediction")
    sentiment_score: Optional[int] = Field(
        None,
        description="Sentiment score (historical data may exceed 0-100 range, no constraint on read)",
    )
    sentiment_label: Optional[str] = Field(None, description="Sentiment label")


class ReportStrategy(BaseModel):
    """Strategy position section."""
    
    ideal_buy: Optional[str] = Field(None, description="Ideal buy price")
    secondary_buy: Optional[str] = Field(None, description="Secondary buy price")
    stop_loss: Optional[str] = Field(None, description="Stop loss price")
    take_profit: Optional[str] = Field(None, description="Take profit price")


class AnalysisContextPackOverviewSubject(BaseModel):
    """AnalysisContextPack visible summary subject info."""

    code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    market: Optional[str] = Field(None, description="Market")


class AnalysisContextPackOverviewBlock(BaseModel):
    """AnalysisContextPack visible summary data block."""

    key: str = Field(..., description="Data block stable key")
    label: str = Field(..., description="Data block display name")
    status: Literal[
        "available",
        "missing",
        "not_supported",
        "fallback",
        "stale",
        "estimated",
        "partial",
        "fetch_failed",
    ] = Field(..., description="Data block quality status")
    source: Optional[str] = Field(None, description="Data source")
    warnings: List[str] = Field(default_factory=list, description="Data block warning codes")
    missing_reasons: List[str] = Field(default_factory=list, description="Missing reasons")


class AnalysisContextPackOverviewCounts(BaseModel):
    """AnalysisContextPack visible summary status counts."""

    available: int = 0
    missing: int = 0
    not_supported: int = 0
    fallback: int = 0
    stale: int = 0
    estimated: int = 0
    partial: int = 0
    fetch_failed: int = 0


class AnalysisContextPackOverviewMetadata(BaseModel):
    """AnalysisContextPack visible summary metadata."""

    trigger_source: Optional[str] = Field(None, description="Trigger source")
    news_result_count: Optional[int] = Field(None, description="News result count")


class AnalysisContextPackOverviewDataQuality(BaseModel):
    """AnalysisContextPack visible summary data quality score."""

    overall_score: Optional[int] = Field(None, ge=0, le=100, description="Overall input data quality score")
    level: Optional[Literal["good", "usable", "limited", "poor"]] = Field(
        None,
        description="Input data quality level",
    )
    block_scores: Dict[str, int] = Field(default_factory=dict, description="Fixed data block quality scores")
    limitations: List[str] = Field(default_factory=list, description="Low-sensitivity data limitation notes")


class AnalysisContextPackOverview(BaseModel):
    """Low-sensitivity AnalysisContextPack summary visible in history/API."""

    pack_version: str = Field(..., description="AnalysisContextPack version")
    created_at: Optional[str] = Field(None, description="Creation time")
    subject: AnalysisContextPackOverviewSubject
    blocks: List[AnalysisContextPackOverviewBlock] = Field(default_factory=list)
    counts: AnalysisContextPackOverviewCounts
    data_quality: Optional[AnalysisContextPackOverviewDataQuality] = Field(
        None,
        description="Low-sensitivity summary of analysis input data quality",
    )
    warnings: List[str] = Field(default_factory=list, description="Top-level data quality warnings")
    metadata: AnalysisContextPackOverviewMetadata = Field(default_factory=AnalysisContextPackOverviewMetadata)


class ReportDetails(BaseModel):
    """Report details section."""
    
    news_content: Optional[str] = Field(None, description="News summary")
    raw_result: Optional[Any] = Field(None, description="Raw analysis result (JSON)")
    context_snapshot: Optional[Any] = Field(None, description="Context snapshot at analysis time (JSON)")
    analysis_context_pack_overview: Optional[AnalysisContextPackOverview] = Field(
        None,
        description="Low-sensitivity summary of analysis input context pack",
    )
    financial_report: Optional[Any] = Field(None, description="结构化财报摘要（来自 fundamental_context）")
    dividend_metrics: Optional[Any] = Field(None, description="结构化分红指标（含 TTM 口径）")
    belong_boards: Optional[Any] = Field(None, description="关联板块列表")
    sector_rankings: Optional[Any] = Field(None, description="板块涨跌榜（结构 {top, bottom}）")
    concept_rankings: Optional[Any] = Field(None, description="概念板块涨跌榜（结构 {top, bottom}）")
    market_structure: Optional[Any] = Field(None, description="市场结构上下文（题材层 + 个股位置层）")

    @model_validator(mode="after")
    def populate_context_derived_details(self) -> "ReportDetails":
        if self.concept_rankings is None and self.context_snapshot is not None:
            try:
                from src.utils.data_processing import extract_board_detail_fields

                extracted = extract_board_detail_fields(self.context_snapshot)
                self.concept_rankings = extracted.get("concept_rankings")
            except Exception:
                self.concept_rankings = None
        if self.market_structure is None:
            try:
                from src.utils.data_processing import extract_market_structure_detail_field

                self.market_structure = extract_market_structure_detail_field(
                    self.context_snapshot,
                    self.raw_result,
                )
            except Exception:
                self.market_structure = None
        return self


class AnalysisReport(BaseModel):
    """Complete analysis report."""

    meta: ReportMeta = Field(..., description="Metadata")
    summary: ReportSummary = Field(..., description="Overview section")
    strategy: Optional[ReportStrategy] = Field(None, description="Strategy position section")
    details: Optional[ReportDetails] = Field(None, description="Details section")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "meta": {
                "query_id": "abc123",
                "stock_code": "600519",
                "stock_name": "Technically good",
                "report_type": "detailed",
                "report_language": "zh",
                "created_at": "2024-01-01T12:00:00"
            },
            "summary": {
                "analysis_summary": "Technically good，Recommended to hold",
                "operation_advice": "Recommended to hold",
                "trend_prediction": "optimism",
                "sentiment_score": 75,
                "sentiment_label": "optimism"
            },
            "strategy": {
                "ideal_buy": "1800.00",
                "secondary_buy": "1750.00",
                "stop_loss": "1700.00",
                "take_profit": "2000.00"
            },
            "details": None
        }
    })


class MarkdownReportResponse(BaseModel):
    """Markdown format report response."""

    content: str = Field(..., description="Complete report content in Markdown format")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content": "# 📊 Technically good (600519) analysis report\n\n> Analysis date：**2024-01-01**\n\n..."
        }
    })


class StockBarItem(BaseModel):
    """Stock bar item (deduplicated per-stock summary)."""

    id: int = Field(..., description="Primary key ID of the latest analysis for this stock")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    report_type: Optional[str] = Field(None, description="Report type")
    sentiment_score: Optional[int] = Field(
        None,
        description="Latest sentiment score",
    )
    operation_advice: Optional[str] = Field(None, description="Latest operation advice")
    action: Optional[DecisionAction] = Field(None, description="Structured advice action taxonomy")
    action_label: Optional[str] = Field(None, description="Advice action display label")
    analysis_count: int = Field(..., description="Total historical analysis count for this stock")
    last_analysis_time: Optional[str] = Field(None, description="Time of the most recent analysis")
    model_used: Optional[str] = Field(
        None,
        description="最新分析使用的模型快照，仅用于列表展示；不改动运行时调用与配置路径",
    )
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="Low-sensitivity market phase summary from the latest analysis",
    )
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1234,
            "stock_code": "600519",
            "stock_name": "Technically good",
            "report_type": "detailed",
            "sentiment_score": 75,
            "operation_advice": "Recommended to hold",
            "analysis_count": 18,
            "last_analysis_time": "2024-01-01T12:00:00",
            "model_used": "Gemini 2.5 Pro",
        }
    })


class StockBarResponse(BaseModel):
    """Stock bar list response."""

    total: int = Field(..., description="Number of unique stocks")
    items: List[StockBarItem] = Field(default_factory=list, description="Stock list")


class WatchlistRequest(BaseModel):
    """Watchlist operation request."""

    stock_code: str = Field(..., description="Stock code", min_length=1)


class WatchlistResponse(BaseModel):
    """Watchlist response."""

    stock_codes: List[str] = Field(default_factory=list, description="Current watchlist stock code list")
    message: str = Field(..., description="Operation result description")


class RunDiagnosticComponent(BaseModel):
    """Single run diagnostic component summary."""

    key: str = Field(..., description="Component key")
    label: str = Field(..., description="Component display name")
    status: str = Field(..., description="Component status: ok/degraded/failed/unknown/not_configured/skipped")
    message: str = Field(..., description="User-readable summary")
    details: Optional[Dict[str, Any]] = Field(None, description="Collapsible diagnostic details")


class RunDiagnosticSummaryResponse(BaseModel):
    """History report run diagnostic summary."""

    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    query_id: Optional[str] = Field(None, description="Analysis query ID")
    stock_code: Optional[str] = Field(None, description="Stock code")
    trigger_source: Optional[str] = Field(None, description="Trigger source")
    status: str = Field(..., description="Overall status: normal/degraded/failed/unknown")
    status_label: str = Field(..., description="Overall status display label")
    reason: str = Field(..., description="Primary diagnostic reason")
    components: Dict[str, RunDiagnosticComponent] = Field(default_factory=dict, description="Key pipeline diagnostic components")
    copy_text: str = Field(..., description="Sanitized copyable troubleshooting text")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trace_id": "task_abc123",
            "query_id": "task_abc123",
            "stock_code": "600519",
            "status": "degraded",
            "status_label": "partial downgrade",
            "reason": "Real-time quotes failed：timeout",
            "components": {},
            "copy_text": "trace_id: task_abc123\nstock_code: 600519\n...",
        }
    })
