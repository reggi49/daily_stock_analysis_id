# -*- coding: utf-8 -*-
"""
===================================
Real-time market unified type definition & circuit breaker
===================================

Design goals:
1. Unify the real-time market return structure of various data sources
2. Implement circuit breaker/cool-down mechanism to avoid repeated requests when consecutive failures occur
3. Support multiple data source failover

Usage:
- All Fetcher's get_realtime_quote() returns a uniform UnifiedRealtimeQuote
- CircuitBreaker manages the circuit breaker status of each data source
"""

import logging
import time
from threading import RLock
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Union
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================
# Type conversion utilities
# ============================================
# safe_float / safe_int: Safe type conversion (str/float/int/NaN)
# Used for converting values from various data sources into proper types.

def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """
    Safely convert to floating point.

    Handles the following cases:
    - None / empty string -> default
    - pandas NaN / numpy NaN -> default
    - numeric string -> float
    - Already a numeric value -> float
    
    Args:
        val: value to be converted
        default: default value when conversion fails
        
    Returns:
        Converted floating point number, or default value
    """
    try:
        if val is None:
            return default
        
        # Handle strings
        if isinstance(val, str):
            val = val.strip()
            if val == "" or val == "-" or val == "--":
                return default
        
        # Handle pandas/numpy NaN
        # Use math.isnan instead of pd.isna to avoid forcing pandas dependency
        import math
        try:
            if math.isnan(float(val)):
                return default
        except (ValueError, TypeError):
            pass
        
        return float(val)
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert to integer.

    First convert to float, then round to handle cases like "123.0".
    
    Args:
        val: value to be converted
        default: default value when conversion fails
        
    Returns:
        Converted integer, or default value
    """
    f_val = safe_float(val, default=None)
    if f_val is not None:
        return int(f_val)
    return default


class RealtimeSource(Enum):
    """Real-time market data source."""
    EFINANCE = "efinance"           # EastMoney (efinance library)
    AKSHARE_EM = "akshare_em"       # EastMoney (akshare library)
    AKSHARE_SINA = "akshare_sina"   # Sina Finance
    AKSHARE_QQ = "akshare_qq"       # Tencent Finance
    TUSHARE = "tushare"             # Tushare Pro
    TICKFLOW = "tickflow"           # TickFlow
    TENCENT = "tencent"             # Tencent direct connection
    SINA = "sina"                   # Sina direct connection
    STOOQ = "stooq"                 # Stooq US stock fallback
    LONGBRIDGE = "longbridge"       # Longbridge (US/HK stock fallback)
    FALLBACK = "fallback"           # Degraded fallback


@dataclass
class UnifiedRealtimeQuote:
    """
    Unified real-time market data structure.

    Design principles:
    - Fields returned by each data source may differ; missing fields use None
    - Use getattr(quote, field, None) for guaranteed compatibility
    - source field tags the data source for easy debugging
    """
    code: str
    name: str = ""
    source: RealtimeSource = RealtimeSource.FALLBACK

    # === Data quality metadata (populated by DataFetcherManager) ===
    fetched_at: Optional[str] = None             # Fetch time of this system (ISO 8601 datetime)
    provider_timestamp: Optional[str] = None     # Provider actual quote time (ISO 8601 datetime)
    is_stale: Optional[bool] = None              # True when provider_timestamp exceeds minimum TTL threshold
    stale_seconds: Optional[int] = None          # Seconds between provider_timestamp and fetched_at
    fallback_from: Optional[str] = None          # Failed primary source token for whole-source fallback
    market: Optional[str] = None                 # Market tag (cn/hk/us/jp/kr/tw)
    currency: Optional[str] = None               # Quote currency (JPY/KRW/TWD/USD/HKD/CNY etc.)
    data_quality: Optional[str] = None           # ok/partial/unavailable
    missing_fields: Optional[list[str]] = None   # Provider missing key fields
    
    # === Core price data (available from almost all sources) ===
    price: Optional[float] = None           # Latest price
    change_pct: Optional[float] = None      # Change percentage (%)
    change_amount: Optional[float] = None   # Change amount
    
    # === Volume and price indicators (some sources may lack these) ===
    volume: Optional[int] = None            # Trading volume (shares, consistent with historical daily data)
    amount: Optional[float] = None          # Trading amount (yuan)
    volume_ratio: Optional[float] = None    # Volume ratio
    turnover_rate: Optional[float] = None   # Turnover rate (%)
    amplitude: Optional[float] = None       # Amplitude (%)
    
    # === Price range ===
    open_price: Optional[float] = None      # Opening price
    high: Optional[float] = None            # Highest price
    low: Optional[float] = None             # Lowest price
    pre_close: Optional[float] = None       # Previous close price
    
    # === Valuation indicators (only full interfaces like EastMoney have these) ===
    pe_ratio: Optional[float] = None        # P/E ratio (dynamic)
    pb_ratio: Optional[float] = None        # P/B ratio
    total_mv: Optional[float] = None        # Total market value (yuan)
    circ_mv: Optional[float] = None         # Circulating market value (yuan)
    
    # === Other indicators ===
    change_60d: Optional[float] = None      # 60-day change percentage (%)
    high_52w: Optional[float] = None        # 52-week high
    low_52w: Optional[float] = None         # 52-week low
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (filter out None values)."""
        result = {
            'code': self.code,
            'name': self.name,
            'source': self.source.value,
        }
        # Only add non None fields
        optional_fields = [
            'fetched_at', 'provider_timestamp', 'is_stale', 'stale_seconds',
            'fallback_from', 'market', 'currency', 'data_quality', 'missing_fields',
            'price', 'change_pct', 'change_amount', 'volume', 'amount',
            'volume_ratio', 'turnover_rate', 'amplitude',
            'open_price', 'high', 'low', 'pre_close',
            'pe_ratio', 'pb_ratio', 'total_mv', 'circ_mv',
            'change_60d', 'high_52w', 'low_52w'
        ]
        for f in optional_fields:
            val = getattr(self, f, None)
            if val is not None:
                result[f] = val
        return result
    
    def has_basic_data(self) -> bool:
        """Check if basic price data is available."""
        return self.price is not None and self.price > 0
    
    def has_volume_data(self) -> bool:
        """Check whether there is volume and price data."""
        return self.volume_ratio is not None or self.turnover_rate is not None


