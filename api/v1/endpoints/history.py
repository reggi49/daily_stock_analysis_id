# -*- coding: utf-8 -*-
"""
===================================
History Records Endpoint
===================================

Responsibilities:
1. Provides GET /api/v1/history history list query endpoint
2. Provides GET /api/v1/history/{query_id} history detail query endpoint
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Body

from api.deps import get_database_manager
from api.v1.schemas.history import (
    HistoryListResponse,
    HistoryItem,
    DeleteHistoryRequest,
    DeleteHistoryResponse,
    NewsIntelItem,
    NewsIntelResponse,
    AnalysisReport,
    ReportMeta,
    ReportSummary,
    ReportStrategy,
    ReportDetails,
    MarkdownReportResponse,
    RunDiagnosticSummaryResponse,
    StockBarItem,
    StockBarResponse,
)
from api.v1.schemas.common import ErrorResponse
from api.v1.schemas.run_flow import RunFlowSnapshot
from src.storage import DatabaseManager
from src.report_language import (
    get_sentiment_label,
    get_localized_stock_name,
    localize_operation_advice,
    localize_trend_prediction,
    normalize_report_language,
)
from src.services.history_service import HistoryService, MarkdownReportGenerationError
from src.schemas.decision_action import build_action_fields
from src.utils.data_processing import (
    normalize_model_used,
    extract_fundamental_detail_fields,
    extract_board_detail_fields,
    extract_market_structure_detail_field,
    extract_realtime_detail_fields,
)
from src.analysis_context_pack_overview import (
    extract_analysis_context_pack_overview,
    sanitize_context_snapshot_for_api,
)
from src.market_phase_summary import extract_market_phase_summary

logger = logging.getLogger(__name__)

router = APIRouter()
_DELETE_BY_CODE_BATCH_SIZE = 10_000


def _normalize_code_for_grouping(code: str) -> str:
    """Normalize stock code for deduplication grouping.

    Delegates to data_provider.base.normalize_stock_code which handles
    SH600519, 600519.SH, HK00700, 00700.HK, BJ920748, etc.
    """
    from data_provider.base import normalize_stock_code
    return normalize_stock_code(code or "")


def _raw_result_value(raw_result: Any, key: str) -> Any:
    if not isinstance(raw_result, dict):
        return None

    value = raw_result.get(key)
    if value is not None and value != "":
        return value

    for container_key in ("summary", "dashboard"):
        container = raw_result.get(container_key)
        if isinstance(container, dict):
            nested_value = container.get(key)
            if nested_value is not None and nested_value != "":
                return nested_value

    return None


def _coalesce_text(*values: Any) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _coalesce_int(*values: Any) -> Optional[int]:
    for value in values:
        if value is None or isinstance(value, bool):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            return int(float(value))
        except (TypeError, ValueError):
            continue
    return None


def _extract_guardrail_reason(raw_result: Any) -> Optional[str]:
    if not isinstance(raw_result, dict):
        return None
    for reason in (
        raw_result.get("guardrail_reason"),
        raw_result.get("downgrade_reason"),
        raw_result.get("decision_score_guardrail_reason"),
    ):
        if reason is not None:
            text = str(reason).strip()
            if text:
                return text

    metadata = raw_result.get("metadata")
    if isinstance(metadata, dict):
        metadata_reason = metadata.get("guardrail_reason") or metadata.get("downgrade_reason")
        if metadata_reason is not None:
            text = str(metadata_reason).strip()
            if text:
                return text
    return None


@router.get(
    "",
    response_model=HistoryListResponse,
    responses={
        200: {"description": "History record list"},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get analysis history list",
    description="Paginated analysis history summary, filterable by stock code and date range"
)
def get_history_list(
    stock_code: Optional[str] = Query(None, description="Stock code filter"),
    report_type: Optional[str] = Query(None, description="Report type filter, e.g. market_review"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number (starting from 1)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> HistoryListResponse:
    """
    Get analysis history list.
    
    Paginated analysis history summary, filterable by stock code and date range.
    
    Args:
        stock_code: Stock code filter
        report_type: Report type filter
        start_date: Start date
        end_date: End date
        page: Page number
        limit: Items per page
        db_manager: Database manager dependency
        
    Returns:
        HistoryListResponse: History record list
    """
    try:
        service = HistoryService(db_manager)
        
        # Using sync def; FastAPI auto-runs in thread pool
        result = service.get_history_list(
            stock_code=stock_code,
            report_type=report_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            limit=limit
        )
        
        # Convert to response model
        items = [
            HistoryItem(
                id=item.get("id"),
                query_id=item.get("query_id", ""),
                stock_code=item.get("stock_code", ""),
                stock_name=item.get("stock_name"),
                report_type=item.get("report_type"),
                trend_prediction=item.get("trend_prediction"),
                analysis_summary=item.get("analysis_summary"),
                sentiment_score=item.get("sentiment_score"),
                operation_advice=item.get("operation_advice"),
                action=item.get("action"),
                action_label=item.get("action_label"),
                current_price=item.get("current_price"),
                change_pct=item.get("change_pct"),
                volume_ratio=item.get("volume_ratio"),
                turnover_rate=item.get("turnover_rate"),
                model_used=item.get("model_used"),
                created_at=item.get("created_at"),
                market_phase_summary=item.get("market_phase_summary"),
            )
            for item in result.get("items", [])
        ]
        
        return HistoryListResponse(
            total=result.get("total", 0),
            page=page,
            limit=limit,
            items=items
        )
        
    except Exception as e:
        logger.error(f"Failed to query history list: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query history list: {str(e)}"
            }
        )


@router.delete(
    "/by-code/{stock_code}",
    response_model=DeleteHistoryResponse,
    responses={
        200: {"description": "Deleted successfully"},
        400: {"description": "Stock code cannot be empty", "model": ErrorResponse},
        404: {"description": "Record not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
    summary="Delete history by stock code",
    description="Delete all analysis history records for a specified stock code (supports code variant normalization matching)",
)
def delete_history_by_code(
    stock_code: str,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> DeleteHistoryResponse:
    try:
        candidates = HistoryService._history_code_filter_candidates(stock_code)
        if not candidates:
            raise HTTPException(
                status_code=400,
                detail={"error": "invalid_request", "message": "stock_code cannot be empty"},
            )

        deleted = 0
        while True:
            records, _ = db_manager.get_analysis_history_paginated(
                code=candidates,
                limit=_DELETE_BY_CODE_BATCH_SIZE,
            )
            record_ids = [r.id for r in records if r.id is not None]
            if not record_ids:
                break

            batch_deleted = db_manager.delete_analysis_history_records(record_ids)
            if batch_deleted == 0:
                raise RuntimeError("history deletion made no progress")
            deleted += batch_deleted

            if len(records) < _DELETE_BY_CODE_BATCH_SIZE:
                break

        return DeleteHistoryResponse(deleted=deleted)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete history by stock code: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"Delete failed: {str(e)}"},
        )


@router.delete(
    "",
    response_model=DeleteHistoryResponse,
    responses={
        200: {"description": "Deleted successfully"},
        400: {"description": "Invalid request parameters", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Delete history records",
    description="Batch delete analysis history by record primary key IDs"
)
def delete_history_records(
    request: DeleteHistoryRequest = Body(...),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> DeleteHistoryResponse:
    """
    Batch delete history analysis records by primary key ID.
    """
    record_ids = sorted({record_id for record_id in request.record_ids if record_id is not None})
    if not record_ids:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_request",
                "message": "record_ids cannot be empty"
            }
        )

    try:
        service = HistoryService(db_manager)
        deleted = service.delete_history_records(record_ids)
        return DeleteHistoryResponse(deleted=deleted)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete history records: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to delete history records: {str(e)}"
            }
        )


@router.get(
    "/stocks",
    response_model=StockBarResponse,
    responses={
        200: {"description": "Deduplicated stock list"},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get deduplicated stock list",
    description="Returns the latest analysis summary for each stock in history, excluding market reviews (code=MARKET).",
)
def get_stock_bar(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(200, ge=1, le=500, description="Maximum number of results"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> StockBarResponse:
    try:
        from datetime import date as date_type
        from src.utils.data_processing import parse_json_field

        service = HistoryService(db_manager)
        start = date_type.fromisoformat(start_date) if start_date else None
        end = date_type.fromisoformat(end_date) if end_date else None

        # Fetch more than limit to compensate for normalization dedup shrinkage
        # (e.g. 002460 + 002460.SZ both initially counted but merged to one)
        fetch_limit = min(limit * 3, 500)
        records = db_manager.get_distinct_stocks_from_history(
            start_date=start,
            end_date=end,
            limit=fetch_limit,
        )

        # Deduplicate by normalized code, keeping the record with highest id
        seen: dict = {}
        for record in records:
            display_code = service._display_stock_code(record.code or "")
            norm_code = _normalize_code_for_grouping(display_code)
            if norm_code not in seen or record.id > seen[norm_code].id:
                seen[norm_code] = record

        items = []
        for norm_code in seen:
            record = seen[norm_code]
            raw_result = parse_json_field(getattr(record, "raw_result", None))
            model_used = raw_result.get("model_used") if isinstance(raw_result, dict) else None
            sentiment_score = _coalesce_int(
                record.sentiment_score,
                _raw_result_value(raw_result, "sentiment_score"),
            )
            operation_advice = _coalesce_text(
                record.operation_advice,
                _raw_result_value(raw_result, "operation_advice"),
            )
            action_fields = build_action_fields(
                operation_advice=operation_advice,
                explicit_action=_raw_result_value(raw_result, "action"),
                report_type=record.report_type,
                report_language=normalize_report_language(
                    _raw_result_value(raw_result, "report_language")
                ),
                sentiment_score=sentiment_score,
                guardrail_reason=_extract_guardrail_reason(raw_result),
                align_with_score=True,
            )

            display_stock_code = service._display_stock_code(record.code)
            analysis_count = db_manager.get_analysis_history_paginated(
                code=HistoryService._history_code_filter_candidates(display_stock_code),
                limit=1,
            )[1]
            items.append(
                StockBarItem(
                    id=record.id,
                    stock_code=display_stock_code,
                    stock_name=record.name,
                    report_type=record.report_type,
                    sentiment_score=sentiment_score,
                    operation_advice=operation_advice,
                    action=action_fields["action"],
                    action_label=action_fields["action_label"],
                    analysis_count=analysis_count,
                    last_analysis_time=service._serialize_created_at(record.created_at),
                    model_used=normalize_model_used(model_used),
                    market_phase_summary=service._display_market_phase_summary(
                        record.code,
                        getattr(record, "context_snapshot", None),
                    ),
                )
            )

        items = items[:limit]
        return StockBarResponse(total=len(items), items=items)

    except Exception as e:
        logger.error(f"Failed to query stock bar: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query stock bar: {str(e)}",
            },
        )


@router.get(
    "/{record_id}",
    response_model=AnalysisReport,
    responses={
        200: {"description": "Report details"},
        404: {"description": "Report not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get history report details",
    description="Get a complete historical analysis report by analysis history record ID or query_id"
)
def get_history_detail(
    record_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> AnalysisReport:
    """
    Get history report details.
    
    Get a complete historical analysis report by analysis history record primary key ID or query_id.
    Tries integer primary key ID first; falls back to query_id string lookup if not a valid integer.
    
    Args:
        record_id: Analysis history record primary key ID (integer) or query_id (string)
        db_manager: Database manager dependency
        
    Returns:
        AnalysisReport: Complete analysis report
        
    Raises:
        HTTPException: 404 - Report not found
    """
    try:
        service = HistoryService(db_manager)
        
        # Try integer ID first, fall back to query_id string lookup
        result = service.resolve_and_get_detail(record_id)
        
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"No analysis record found for id/query_id={record_id}"
                }
            )
        
        # Extract price info from context_snapshot
        # Note: using `is None` instead of `or` to avoid treating 0.0 (flat) as missing;
        # also not using `change_60d` (60-day cumulative change) as fallback for intraday change_pct.
        context_snapshot = result.get("context_snapshot")
        analysis_context_pack_overview = extract_analysis_context_pack_overview(context_snapshot)
        market_phase_summary = result.get("market_phase_summary")
        if market_phase_summary is None:
            market_phase_summary = extract_market_phase_summary(context_snapshot)
        api_context_snapshot = sanitize_context_snapshot_for_api(context_snapshot)
        realtime_fields = extract_realtime_detail_fields(context_snapshot)
        current_price = realtime_fields.get("current_price")
        change_pct = realtime_fields.get("change_pct")
        
        raw_result = result.get("raw_result")
        if not isinstance(raw_result, dict):
            raw_result = {}
        report_language = normalize_report_language(
            result.get("report_language")
            or raw_result.get("report_language")
            or (
                context_snapshot.get("report_language")
                if isinstance(context_snapshot, dict)
                else None
            )
        )
        stock_name = get_localized_stock_name(
            result.get("stock_name"),
            result.get("stock_code", ""),
            report_language,
        )

        # Build response model
        meta = ReportMeta(
            id=result.get("id"),
            query_id=result.get("query_id", ""),
            stock_code=result.get("stock_code", ""),
            stock_name=stock_name,
            report_type=result.get("report_type"),
            report_language=report_language,
            created_at=result.get("created_at"),
            current_price=current_price,
            change_pct=change_pct,
            model_used=normalize_model_used(result.get("model_used")),
            market_phase_summary=market_phase_summary,
        )
        
        summary = ReportSummary(
            analysis_summary=result.get("analysis_summary"),
            operation_advice=localize_operation_advice(
                result.get("operation_advice"),
                report_language,
            ),
            action=result.get("action"),
            action_label=result.get("action_label"),
            trend_prediction=localize_trend_prediction(
                result.get("trend_prediction"),
                report_language,
            ),
            sentiment_score=result.get("sentiment_score"),
            sentiment_label=(
                get_sentiment_label(result.get("sentiment_score"), report_language)
                if result.get("sentiment_score") is not None
                else result.get("sentiment_label")
            )
        )
        
        strategy = ReportStrategy(
            ideal_buy=result.get("ideal_buy"),
            secondary_buy=result.get("secondary_buy"),
            stop_loss=result.get("stop_loss"),
            take_profit=result.get("take_profit")
        )
        
        fallback_fundamental = db_manager.get_latest_fundamental_snapshot(
            query_id=result.get("query_id", ""),
            code=result.get("storage_stock_code") or result.get("stock_code", ""),
        )
        extracted_fundamental = extract_fundamental_detail_fields(
            context_snapshot=result.get("context_snapshot"),
            fallback_fundamental_payload=fallback_fundamental,
        )
        extracted_boards = extract_board_detail_fields(
            context_snapshot=result.get("context_snapshot"),
            fallback_fundamental_payload=fallback_fundamental,
        )
        market_structure = extract_market_structure_detail_field(
            result.get("context_snapshot"),
            result.get("raw_result"),
        )

        details = ReportDetails(
            news_content=result.get("news_content"),
            raw_result=result.get("raw_result"),
            context_snapshot=api_context_snapshot,
            analysis_context_pack_overview=analysis_context_pack_overview,
            financial_report=extracted_fundamental.get("financial_report"),
            dividend_metrics=extracted_fundamental.get("dividend_metrics"),
            belong_boards=extracted_boards.get("belong_boards"),
            sector_rankings=extracted_boards.get("sector_rankings"),
            concept_rankings=extracted_boards.get("concept_rankings"),
            market_structure=market_structure,
        )
        
        return AnalysisReport(
            meta=meta,
            summary=summary,
            strategy=strategy,
            details=details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query history details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query history details: {str(e)}"
            }
        )


@router.get(
    "/{record_id}/diagnostics",
    response_model=RunDiagnosticSummaryResponse,
    responses={
        200: {"description": "Run diagnostic summary"},
        404: {"description": "Report not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get history report run diagnostic summary",
    description="Get a user-readable diagnostic summary and sanitized copy text by analysis history record ID or query_id.",
)
def get_history_diagnostics(
    record_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> RunDiagnosticSummaryResponse:
    """
    Get history report run diagnostic summary.
    """
    try:
        service = HistoryService(db_manager)
        summary = service.resolve_and_get_diagnostics(record_id)
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"No analysis record found for id/query_id={record_id}",
                },
            )
        return RunDiagnosticSummaryResponse.model_validate(summary)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query run diagnostic summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query run diagnostic summary: {str(e)}",
            },
        )


@router.get(
    "/{record_id}/flow",
    response_model=RunFlowSnapshot,
    responses={
        200: {"description": "Run flow snapshot"},
        404: {"description": "Report not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get history report run flow",
    description="Get data flow/information flow snapshot by analysis history record ID or query_id.",
)
def get_history_run_flow(
    record_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> RunFlowSnapshot:
    """
    Get history report run flow.
    """
    try:
        service = HistoryService(db_manager)
        snapshot = service.resolve_and_get_run_flow(record_id)
        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "not_found",
                    "message": f"No analysis record found for id/query_id={record_id}",
                },
            )
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query run flow snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query run flow snapshot: {str(e)}",
            },
        )


@router.get(
    "/{record_id}/news",
    response_model=NewsIntelResponse,
    responses={
        200: {"description": "News intelligence list"},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get history report related news",
    description="Get related news intelligence list by analysis history record ID (returns 200 even if empty)"
)
def get_history_news(
    record_id: str,
    limit: int = Query(20, ge=1, le=100, description="Result count limit"),
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> NewsIntelResponse:
    """
    Get history report related news.

    Get related news intelligence list by analysis history record ID or query_id.
    Internally resolves record_id -> query_id.

    Args:
        record_id: Analysis history record primary key ID (integer) or query_id (string)
        limit: Result count limit
        db_manager: Database manager dependency

    Returns:
        NewsIntelResponse: News intelligence list
    """
    try:
        service = HistoryService(db_manager)
        items = service.resolve_and_get_news(record_id=record_id, limit=limit)

        response_items = [
            NewsIntelItem(
                title=item.get("title", ""),
                snippet=item.get("snippet"),
                url=item.get("url", "")
            )
            for item in items
        ]

        return NewsIntelResponse(
            total=len(response_items),
            items=response_items
        )

    except Exception as e:
        logger.error(f"Failed to query news intelligence: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to query news intelligence: {str(e)}"
            }
        )


@router.get(
    "/{record_id}/markdown",
    response_model=MarkdownReportResponse,
    responses={
        200: {"description": "Markdown format report"},
        404: {"description": "Report not found", "model": ErrorResponse},
        500: {"description": "Server error", "model": ErrorResponse},
    },
    summary="Get history report in Markdown format",
    description="Get a complete analysis report in Markdown format by analysis history record ID"
)
def get_history_markdown(
    record_id: str,
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> MarkdownReportResponse:
    """
    Get history report Markdown format content.

    Generate a Markdown report matching the push notification format by analysis history record ID or query_id.

    Args:
        record_id: Analysis history record primary key ID (integer) or query_id (string)
        db_manager: Database manager dependency

    Returns:
        MarkdownReportResponse: Complete report in Markdown format

    Raises:
        HTTPException: 404 - Report not found
        HTTPException: 500 - Report generation failed (internal server error)
    """
    service = HistoryService(db_manager)

    try:
        markdown_content = service.get_markdown_report(record_id)
    except MarkdownReportGenerationError as e:
        logger.error(f"Markdown report generation failed for {record_id}: {e.message}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "generation_failed",
                "message": f"Failed to generate Markdown report: {e.message}"
            }
        )
    except Exception as e:
        logger.error(f"Failed to get Markdown report: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": f"Failed to get Markdown report: {str(e)}"
            }
        )

    if markdown_content is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"No analysis record found for id/query_id={record_id}"
            }
        )

    return MarkdownReportResponse(content=markdown_content)
