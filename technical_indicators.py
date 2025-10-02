import pandas as pd
import numpy as np
from typing import Optional, Tuple, Union
import talib

class TechnicalIndicators:
    """Technical indicators calculator for trading strategies."""

    @staticmethod
    def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        if data is None or len(data) == 0:
            return pd.Series(dtype=float)
        return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD indicator."""
        if data is None or len(data) == 0:
            empty = pd.Series(dtype=float)
            return empty, empty, empty

        macd_line, signal_line, histogram = talib.MACD(
            data.values,
            fastperiod=fast,
            slowperiod=slow,
            signalperiod=signal
        )
        return (
            pd.Series(macd_line, index=data.index),
            pd.Series(signal_line, index=data.index),
            pd.Series(histogram, index=data.index)
        )

    @staticmethod
    def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        if data is None or len(data) == 0:
            empty = pd.Series(dtype=float)
            return empty, empty, empty

        upper, middle, lower = talib.BBANDS(
            data.values,
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev
        )
        return (
            pd.Series(upper, index=data.index),
            pd.Series(middle, index=data.index),
            pd.Series(lower, index=data.index)
        )

    @staticmethod
    def calculate_ema(data: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average."""
        if data is None or len(data) == 0:
            return pd.Series(dtype=float)
        return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def calculate_sma(data: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Simple Moving Average."""
        if data is None or len(data) == 0:
            return pd.Series(dtype=float)
        return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)

    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        if high is None or low is None or close is None or len(high) == 0:
            return pd.Series(dtype=float)

        atr = talib.ATR(high.values, low.values, close.values, timeperiod=period)
        return pd.Series(atr, index=close.index)

    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                            fastk_period: int = 14, slowk_period: int = 3,
                            slowd_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator."""
        if high is None or low is None or close is None or len(high) == 0:
            empty = pd.Series(dtype=float)
            return empty, empty

        slowk, slowd = talib.STOCH(
            high.values,
            low.values,
            close.values,
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowd_period=slowd_period
        )
        return (
            pd.Series(slowk, index=close.index),
            pd.Series(slowd, index=close.index)
        )

    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index."""
        if high is None or low is None or close is None or len(high) == 0:
            return pd.Series(dtype=float)

        adx = talib.ADX(high.values, low.values, close.values, timeperiod=period)
        return pd.Series(adx, index=close.index)

    @staticmethod
    def calculate_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate On-Balance Volume."""
        if close is None or volume is None or len(close) == 0:
            return pd.Series(dtype=float)

        obv = talib.OBV(close.values, volume.values)
        return pd.Series(obv, index=close.index)