@dataclass
class ChipDistribution:
    """
    Chip distribution data.

    Reflects position cost distribution and profitability.
    """
    code: str
    date: str = ""
    source: str = "akshare"
    
    # Profit situation
    profit_ratio: float = 0.0     # Profit ratio (0-1)
    avg_cost: float = 0.0         # Average cost
    
    # Chip concentration
    cost_90_low: float = 0.0      # 90% chip cost lower bound
    cost_90_high: float = 0.0     # 90% chip cost upper bound
    concentration_90: float = 0.0  # 90% chip concentration (smaller = more concentrated)
    
    cost_70_low: float = 0.0      # 70% chip cost lower bound
    cost_70_high: float = 0.0     # 70% chip cost upper bound
    concentration_70: float = 0.0  # 70% chip concentration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'code': self.code,
            'date': self.date,
            'source': self.source,
            'profit_ratio': self.profit_ratio,
            'avg_cost': self.avg_cost,
            'cost_90_low': self.cost_90_low,
            'cost_90_high': self.cost_90_high,
            'concentration_90': self.concentration_90,
            'concentration_70': self.concentration_70,
        }
    
    def get_chip_status(self, current_price: float) -> str:
        """
        Get chip status description.
        
        Args:
            current_price: current stock price
            
        Returns:
            Chip status description
        """
        status_parts = []
        
        # Profit ratio analysis
        if self.profit_ratio >= 0.9:
            status_parts.append("Extremely high profit zone (profit > 90%)")
        elif self.profit_ratio >= 0.7:
            status_parts.append("High profit zone (profit 70-90%)")
        elif self.profit_ratio >= 0.5:
            status_parts.append("Moderate profit zone (profit 50-70%)")
        elif self.profit_ratio >= 0.3:
            status_parts.append("Moderate trap zone (trap 50-70%)")
        elif self.profit_ratio >= 0.1:
            status_parts.append("High trap zone (trap 70-90%)")
        else:
            status_parts.append("Extremely high trap zone (trap > 90%)")
        
        # Chip concentration analysis (90% concentration < 10% means concentrated)
        if self.concentration_90 < 0.08:
            status_parts.append("Chips highly concentrated")
        elif self.concentration_90 < 0.15:
            status_parts.append("Chips relatively concentrated")
        elif self.concentration_90 < 0.25:
            status_parts.append("Moderate chip dispersion")
        else:
            status_parts.append("Chips relatively dispersed")
        
        # Cost and current price relationship
        if current_price > 0 and self.avg_cost > 0:
            cost_diff = (current_price - self.avg_cost) / self.avg_cost * 100
            if cost_diff > 20:
                status_parts.append(f"Price {cost_diff:.1f}% above average cost")
            elif cost_diff > 5:
                status_parts.append(f"Price slightly above cost by {cost_diff:.1f}%")
            elif cost_diff > -5:
                status_parts.append("Price near average cost")
            else:
                status_parts.append(f"Price {abs(cost_diff):.1f}% below average cost")
        
        return ", ".join(status_parts)


