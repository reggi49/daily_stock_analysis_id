# -*- coding: utf-8 -*-
"""
===================================
Stock Data Models
===================================

Responsibilities:
1. Define stock realtime quote model
2. Define historical K-line data model
"""

from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class StockQuote(BaseModel):
    """Stock realtime quote."""
    
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    current_price: float = Field(..., description="Current price")
    change: Optional[float] = Field(None, description="Price change")
    change_percent: Optional[float] = Field(None, description="Price change percent (%)")
    open: Optional[float] = Field(None, description="Opening price")
    high: Optional[float] = Field(None, description="Highest price")
    low: Optional[float] = Field(None, description="Lowest price")
    prev_close: Optional[float] = Field(None, description="Previous closing price")
    volume: Optional[float] = Field(None, description="Volume (shares)")
    amount: Optional[float] = Field(None, description="Turnover (currency)")
    update_time: Optional[str] = Field(None, description="Update time")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "Kweichow Moutai",
            "current_price": 1800.00,
            "change": 15.00,
            "change_percent": 0.84,
            "open": 1785.00,
            "high": 1810.00,
            "low": 1780.00,
            "prev_close": 1785.00,
            "volume": 10000000,
            "amount": 18000000000,
            "update_time": "2024-01-01T15:00:00"
        }
    })


class KLineData(BaseModel):
    """K-line data point."""
    
    date: str = Field(..., description="Date")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    close: float = Field(..., description="Closing price")
    volume: Optional[float] = Field(None, description="Volume")
    amount: Optional[float] = Field(None, description="Turnover")
    change_percent: Optional[float] = Field(None, description="Price change percent (%)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "date": "2024-01-01",
            "open": 1785.00,
            "high": 1810.00,
            "low": 1780.00,
            "close": 1800.00,
            "volume": 10000000,
            "amount": 18000000000,
            "change_percent": 0.84
        }
    })


class ExtractItem(BaseModel):
    """Single extraction result (code, name, confidence)."""

    code: Optional[str] = Field(None, description="Stock code, None indicates parsing failure")
    name: Optional[str] = Field(None, description="Stock name (if available)")
    confidence: str = Field("medium", description="Confidence: high/medium/low")


class ExtractFromImageResponse(BaseModel):
    """Image stock code extraction response."""

    codes: List[str] = Field(..., description="Extracted stock codes (deduplicated, backward compatible)")
    items: List[ExtractItem] = Field(default_factory=list, description="Extraction result details (code+name+confidence)")
    raw_text: Optional[str] = Field(None, description="Raw LLM response (for debugging)")


class StockHistoryResponse(BaseModel):
    """Stock historical data response."""
    
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    period: str = Field(..., description="K-line period")
    data: List[KLineData] = Field(default_factory=list, description="K-line data list")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "Kweichow Moutai",
            "period": "daily",
            "data": []
        }
    })
