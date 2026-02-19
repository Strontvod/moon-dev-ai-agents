"""
🌙 Moon Dev's Custom Strategies Package
"""
from src.strategies.base_strategy import BaseStrategy
from .example_strategy import ExampleStrategy
from .divergence_volatility_strategy import DivergenceVolatilityStrategy

__all__ = ['ExampleStrategy', 'DivergenceVolatilityStrategy']