class CircuitBreaker:
    """
    Manage data source circuit breaker / cool-down status.
    
    Strategy:
    - After N consecutive failures, enter the open (fuse) state
    - Skip this data source during the circuit breaker period
    - Automatically returns to half-open state after cool-down time
    - A single success in half-open state results in full recovery; if it fails, continue to fuse
    
    State machine:
    CLOSED (normal) --fail N times--> OPEN (fused) --cool-down elapsed--> HALF_OPEN (half open)
    HALF_OPEN --success--> CLOSED
    HALF_OPEN --fail--> OPEN
    """
    
    # Status constants
    CLOSED = "closed"      # Normal state
    OPEN = "open"          # Fused state (unavailable)
    HALF_OPEN = "half_open"  # Half-open state (probing requests)
    
    def __init__(
        self,
        failure_threshold: int = 3,       # Consecutive failure threshold
        cooldown_seconds: float = 300.0,  # Cool-down time (seconds), default 5 minutes
        half_open_max_calls: int = 1      # Max attempts in half-open state
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        
        # Cool-down tracking {source_name: {state, failures, last_failure_time, half_open_calls}}
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
    
    def _get_state_locked(self, source: str) -> Dict[str, Any]:
        """Get or initialize data source state (caller must hold the lock)."""
        if source not in self._states:
            self._states[source] = {
                'state': self.CLOSED,
                'failures': 0,
                'last_failure_time': 0.0,
                'half_open_calls': 0
            }
        return self._states[source]
    
    def is_available(self, source: str) -> bool:
        """
        Check if the data source is available for requests.
        
        Returns True if the source can be tried, False if it should be skipped.
        """
        with self._lock:
            state = self._get_state_locked(source)
            current_time = time.time()

            if state['state'] == self.CLOSED:
                return True

            if state['state'] == self.OPEN:
                # Check cool-down time
                time_since_failure = current_time - state['last_failure_time']
                if time_since_failure >= self.cooldown_seconds:
                    # Cool-down completed, enter half-open state
                    state['state'] = self.HALF_OPEN
                    state['half_open_calls'] = 0
                    state['last_failure_time'] = current_time
                    logger.info(f"[CircuitBreaker] {source} cool-down completed, entering half-open state")
                    # Fall through to HALF_OPEN check below
                else:
                    remaining = self.cooldown_seconds - time_since_failure
                    logger.debug(f"[CircuitBreaker] {source} in fused state, remaining cool-down: {remaining:.0f}s")
                    return False

            if state['state'] == self.HALF_OPEN:
                if state['half_open_calls'] < self.half_open_max_calls:
                    state['half_open_calls'] += 1
                    return True
                # All probe quotas used; if cool-down expires without a
                # record_success/record_failure callback, reset to prevent
                # getting permanently stuck in HALF_OPEN.
                time_since_failure = current_time - state['last_failure_time']
                if time_since_failure >= self.cooldown_seconds:
                    state['half_open_calls'] = 1
                    state['last_failure_time'] = current_time
                    logger.info(f"[CircuitBreaker] {source} half-open state probe timeout, result uncertain")
                    return True
                return False

            return True
    
    def record_inconclusive(self, source: str) -> None:
        """Record inconclusive probe result (e.g. return None).

        Only affects HALF_OPEN state: transitions back to OPEN so it can be
        re-probed after cool-down. No operation in CLOSED state, does not
        affect failure count.
        """
        with self._lock:
            state = self._get_state_locked(source)
            if state['state'] == self.HALF_OPEN:
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                state['last_failure_time'] = time.time()
                logger.info(f"[CircuitBreaker] {source} half-open detection result inconclusive, re-entering cool-down")

    def record_success(self, source: str) -> None:
        """Record a successful request."""
        with self._lock:
            state = self._get_state_locked(source)

            if state['state'] == self.HALF_OPEN:
                # Successful in half-open state, full recovery
                logger.info(f"[CircuitBreaker] {source} half-open request successful, full recovery")

            # Reset state
            state['state'] = self.CLOSED
            state['failures'] = 0
            state['half_open_calls'] = 0
    
    def record_failure(self, source: str, error: Optional[str] = None) -> None:
        """Record a failed request."""
        with self._lock:
            state = self._get_state_locked(source)
            current_time = time.time()

            state['failures'] += 1
            state['last_failure_time'] = current_time

            if state['state'] == self.HALF_OPEN:
                # Failed in half-open state, continue to fuse
                state['state'] = self.OPEN
                state['half_open_calls'] = 0
                logger.warning(f"[CircuitBreaker] {source} half-open request failed, continuing fuse for {self.cooldown_seconds}s")
            elif state['failures'] >= self.failure_threshold:
                # Threshold reached, trigger circuit breaker
                state['state'] = self.OPEN
                logger.warning(f"[CircuitBreaker] {source} consecutive failures {state['failures']}, entering fused state "
                              f"(cool-down {self.cooldown_seconds}s)")
                if error:
                    logger.warning(f"[CircuitBreaker] final error: {error}")
    
    def get_status(self) -> Dict[str, str]:
        """Get all data source statuses."""
        with self._lock:
            return {source: info['state'] for source, info in self._states.items()}
    
    def reset(self, source: Optional[str] = None) -> None:
        """Reset fuse status."""
        with self._lock:
            if source:
                if source in self._states:
                    del self._states[source]
            else:
                self._states.clear()


# Global circuit breaker instance (dedicated to real-time quotes)
_realtime_circuit_breaker = CircuitBreaker(
    failure_threshold=3,      # Fuse after 3 consecutive failures
    cooldown_seconds=300.0,   # 5-minute cool-down
    half_open_max_calls=1
)

# Chip interface fuse (less stable interface)
_chip_circuit_breaker = CircuitBreaker(
    failure_threshold=2,      # Fuse after 2 consecutive failures
    cooldown_seconds=600.0,   # 10-minute cool-down
    half_open_max_calls=1
)


def get_realtime_circuit_breaker() -> CircuitBreaker:
    """Get real-time market circuit breaker."""
    return _realtime_circuit_breaker


def get_chip_circuit_breaker() -> CircuitBreaker:
    """Get chip interface circuit breaker."""
    return _chip_circuit_breaker
