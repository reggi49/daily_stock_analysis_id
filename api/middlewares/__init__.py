# -*- coding: utf-8 -*-
"""
===================================
API Middleware Module Initialization
===================================

Responsibilities:
1. Export all middlewares
"""

from api.middlewares.error_handler import ErrorHandlerMiddleware

__all__ = ["ErrorHandlerMiddleware"]
