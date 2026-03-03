"""News, earnings, and other feeds."""

from dine_trade.data.feeds.news_feed import get_recent_headlines
from dine_trade.data.feeds.alpaca_news_ws import run_news_stream
from dine_trade.data.feeds.earnings_audio import (
    get_earnings_transcript,
    analyze_transcript_sentiment,
)

__all__ = [
    "get_recent_headlines",
    "run_news_stream",
    "get_earnings_transcript",
    "analyze_transcript_sentiment",
]


