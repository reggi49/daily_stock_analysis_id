# -*- coding: utf-8 -*-
"""
===================================
Analysis Models
===================================

Responsibilities:
1. Define analysis request and response models
2. Define task status models
3. Define async task queue related models
"""

from typing import Optional, List, Any, Literal
from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from src.utils.analysis_metadata import SELECTION_SOURCE_PATTERN


class TaskStatusEnum(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"


AnalysisPhase = Literal["auto", "premarket", "intraday", "postmarket"]


class AnalyzeRequest(BaseModel):
    """Analysis request parameters"""
    
    stock_code: Optional[str] = Field(
        None, 
        description="Single stock code", 
        json_schema_extra={"example": "600519"},
    )
    stock_codes: Optional[List[str]] = Field(
        None, 
        description="Multiple stock codes (mutually exclusive with stock_code)",
        json_schema_extra={"example": ["600519", "000858"]},
    )
    report_type: str = Field(
        "detailed",
        description="Report type: simple / detailed / full / brief",
        pattern="^(simple|detailed|full|brief)$",
    )
    force_refresh: bool = Field(
        False,
        description="Whether to force refresh (ignore cache)"
    )
    async_mode: bool = Field(
        False,
        description="Whether to use async mode"
    )
    analysis_phase: AnalysisPhase = Field(
        "auto",
        description="Analysis phase override: auto(auto-infer) / premarket / intraday / postmarket",
    )
    stock_name: Optional[str] = Field(
        None,
        description="User-selected stock name (provided during autocomplete)",
        json_schema_extra={"example": "Kweichow Moutai"},
    )
    original_query: Optional[str] = Field(
        None,
        description="User original input (e.g. Moutai, gzmt, 600519)",
        json_schema_extra={"example": "Moutai"},
    )
    selection_source: Optional[str] = Field(
        None,
        description="Stock selection source: manual | autocomplete | import | image",
        pattern=SELECTION_SOURCE_PATTERN,
        json_schema_extra={"example": "autocomplete"},
    )
    notify: bool = Field(
        True,
        description="Whether to send push notifications (Telegram/WeChat Work, etc.)"
    )
    report_language: Optional[Literal["zh", "en", "ko"]] = Field(
        None,
        validation_alias=AliasChoices("report_language", "reportLanguage"),
        description="Analysis report output language; uses global REPORT_LANGUAGE when not provided",
    )
    skills: Optional[List[str]] = Field(
        None,
        validation_alias=AliasChoices("skills", "strategies"),
        description="Strategy skill ID list for this analysis; compatible with legacy strategies field",
        json_schema_extra={"example": ["bull_trend", "growth_quality"]},
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "report_type": "detailed",
            "force_refresh": False,
            "async_mode": False,
            "analysis_phase": "auto",
            "stock_name": "Analysis task has been added to the queue",
            "original_query": "Analysis task has been added to the queue",
            "selection_source": "autocomplete",
            "notify": True,
            "report_language": "zh",
            "skills": ["bull_trend"]
        }
    })


class MarketReviewRequest(BaseModel):
    """Market review trigger parameters."""

    send_notification: bool = Field(
        True,
        description="Whether to send push notification after market review completes",
    )
    report_language: Optional[Literal["zh", "en", "ko"]] = Field(
        None,
        validation_alias=AliasChoices("report_language", "reportLanguage"),
        description="Market review report output language; uses global REPORT_LANGUAGE when not provided",
    )


class MarketReviewAccepted(BaseModel):
    """Market review background task accepted response."""

    status: str = Field("accepted", description="Submission status")
    message: str = Field(..., description="Notification message")
    send_notification: bool = Field(..., description="Whether to send notification")
    trace_id: Optional[str] = Field(
        None,
        description="Diagnostic trace ID for this background task",
    )
    task_id: Optional[str] = Field(
        None,
        description="Task ID (only returned when the task is actually submitted)",
    )


class AnalysisResultResponse(BaseModel):
    """Analysis result response model."""
    
    query_id: str = Field(..., description="Analysis record unique identifier")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    report: Optional[Any] = Field(None, description="Analysis report")
    diagnostic_summary: Optional[Any] = Field(None, description="Run diagnostic summary")
    created_at: str = Field(..., description="Creation time")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "query_id": "abc123def456",
            "stock_code": "600519",
            "stock_name": "Analysis task has been added to the queue",
            "report": {
                "summary": {
                    "sentiment_score": 75,
                    "operation_advice": "stock"
                }
            },
            "created_at": "2024-01-01T12:00:00"
        }
    })


class TaskAccepted(BaseModel):
    """Async task accepted response."""
    
    task_id: str = Field(..., description="Task ID, used for status queries")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    status: str = Field(
        ..., 
        description="Task status",
        pattern="^(pending|processing)$"
    )
    message: Optional[str] = Field(None, description="Notification message")
    analysis_phase: AnalysisPhase = Field("auto", description="Requested analysis phase")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "status": "pending",
            "message": "Analysis task accepted",
            "analysis_phase": "auto"
        }
    })


class BatchTaskAcceptedItem(BaseModel):
    """Single successfully submitted item in a batch async task."""

    task_id: str = Field(..., description="Task ID, used for status queries")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    stock_code: str = Field(..., description="Stock code")
    status: str = Field(
        ...,
        description="Task status",
        pattern="^(pending|processing)$"
    )
    message: Optional[str] = Field(None, description="Notification message")
    analysis_phase: AnalysisPhase = Field("auto", description="Requested analysis phase")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "stock_code": "600519",
            "status": "pending",
            "message": "Analysis task has been added to the queue: 600519",
            "analysis_phase": "auto"
        }
    })


