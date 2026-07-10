# -*- coding: utf-8 -*-
"""
===================================
Stock Data Access Layer
===================================

Responsibilities:
1. Encapsulate database operations for stock data
2. Provide daily data query interface
"""

import logging
from datetime import date
from typing import Optional, List, Dict, Any

import pandas as pd
from sqlalchemy import and_, desc, select

from src.storage import DatabaseManager, StockDaily

logger = logging.getLogger(__name__)


class StockRepository:
    """
    Stock data access layer
    
    Encapsulates database operations for the StockDaily table
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize the data access layer
        
        Args:
            db_manager: Database manager (optional, defaults to singleton)
        """
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_latest(self, code: str, days: int = 2) -> List[StockDaily]:
        """
        Fetch the most recent N days of data
        
        Args:
            code: Stock code
            days: Number of days to fetch
            
        Returns:
            List of StockDaily objects (sorted by date descending)
        """
        try:
            return self.db.get_latest_data(code, days)
        except Exception as e:
            logger.error(f"Failed to fetch latest data: {e}")
            return []
    
    def get_range(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> List[StockDaily]:
        """
        Fetch data within a specified date range
        
        Args:
            code: Stock code
            start_date: Start date
            end_date: End date
            
        Returns:
            List of StockDaily objects
        """
        try:
            return self.db.get_data_range(code, start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch date-range data: {e}")
            return []
    
    def save_dataframe(
        self,
        df: pd.DataFrame,
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        Save a DataFrame to the database
        
        Args:
            df: DataFrame containing daily data
            code: Stock code
            data_source: Data source
            
        Returns:
            Number of records saved
        """
        try:
            return self.db.save_daily_data(df, code, data_source)
        except Exception as e:
            logger.error(f"Failed to save daily data: {e}")
            return 0
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        Check whether data exists for a given date
        
        Args:
            code: Stock code
            target_date: Target date (defaults to today)
            
        Returns:
            Whether data exists
        """
        try:
            return self.db.has_today_data(code, target_date)
        except Exception as e:
            logger.error(f"Failed to check data existence: {e}")
            return False
    
    def get_analysis_context(
        self, 
        code: str, 
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch analysis context
        
        Args:
            code: Stock code
            target_date: Target date
            
        Returns:
            Analysis context dictionary
        """
        try:
            return self.db.get_analysis_context(code, target_date)
        except Exception as e:
            logger.error(f"Failed to fetch analysis context: {e}")
            return None

    def get_start_daily(self, *, code: str, analysis_date: date) -> Optional[StockDaily]:
        """Return StockDaily for analysis_date (preferred) or nearest previous date."""
        with self.db.get_session() as session:
            row = session.execute(
                select(StockDaily)
                .where(and_(StockDaily.code == code, StockDaily.date <= analysis_date))
                .order_by(desc(StockDaily.date))
                .limit(1)
            ).scalar_one_or_none()
            return row

    def get_daily_on_date(self, *, code: str, target_date: date) -> Optional[StockDaily]:
        """Return StockDaily for the exact target_date without trading-day fallback."""
        with self.db.get_session() as session:
            row = session.execute(
                select(StockDaily)
                .where(and_(StockDaily.code == code, StockDaily.date == target_date))
                .limit(1)
            ).scalar_one_or_none()
            return row

    def get_forward_bars(self, *, code: str, analysis_date: date, eval_window_days: int) -> List[StockDaily]:
        """Return forward daily bars after analysis_date, up to eval_window_days."""
        with self.db.get_session() as session:
            rows = session.execute(
                select(StockDaily)
                .where(and_(StockDaily.code == code, StockDaily.date > analysis_date))
                .order_by(StockDaily.date)
                .limit(eval_window_days)
            ).scalars().all()
            return list(rows)
