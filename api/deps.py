# -*- coding: utf-8 -*-
"""
===================================
API Dependency Injection Module
===================================

Responsibilities:
1. Provide database Session dependency
2. Provide configuration dependency
3. Provide service layer dependencies
"""

from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from src.storage import DatabaseManager
from src.config import get_config, Config
from src.services.system_config_service import SystemConfigService
from src.services.runtime_scheduler import RuntimeSchedulerService


def get_db() -> Generator[Session, None, None]:
    """
    Get database Session dependency.
    
    Uses FastAPI dependency injection to ensure the Session is automatically
    closed after the request ends.
    
    Yields:
        Session: SQLAlchemy Session object
        
    Example:
        @router.get("/items")
        async def get_items(db: Session = Depends(get_db)):
            ...
    """
    db_manager = DatabaseManager.get_instance()
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


def get_config_dep() -> Config:
    """
    Get configuration dependency.
    
    Returns:
        Config: Configuration singleton object
    """
    return get_config()


def get_database_manager() -> DatabaseManager:
    """
    Get database manager dependency.
    
    Returns:
        DatabaseManager: Database manager singleton object
    """
    return DatabaseManager.get_instance()


def get_system_config_service(request: Request) -> SystemConfigService:
    """Get app-lifecycle shared SystemConfigService instance."""
    service = getattr(request.app.state, "system_config_service", None)
    if service is None:
        service = SystemConfigService()
        request.app.state.system_config_service = service
    return service


def get_runtime_scheduler_service(request: Request) -> RuntimeSchedulerService:
    """Get app-lifecycle shared RuntimeSchedulerService instance."""
    service = getattr(request.app.state, "runtime_scheduler_service", None)
    if service is None:
        service = RuntimeSchedulerService()
        request.app.state.runtime_scheduler_service = service
    return service