class BatchDuplicateTaskItem(BaseModel):
    """Duplicate submission item in a batch async task."""

    stock_code: str = Field(..., description="Stock code")
    existing_task_id: str = Field(..., description="Existing task ID")
    message: str = Field(..., description="Error message")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "existing_task_id": "task_existing_123",
            "message": "stock 600519 Under analysis (task_id: task_existing_123)"
        }
    })


class BatchTaskAcceptedResponse(BaseModel):
    """Batch async task accepted response."""

    accepted: List[BatchTaskAcceptedItem] = Field(default_factory=list, description="Successfully submitted task list")
    duplicates: List[BatchDuplicateTaskItem] = Field(default_factory=list, description="Skipped duplicate task list")
    message: str = Field(..., description="Summary message")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "accepted": [
                {
                    "task_id": "task_abc123",
                    "stock_code": "600519",
                    "status": "pending",
                    "message": "Analysis task has been added to the queue: 600519",
                    "analysis_phase": "auto"
                }
            ],
            "duplicates": [
                {
                    "stock_code": "000858",
                    "existing_task_id": "task_existing_456",
                    "message": "stock 000858 Under analysis (task_id: task_existing_456)"
                }
            ],
            "message": "tasks 1 tasks，1 duplicates skipped"
        }
    })


class TaskStatus(BaseModel):
    """Task status model"""
    
    task_id: str = Field(..., description="Task ID")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    status: TaskStatusEnum = Field(
        ..., 
        description="Task status",
    )
    progress: Optional[int] = Field(
        None, 
        description="Progress percentage (0-100)",
        ge=0,
        le=100
    )
    result: Optional[AnalysisResultResponse] = Field(
        None, 
        description="Analysis result (only present when completed)"
    )
    market_review_report: Optional[str] = Field(
        None,
        description="Report text returned from market review task (market review tasks only)",
    )
    market_review_payload: Optional[Any] = Field(
        None,
        description="Structured market-review payload for API/Web consumers.",
    )
    error: Optional[str] = Field(
        None, 
        description="Error message (only present when failed)"
    )
    stock_name: Optional[str] = Field(None, description="Stock name")
    original_query: Optional[str] = Field(None, description="User original input")
    selection_source: Optional[str] = Field(
        None,
        description="Selection source",
        pattern=SELECTION_SOURCE_PATTERN,
    )
    analysis_phase: Optional[AnalysisPhase] = Field(
        None,
        description="Requested analysis phase; may be empty for historical DB fallbacks without persistent fields",
    )
    skills: Optional[List[str]] = Field(None, description="Strategy skill ID list used for this task")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "task_abc123",
            "status": "completed",
            "progress": 100,
            "result": None,
            "market_review_report": None,
            "error": None,
            "stock_name": "Analysis task has been added to the queue",
            "original_query": "Analysis task has been added to the queue",
            "selection_source": "autocomplete",
            "analysis_phase": "auto",
            "skills": ["bull_trend"]
        }
    })


class TaskInfo(BaseModel):
    """
    Task details model

    Used for task list and SSE event delivery
    """
    
    task_id: str = Field(..., description="Task ID")
    trace_id: Optional[str] = Field(None, description="Diagnostic trace ID")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    status: TaskStatusEnum = Field(..., description="Task status")
    progress: int = Field(0, description="Progress percentage (0-100)", ge=0, le=100)
    message: Optional[str] = Field(None, description="Status message")
    report_type: str = Field("detailed", description="Report type")
    created_at: str = Field(..., description="Creation time")
    started_at: Optional[str] = Field(None, description="Execution start time")
    completed_at: Optional[str] = Field(None, description="Completion time")
    error: Optional[str] = Field(None, description="Error message (only present when failed)")
    original_query: Optional[str] = Field(None, description="User original input")
    selection_source: Optional[str] = Field(
        None,
        description="Selection source",
        pattern=SELECTION_SOURCE_PATTERN,
    )
    analysis_phase: AnalysisPhase = Field("auto", description="Requested analysis phase")
    skills: Optional[List[str]] = Field(None, description="Strategy skill ID list used for this task")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "task_id": "abc123def456",
            "stock_code": "600519",
            "stock_name": "Analysis task has been added to the queue",
            "status": "processing",
            "progress": 50,
            "message": "Under analysis...",
            "report_type": "detailed",
            "created_at": "2026-02-05T10:30:00",
            "started_at": "2026-02-05T10:30:01",
            "completed_at": None,
            "error": None,
            "original_query": "Analysis task has been added to the queue",
            "selection_source": "autocomplete",
            "analysis_phase": "auto",
            "skills": ["bull_trend"]
        }
    })


class TaskListResponse(BaseModel):
    """Task list response model."""
    
    total: int = Field(..., description="Total task count")
    pending: int = Field(..., description="Number of pending tasks")
    processing: int = Field(..., description="Number of processing tasks")
    tasks: List[TaskInfo] = Field(..., description="Task list")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 3,
            "pending": 1,
            "processing": 2,
            "tasks": []
        }
    })


class DuplicateTaskErrorResponse(BaseModel):
    """Duplicate task error response model."""
    
    error: str = Field("duplicate_task", description="Error type")
    message: str = Field(..., description="Error message")
    stock_code: str = Field(..., description="Stock code")
    existing_task_id: str = Field(..., description="Existing task ID")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "duplicate_task",
            "message": "stock 600519 Under analysis",
            "stock_code": "600519",
            "existing_task_id": "abc123def456"
        }
    })
