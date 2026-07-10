# -*- coding: utf-8 -*-
"""
===================================
Report type enum for analysis-triggered push delivery
===================================

Selects the report format to be pushed when analysis is triggered.
"""

from enum import Enum


class ReportType(str, Enum):
    """
    Select the report format to be pushed when analysis is triggered

    Inherits from str to allow direct comparison and serialization with strings.
    """
    SIMPLE = "simple"  # Concise report: uses generate_single_stock_report
    FULL = "full"      # Full report: uses generate_dashboard_report
    BRIEF = "brief"    # Brief mode: 3-5 sentence summary, suitable for mobile/push

    @classmethod
    def from_str(cls, value: str) -> "ReportType":
        """
        Safe conversion from string to enum value

        Args:
            value: string value

        Returns:
            The corresponding enumeration value; invalid input returns default value SIMPLE
        """
        try:
            normalized = value.lower().strip()
            if normalized == "detailed":
                normalized = cls.FULL.value
            return cls(normalized)
        except (ValueError, AttributeError):
            return cls.SIMPLE
    
    @property
    def display_name(self) -> str:
        """Get the name used for display"""
        return {
            ReportType.SIMPLE: "Concise Report",
            ReportType.FULL: "Full Report",
            ReportType.BRIEF: "Brief Report",
        }.get(self, "Concise Report")
