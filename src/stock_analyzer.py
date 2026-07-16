# -*- coding: utf-8 -*-
"""
===================================
Trend Trading Analyzer - Based on user trading concept
===================================

Trading Philosophy Core Principles：
1. strict strategy - Don't chase high，Pursue the success rate of each transaction
2. Trend trading - MA5>MA10>MA20 multi-head arrangement，Go with the flow
3. Efficiency first - Pay attention to stocks with good chip structure
4. Buy some preferences - exist MA5/MA10 Buy nearby

technical standards：
- multi-head arrangement：MA5 > MA10 > MA20
- Quantitative energy analysis：(Close - MA5) / MA5 < 5%（Don't chase high）
- energy form：Shrink callback priority
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum

import pandas as pd
import numpy as np

from src.config import get_config
from src.schemas.decision_scale import signal_key_for_score

logger = logging.getLogger(__name__)


class TrendStatus(Enum):
    """Trend status enum"""
    STRONG_BULL = "Strong bull"      # MA5 > MA10 > MA20，And the distance is expanded
    BULL = "multi-head arrangement"             # MA5 > MA10 > MA20
    WEAK_BULL = "Weak bulls"        # MA5 > MA10，but MA10 < MA20
    CONSOLIDATION = "consolidation"        # moving average wrapping
    WEAK_BEAR = "Weak short"        # MA5 < MA10，but MA10 > MA20
    BEAR = "Short arrangement"             # MA5 < MA10 < MA20
    STRONG_BEAR = "Strong short position"      # MA5 < MA10 < MA20，And the distance is expanded


class VolumeStatus(Enum):
    """Energy status enumeration"""
    HEAVY_VOLUME_UP = "Rising on heavy volume"       # Both volume and price rise
    HEAVY_VOLUME_DOWN = "Falling on heavy volume"     # Heavy volume kills the price
    SHRINK_VOLUME_UP = "Shrinking and rising"      # Infinite rise
    SHRINK_VOLUME_DOWN = "Taper callback"    # Taper callback（good）
    NORMAL = "Energy is normal"


class BuySignal(Enum):
    """Buy signal enum"""
    STRONG_BUY = "Strong buy"       # Multiple conditions met
    BUY = "Buy"                  # Basic conditions are met
    HOLD = "hold"                 # Already held can continue
    WAIT = "wait and see"                 # Waiting for a better time
    SELL = "sell"                 # trend weakening
    STRONG_SELL = "Strong Sell"      # trend breaking


class MACDStatus(Enum):
    """MACDStatus enum"""
    GOLDEN_CROSS_ZERO = "Strongest buy signal"      # DIFWear it on topDEA，and above the zero axis
    GOLDEN_CROSS = "golden fork"                # DIFWear it on topDEA
    BULLISH = "long"                    # DIF>DEA>0
    CROSSING_UP = "Pass through the zero axis"             # DIFPass through the zero axis
    CROSSING_DOWN = "Cross the zero axis"           # DIFCross the zero axis
    BEARISH = "short"                    # DIF<DEA<0
    DEATH_CROSS = "Sicha"                # DIFWear underneathDEA


class RSIStatus(Enum):
    """RSIStatus enum"""
    OVERBOUGHT = "overbought"        # RSI > 70
    STRONG_BUY = "Strong buy"    # 50 < RSI < 70
    NEUTRAL = "neutral"          # 40 <= RSI <= 60
    WEAK = "Weak"             # 30 < RSI < 40
    OVERSOLD = "oversold"         # RSI < 30


@dataclass
class TrendAnalysisResult:
    """Trend analysis results"""
    code: str
    
    # Quantitative energy analysis
    trend_status: TrendStatus = TrendStatus.CONSOLIDATION
    ma_alignment: str = ""           # Moving average arrangement description
    trend_strength: float = 0.0      # trend strength 0-100
    
    # Quantitative energy analysis
    ma5: float = 0.0
    ma10: float = 0.0
    ma20: float = 0.0
    ma60: float = 0.0
    current_price: float = 0.0
    
    # Quantitative energy analysis（Quantitative energy analysis MA5 Quantitative energy analysis）
    bias_ma5: float = 0.0            # (Close - MA5) / MA5 * 100
    bias_ma10: float = 0.0
    bias_ma20: float = 0.0
    
    # Quantitative energy analysis
    volume_status: VolumeStatus = VolumeStatus.NORMAL
    volume_ratio_5d: float = 0.0     # Trading volume of the day/5average daily volume
    volume_trend: str = ""           # Description of energy trends
    
    # support pressure
    support_ma5: bool = False        # MA5 Does it constitute support?
    support_ma10: bool = False       # MA10 Does it constitute support?
    resistance_levels: List[float] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)

    # MACD index
    macd_dif: float = 0.0          # DIF Express
    macd_dea: float = 0.0          # DEA slow line
    macd_bar: float = 0.0           # MACD bar chart
    macd_status: MACDStatus = MACDStatus.BULLISH
    macd_signal: str = ""            # MACD Signal description

    # RSI index
    rsi_6: float = 0.0              # RSI(6) short term
    rsi_12: float = 0.0             # RSI(12) medium term
    rsi_24: float = 0.0             # RSI(24) long term
    rsi_status: RSIStatus = RSIStatus.NEUTRAL
    rsi_signal: str = ""              # RSI Signal description

    # buy signal
    buy_signal: BuySignal = BuySignal.WAIT
    signal_score: int = 0            # Overall rating 0-100
    signal_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'trend_status': self.trend_status.value,
            'ma_alignment': self.ma_alignment,
            'trend_strength': self.trend_strength,
            'ma5': self.ma5,
            'ma10': self.ma10,
            'ma20': self.ma20,
            'ma60': self.ma60,
            'current_price': self.current_price,
            'bias_ma5': self.bias_ma5,
            'bias_ma10': self.bias_ma10,
            'bias_ma20': self.bias_ma20,
            'volume_status': self.volume_status.value,
            'volume_ratio_5d': self.volume_ratio_5d,
            'volume_trend': self.volume_trend,
            'support_ma5': self.support_ma5,
            'support_ma10': self.support_ma10,
            'buy_signal': self.buy_signal.value,
            'signal_score': self.signal_score,
            'signal_reasons': self.signal_reasons,
            'risk_factors': self.risk_factors,
            'macd_dif': self.macd_dif,
            'macd_dea': self.macd_dea,
            'macd_bar': self.macd_bar,
            'macd_status': self.macd_status.value,
            'macd_signal': self.macd_signal,
            'rsi_6': self.rsi_6,
            'rsi_12': self.rsi_12,
            'rsi_24': self.rsi_24,
            'rsi_status': self.rsi_status.value,
            'rsi_signal': self.rsi_signal,
        }


class StockTrendAnalyzer:
    """
    Stock Trend Analyzer

    Implemented based on user transaction concept：
    1. Quantitative energy analysis - MA5>MA10>MA20 multi-head arrangement
    2. Deviation rate detection - Don't chase high，deviate MA5 Exceed 5% Don't buy
    3. Quantitative energy analysis - Preference for scaling back
    4. Buy point identification - Dislike MA5/MA10 support
    5. MACD index - Trend confirmation and golden cross signal
    6. RSI index - Overbought and oversold judgment
    """
    
    # Transaction parameter configuration（BIAS_THRESHOLD from Config read，See _generate_signal）
    VOLUME_SHRINK_RATIO = 0.7   # Shrinkage judgment threshold（Quantity of the day/5average daily volume）
    VOLUME_HEAVY_RATIO = 1.5    # Volume judgment threshold
    MA_SUPPORT_TOLERANCE = 0.02  # MA Support judgment tolerance（2%）

    # MACD parameter（standard12/26/9）
    MACD_FAST = 12              # fast line cycle
    MACD_SLOW = 26             # slow line cycle
    MACD_SIGNAL = 9             # signal line period

    # RSI parameter
    RSI_SHORT = 6               # short termRSIcycle
    RSI_MID = 12               # medium termRSIcycle
    RSI_LONG = 24              # long termRSIcycle
    RSI_OVERBOUGHT = 70        # overbought threshold
    RSI_OVERSOLD = 30          # oversold threshold
    
    def __init__(self):
        """Initialize analyzer"""
        pass
    
    def analyze(self, df: pd.DataFrame, code: str) -> TrendAnalysisResult:
        """
        Analyze stock trends
        
        Args:
            df: Include OHLCV data DataFrame
            code: Analyze results
            
        Returns:
            TrendAnalysisResult Analyze results
        """
        result = TrendAnalysisResult(code=code)
        
        if df is None or df.empty or len(df) < 20:
            logger.warning(f"{code} Not enough data，Unable to perform trend analysis")
            result.risk_factors.append("Not enough data，Unable to complete analysis")
            return result
        
        # Make sure the data is sorted by date
        df = df.sort_values('date').reset_index(drop=True)
        
        # Calculate moving average
        df = self._calculate_mas(df)

        # calculate MACD and RSI
        df = self._calculate_macd(df)
        df = self._calculate_rsi(df)

        # Get the latest data
        latest = df.iloc[-1]
        result.current_price = float(latest['close'])
        result.ma5 = float(latest['MA5'])
        result.ma10 = float(latest['MA10'])
        result.ma20 = float(latest['MA20'])
        result.ma60 = float(latest.get('MA60', 0))

        # 1. Quantitative energy analysis
        self._analyze_trend(df, result)

        # 2. Deviation rate calculation
        self._calculate_bias(result)

        # 3. Quantitative energy analysis
        self._analyze_volume(df, result)

        # 4. Support pressure analysis
        self._analyze_support_resistance(df, result)

        # 5. MACD analyze
        self._analyze_macd(df, result)

        # 6. RSI analyze
        self._analyze_rsi(df, result)

        # 7. Generate a buy signal
        self._generate_signal(result)

        return result
    
    def _calculate_mas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate moving average"""
        df = df.copy()
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        if len(df) >= 60:
            df['MA60'] = df['close'].rolling(window=60).mean()
        else:
            df['MA60'] = df['MA20']  # Used when data is insufficient MA20 substitute
        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        calculate MACD index

        formula：
        - EMA(12)：12daily exponential moving average
        - EMA(26)：26daily exponential moving average
        - DIF = EMA(12) - EMA(26)
        - DEA = EMA(DIF, 9)
        - MACD = (DIF - DEA) * 2
        """
        df = df.copy()

        # Calculate speed line EMA
        ema_fast = df['close'].ewm(span=self.MACD_FAST, adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.MACD_SLOW, adjust=False).mean()

        # Compute Express DIF
        df['MACD_DIF'] = ema_fast - ema_slow

        # Calculate signal lines DEA
        df['MACD_DEA'] = df['MACD_DIF'].ewm(span=self.MACD_SIGNAL, adjust=False).mean()

        # Calculate histogram
        df['MACD_BAR'] = (df['MACD_DIF'] - df['MACD_DEA']) * 2

        return df

    def _calculate_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        calculate RSI index（Wilder's EMA / SMMA caliber）

        formula：
        - avg_gain / avg_loss use ewm(alpha=1/period, adjust=False)
        - RS = avg_gain / avg_loss
        - RSI = 100 - (100 / (1 + RS))
        """
        df = df.copy()

        for period in [self.RSI_SHORT, self.RSI_MID, self.RSI_LONG]:
            # Calculate price changes
            delta = df['close'].diff()

            # Separate rise and fall
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # use Wilder's EMA / SMMA caliber，filling RSI Charting tools remain consistent。
            avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

            # calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            # filling NaN value
            rsi = rsi.fillna(50)  # Default neutral value

            # add to DataFrame
            col_name = f'RSI_{period}'
            df[col_name] = rsi

        return df
    
    def _analyze_trend(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze trend status
        
        Determine moving average arrangement and trend strength：Determine moving average arrangement and trend strength
        """
        ma5, ma10, ma20 = result.ma5, result.ma10, result.ma20
        
        # Determine moving average arrangement
        if ma5 > ma10 > ma20:
            # Check if the spacing is increasing（Strong）
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA5'] - prev['MA20']) / prev['MA20'] * 100 if prev['MA20'] > 0 else 0
            curr_spread = (ma5 - ma20) / ma20 * 100 if ma20 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BULL
                result.ma_alignment = "Strong bull arrangement，Moving averages diverge upward"
                result.trend_strength = 90
            else:
                result.trend_status = TrendStatus.BULL
                result.ma_alignment = "multi-head arrangement MA5>MA10>MA20"
                result.trend_strength = 75
                
        elif ma5 > ma10 and ma10 <= ma20:
            result.trend_status = TrendStatus.WEAK_BULL
            result.ma_alignment = "Weak bulls，MA5>MA10 but MA10≤MA20"
            result.trend_strength = 55
            
        elif ma5 < ma10 < ma20:
            prev = df.iloc[-5] if len(df) >= 5 else df.iloc[-1]
            prev_spread = (prev['MA20'] - prev['MA5']) / prev['MA5'] * 100 if prev['MA5'] > 0 else 0
            curr_spread = (ma20 - ma5) / ma5 * 100 if ma5 > 0 else 0
            
            if curr_spread > prev_spread and curr_spread > 5:
                result.trend_status = TrendStatus.STRONG_BEAR
                result.ma_alignment = "Strong short position，Moving averages diverge downward"
                result.trend_strength = 10
            else:
                result.trend_status = TrendStatus.BEAR
                result.ma_alignment = "Short arrangement MA5<MA10<MA20"
                result.trend_strength = 25
                
        elif ma5 < ma10 and ma10 >= ma20:
            result.trend_status = TrendStatus.WEAK_BEAR
            result.ma_alignment = "Weak short，MA5<MA10 but MA10≥MA20"
            result.trend_strength = 40
            
        else:
            result.trend_status = TrendStatus.CONSOLIDATION
            result.ma_alignment = "moving average wrapping，Unknown trend"
            result.trend_strength = 50
    
    def _calculate_bias(self, result: TrendAnalysisResult) -> None:
        """
        Calculate deviation rate
        
        Quantitative energy analysis = (Current price - moving average) / moving average * 100%
        
        strict strategy：The deviation rate exceeds 5% Don't chase high
        """
        price = result.current_price
        
        if result.ma5 > 0:
            result.bias_ma5 = (price - result.ma5) / result.ma5 * 100
        if result.ma10 > 0:
            result.bias_ma10 = (price - result.ma10) / result.ma10 * 100
        if result.ma20 > 0:
            result.bias_ma20 = (price - result.ma20) / result.ma20 * 100
    
    def _analyze_volume(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze energy
        
        Preference：Taper callback > Rising on heavy volume > Shrinking and rising > Falling on heavy volume
        """
        if len(df) < 5:
            return
        
        latest = df.iloc[-1]
        vol_5d_avg = df['volume'].iloc[-6:-1].mean()
        
        if vol_5d_avg > 0:
            result.volume_ratio_5d = float(latest['volume']) / vol_5d_avg
        
        # Judgment of energy status
        prev_close = df.iloc[-2]['close']
        price_change = (latest['close'] - prev_close) / prev_close * 100
        
        # Judgment of energy status
        if result.volume_ratio_5d >= self.VOLUME_HEAVY_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_UP
                result.volume_trend = "Rising on heavy volume，Bulls are strong"
            else:
                result.volume_status = VolumeStatus.HEAVY_VOLUME_DOWN
                result.volume_trend = "Falling on heavy volume，Be aware of risks"
        elif result.volume_ratio_5d <= self.VOLUME_SHRINK_RATIO:
            if price_change > 0:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_UP
                result.volume_trend = "Shrinking and rising，Insufficient upward momentum"
            else:
                result.volume_status = VolumeStatus.SHRINK_VOLUME_DOWN
                result.volume_trend = "Taper callback，Dishwashing characteristics are obvious（good）"
        else:
            result.volume_status = VolumeStatus.NORMAL
            result.volume_trend = "Energy is normal"
    
    def _analyze_support_resistance(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        Analyze support pressure levels
        
        Buy some preferences：Dislike MA5/MA10 get support
        """
        price = result.current_price
        
        # Check if there is MA5 Get support nearby
        if result.ma5 > 0:
            ma5_distance = abs(price - result.ma5) / result.ma5
            if ma5_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma5:
                result.support_ma5 = True
                result.support_levels.append(result.ma5)
        
        # Check if there is MA10 Get support nearby
        if result.ma10 > 0:
            ma10_distance = abs(price - result.ma10) / result.ma10
            if ma10_distance <= self.MA_SUPPORT_TOLERANCE and price >= result.ma10:
                result.support_ma10 = True
                if result.ma10 not in result.support_levels:
                    result.support_levels.append(result.ma10)
        
        # MA20 as an important support
        if result.ma20 > 0 and price >= result.ma20:
            result.support_levels.append(result.ma20)
        
        # Recent highs act as pressure
        if len(df) >= 20:
            recent_high = df['high'].iloc[-20:].max()
            if recent_high > price:
                result.resistance_levels.append(recent_high)

    def _analyze_macd(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        analyze MACD index

        core signal：
        - Strongest buy signal：Strongest buy signal
        - golden fork：DIF Wear it on top DEA
        - Sicha：DIF Wear underneath DEA
        """
        if len(df) < self.MACD_SLOW:
            result.macd_signal = "Not enough data"
            return

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # get MACD data
        result.macd_dif = float(latest['MACD_DIF'])
        result.macd_dea = float(latest['MACD_DEA'])
        result.macd_bar = float(latest['MACD_BAR'])

        # Judgment of Jin Cha and Death Cha
        prev_dif_dea = prev['MACD_DIF'] - prev['MACD_DEA']
        curr_dif_dea = result.macd_dif - result.macd_dea

        # golden fork：DIF Wear it on top DEA
        is_golden_cross = prev_dif_dea <= 0 and curr_dif_dea > 0

        # Sicha：DIF Wear underneath DEA
        is_death_cross = prev_dif_dea >= 0 and curr_dif_dea < 0

        # zero axis crossing
        prev_zero = prev['MACD_DIF']
        curr_zero = result.macd_dif
        is_crossing_up = prev_zero <= 0 and curr_zero > 0
        is_crossing_down = prev_zero >= 0 and curr_zero < 0

        # judge MACD state
        if is_golden_cross and curr_zero > 0:
            result.macd_status = MACDStatus.GOLDEN_CROSS_ZERO
            result.macd_signal = "⭐ Strongest buy signal，Strong buy signal！"
        elif is_crossing_up:
            result.macd_status = MACDStatus.CROSSING_UP
            result.macd_signal = "⚡ DIFPass through the zero axis，Trend getting stronger"
        elif is_golden_cross:
            result.macd_status = MACDStatus.GOLDEN_CROSS
            result.macd_signal = "✅ golden fork，Trending up"
        elif is_death_cross:
            result.macd_status = MACDStatus.DEATH_CROSS
            result.macd_signal = "❌ Sicha，trending down"
        elif is_crossing_down:
            result.macd_status = MACDStatus.CROSSING_DOWN
            result.macd_signal = "⚠️ DIFCross the zero axis，trend weakening"
        elif result.macd_dif > 0 and result.macd_dea > 0:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = "✓ multi-head arrangement，Continue to rise"
        elif result.macd_dif < 0 and result.macd_dea < 0:
            result.macd_status = MACDStatus.BEARISH
            result.macd_signal = "⚠ Short arrangement，Continued decline"
        else:
            result.macd_status = MACDStatus.BULLISH
            result.macd_signal = " MACD neutral zone"

    def _analyze_rsi(self, df: pd.DataFrame, result: TrendAnalysisResult) -> None:
        """
        analyze RSI index

        core judgment：
        - RSI > 70：overbought，Chase higher cautiously
        - RSI < 30：oversold，Pay attention to rebound
        - 40-60：neutral zone
        """
        if len(df) < self.RSI_LONG:
            result.rsi_signal = "Not enough data"
            return

        latest = df.iloc[-1]

        # get RSI data
        result.rsi_6 = float(latest[f'RSI_{self.RSI_SHORT}'])
        result.rsi_12 = float(latest[f'RSI_{self.RSI_MID}'])
        result.rsi_24 = float(latest[f'RSI_{self.RSI_LONG}'])

        # in the medium term RSI(12) judge for the Lord
        rsi_mid = result.rsi_12

        # judge RSI state
        if rsi_mid > self.RSI_OVERBOUGHT:
            result.rsi_status = RSIStatus.OVERBOUGHT
            result.rsi_signal = f"⚠️ RSIoverbought({rsi_mid:.1f}>70)，Bulls have plenty of power"
        elif rsi_mid > 60:
            result.rsi_status = RSIStatus.STRONG_BUY
            result.rsi_signal = f"✅ RSIStrong({rsi_mid:.1f})，Bulls have plenty of power"
        elif rsi_mid >= 40:
            result.rsi_status = RSIStatus.NEUTRAL
            result.rsi_signal = f" RSIneutral({rsi_mid:.1f})，Concussive finishing"
        elif rsi_mid >= self.RSI_OVERSOLD:
            result.rsi_status = RSIStatus.WEAK
            result.rsi_signal = f"⚡ RSIWeak({rsi_mid:.1f})，Pay attention to rebound"
        else:
            result.rsi_status = RSIStatus.OVERSOLD
            result.rsi_signal = f"⭐ RSIoversold({rsi_mid:.1f}<30)，High chance of rebound"

    def _generate_signal(self, result: TrendAnalysisResult) -> None:
        """
        Generate a buy signal

        Comprehensive scoring system：
        - trend（30point）：High score in bull arrangement
        - Quantitative energy analysis（20point）：near MA5 score high
        - Quantity（15point）：High score for shrinkage callback
        - support（10point）：Obtain moving average support and score high
        - MACD（15point）：Golden cross and bulls score high
        - RSI（10point）：Oversold and strong scores are high
        """
        score = 0
        reasons = []
        risks = []

        # === trend score（30point）===
        trend_scores = {
            TrendStatus.STRONG_BULL: 30,
            TrendStatus.BULL: 26,
            TrendStatus.WEAK_BULL: 18,
            TrendStatus.CONSOLIDATION: 12,
            TrendStatus.WEAK_BEAR: 8,
            TrendStatus.BEAR: 4,
            TrendStatus.STRONG_BEAR: 0,
        }
        trend_score = trend_scores.get(result.trend_status, 12)
        score += trend_score

        if result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            reasons.append(f"✅ {result.trend_status.value}，Go long with the trend")
        elif result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            risks.append(f"⚠️ {result.trend_status.value}，Not suitable for doing long")

        # === Strong trend compensation（20point，Strong trend compensation）===
        bias = result.bias_ma5
        if bias != bias or bias is None:  # NaN or None defense
            bias = 0.0
        base_threshold = get_config().bias_threshold

        # Strong trend compensation: relax threshold for STRONG_BULL with high strength
        trend_strength = result.trend_strength if result.trend_strength == result.trend_strength else 0.0
        if result.trend_status == TrendStatus.STRONG_BULL and (trend_strength or 0) >= 70:
            effective_threshold = base_threshold * 1.5
            is_strong_trend = True
        else:
            effective_threshold = base_threshold
            is_strong_trend = False

        if bias < 0:
            # Price below MA5 (pullback)
            if bias > -3:
                score += 20
                reasons.append(f"✅ The price is slightly lower thanMA5({bias:.1f}%)，Go back and buy some")
            elif bias > -5:
                score += 16
                reasons.append(f"✅ Price falls backMA5({bias:.1f}%)，Observe support")
            else:
                score += 8
                risks.append(f"⚠️ Deviation rate is too large({bias:.1f}%)，Possibly out of position")
        elif bias < 2:
            score += 18
            reasons.append(f"✅ Price is closeMA5({bias:.1f}%)，Good time to intervene")
        elif bias < base_threshold:
            score += 14
            reasons.append(f"⚡ The price is slightly higher thanMA5({bias:.1f}%)，But Ogura intervened")
        elif bias > effective_threshold:
            score += 4
            risks.append(
                f"❌ Deviation rate is too high({bias:.1f}%>{effective_threshold:.1f}%)，It is strictly forbidden to chase high！"
            )
        elif bias > base_threshold and is_strong_trend:
            score += 10
            reasons.append(
                f"⚡ The deviation rate is high in a strong trend({bias:.1f}%)，Can be tracked in light warehouse"
            )
        else:
            score += 4
            risks.append(
                f"❌ Deviation rate is too high({bias:.1f}%>{base_threshold:.1f}%)，It is strictly forbidden to chase high！"
            )

        # === capacity rating（15point）===
        volume_scores = {
            VolumeStatus.SHRINK_VOLUME_DOWN: 15,  # Retracement is the best
            VolumeStatus.HEAVY_VOLUME_UP: 12,     # Heavy volume followed
            VolumeStatus.NORMAL: 10,
            VolumeStatus.SHRINK_VOLUME_UP: 6,     # Infinite rise is poor
            VolumeStatus.HEAVY_VOLUME_DOWN: 0,    # Heavy volume decline is the worst
        }
        vol_score = volume_scores.get(result.volume_status, 8)
        score += vol_score

        if result.volume_status == VolumeStatus.SHRINK_VOLUME_DOWN:
            reasons.append("✅ Taper callback，Main force washing dishes")
        elif result.volume_status == VolumeStatus.HEAVY_VOLUME_DOWN:
            risks.append("⚠️ Falling on heavy volume，Be aware of risks")

        # === Support score（10point）===
        if result.support_ma5:
            score += 5
            reasons.append("✅ MA5Support is effective")
        if result.support_ma10:
            score += 5
            reasons.append("✅ MA10Support is effective")

        # === MACD score（15point）===
        macd_scores = {
            MACDStatus.GOLDEN_CROSS_ZERO: 15,  # The golden fork on the zero axis is the strongest
            MACDStatus.GOLDEN_CROSS: 12,      # golden fork
            MACDStatus.CROSSING_UP: 10,       # Pass through the zero axis
            MACDStatus.BULLISH: 8,            # long
            MACDStatus.BEARISH: 2,            # short
            MACDStatus.CROSSING_DOWN: 0,       # Cross the zero axis
            MACDStatus.DEATH_CROSS: 0,        # Sicha
        }
        macd_score = macd_scores.get(result.macd_status, 5)
        score += macd_score

        if result.macd_status in [MACDStatus.GOLDEN_CROSS_ZERO, MACDStatus.GOLDEN_CROSS]:
            reasons.append(f"✅ {result.macd_signal}")
        elif result.macd_status in [MACDStatus.DEATH_CROSS, MACDStatus.CROSSING_DOWN]:
            risks.append(f"⚠️ {result.macd_signal}")
        else:
            reasons.append(result.macd_signal)

        # === RSI score（10point）===
        rsi_scores = {
            RSIStatus.OVERSOLD: 10,       # Oversold is best
            RSIStatus.STRONG_BUY: 8,     # Strong
            RSIStatus.NEUTRAL: 5,        # neutral
            RSIStatus.WEAK: 3,            # Weak
            RSIStatus.OVERBOUGHT: 0,       # Overbought is the worst
        }
        rsi_score = rsi_scores.get(result.rsi_status, 5)
        score += rsi_score

        if result.rsi_status in [RSIStatus.OVERSOLD, RSIStatus.STRONG_BUY]:
            reasons.append(f"✅ {result.rsi_signal}")
        elif result.rsi_status == RSIStatus.OVERBOUGHT:
            risks.append(f"⚠️ {result.rsi_signal}")
        else:
            reasons.append(result.rsi_signal)

        # === Comprehensive judgment ===
        result.signal_score = score
        result.signal_reasons = reasons
        result.risk_factors = risks

        # Generate a buy signal（Quantitative energy analysis canonical decision scale Be consistent）
        score_signal = signal_key_for_score(score)
        if score_signal == "strong_buy" and result.trend_status in [TrendStatus.STRONG_BULL, TrendStatus.BULL]:
            result.buy_signal = BuySignal.STRONG_BUY
        elif score_signal in {"strong_buy", "buy"} and result.trend_status in [
            TrendStatus.STRONG_BULL,
            TrendStatus.BULL,
            TrendStatus.WEAK_BULL,
        ]:
            result.buy_signal = BuySignal.BUY
        elif score_signal in {"strong_buy", "buy"} and result.trend_status in [
            TrendStatus.CONSOLIDATION,
            TrendStatus.WEAK_BEAR,
        ]:
            result.buy_signal = BuySignal.WAIT
        elif score_signal == "watch":
            result.buy_signal = BuySignal.WAIT
        elif score_signal == "sell" or result.trend_status in [TrendStatus.BEAR, TrendStatus.STRONG_BEAR]:
            result.buy_signal = BuySignal.STRONG_SELL
        else:
            result.buy_signal = BuySignal.SELL
    
    def format_analysis(self, result: TrendAnalysisResult) -> str:
        """
        Format analysis results as text

        Args:
            result: Analyze results

        Returns:
            Formatted analysis text
        """
        lines = [
            f"=== {result.code} trend analysis ===",
            f"",
            f"📊 Quantitative energy analysis: {result.trend_status.value}",
            f"   moving average arrangement: {result.ma_alignment}",
            f"   trend strength: {result.trend_strength}/100",
            f"",
            f"📈 Quantitative energy analysis:",
            f"   Current price: {result.current_price:.2f}",
            f"   MA5:  {result.ma5:.2f} (deviant {result.bias_ma5:+.2f}%)",
            f"   MA10: {result.ma10:.2f} (deviant {result.bias_ma10:+.2f}%)",
            f"   MA20: {result.ma20:.2f} (deviant {result.bias_ma20:+.2f}%)",
            f"",
            f"📊 Quantitative energy analysis: {result.volume_status.value}",
            f"   day(vs5day): {result.volume_ratio_5d:.2f}",
            f"   Energy trend: {result.volume_trend}",
            f"",
            f"📈 MACDindex: {result.macd_status.value}",
            f"   DIF: {result.macd_dif:.4f}",
            f"   DEA: {result.macd_dea:.4f}",
            f"   MACD: {result.macd_bar:.4f}",
            f"   Signal: {result.macd_signal}",
            f"",
            f"📊 RSIindex: {result.rsi_status.value}",
            f"   RSI(6): {result.rsi_6:.1f}",
            f"   RSI(12): {result.rsi_12:.1f}",
            f"   RSI(24): {result.rsi_24:.1f}",
            f"   Signal: {result.rsi_signal}",
            f"",
            f"🎯 Operation suggestions: {result.buy_signal.value}",
            f"   Overall rating: {result.signal_score}/100",
        ]

        if result.signal_reasons:
            lines.append(f"")
            lines.append(f"✅ Reasons to buy:")
            for reason in result.signal_reasons:
                lines.append(f"   {reason}")

        if result.risk_factors:
            lines.append(f"")
            lines.append(f"⚠️ risk factors:")
            for risk in result.risk_factors:
                lines.append(f"   {risk}")

        return "\n".join(lines)


def analyze_stock(df: pd.DataFrame, code: str) -> TrendAnalysisResult:
    """
    Convenience function：Analyze individual stocks
    
    Args:
        df: Include OHLCV data DataFrame
        code: Analyze results
        
    Returns:
        TrendAnalysisResult Analyze results
    """
    analyzer = StockTrendAnalyzer()
    return analyzer.analyze(df, code)


if __name__ == "__main__":
    # test code
    logging.basicConfig(level=logging.INFO)
    
    # Data that simulates a long arrangement
    import numpy as np
    
    dates = pd.date_range(start='2025-01-01', periods=60, freq='D')
    np.random.seed(42)
    
    # Data that simulates a long arrangement
    base_price = 10.0
    prices = [base_price]
    for i in range(59):
        change = np.random.randn() * 0.02 + 0.003  # slight uptrend
        prices.append(prices[-1] * (1 + change))
    
    df = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
        'close': prices,
        'volume': [np.random.randint(1000000, 5000000) for _ in prices],
    })
    
    analyzer = StockTrendAnalyzer()
    result = analyzer.analyze(df, '000001')
    print(analyzer.format_analysis(result))
