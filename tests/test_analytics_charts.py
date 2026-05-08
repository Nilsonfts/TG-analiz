"""Smoke-тесты для модуля построения графиков аналитики."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

from src.handlers.analytics_charts import (
    render_channel_dashboard_png,
    render_growth_overview_png,
)


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _sample_analytics() -> Dict[str, Any]:
    today = date.today()
    return {
        "channel": {
            "id": 1,
            "username": "demo",
            "title": "Demo Channel",
            "subscribers": 10000,
            "posts_count": 200,
        },
        "period": {
            "days": 7,
            "members_total_growth": 120,
            "members_growth_percent": 1.2,
            "avg_daily_growth": 17.1,
            "growth_days": 5,
            "decline_days": 1,
            "stable_days": 1,
            "total_posts": 14,
            "total_views": 56000,
            "total_reactions": 1800,
            "total_forwards": 220,
            "avg_views_per_post": 4000,
            "avg_reactions_per_post": 128.5,
            "avg_forwards_per_post": 15.7,
            "engagement_rate": 3.6,
            "er_classic": 20.2,
            "err": 3.6,
            "vtr": 40.0,
            "avg_post_er": 3.4,
            "avg_posts_per_day": 2.0,
            "current_subscribers": 10000,
            "best_posting_hour": 19,
            "best_posting_hour_avg_views": 5200,
            "best_posting_weekday": 2,
            "best_posting_weekday_avg_views": 4800,
        },
        "members_history": [
            {
                "date": (today - timedelta(days=i)).isoformat(),
                "count": 9900 + i * 15,
                "growth": 15,
            }
            for i in range(7, 0, -1)
        ],
        "views_history": [
            {
                "date": (today - timedelta(days=i)).isoformat(),
                "avg_views": 3500 + i * 100,
                "total_views": 7000 + i * 200,
                "posts_count": 2,
            }
            for i in range(7, 0, -1)
        ],
        "content_breakdown": {
            "text": {"posts_count": 6, "total_views": 18000, "total_reactions": 600, "avg_views": 3000},
            "photo": {"posts_count": 5, "total_views": 22000, "total_reactions": 800, "avg_views": 4400},
            "video": {"posts_count": 3, "total_views": 16000, "total_reactions": 400, "avg_views": 5333},
        },
        "posts_by_hour": {
            hour: {"posts_count": 1, "avg_views": 3000 + (hour % 5) * 400}
            for hour in [9, 12, 15, 18, 19, 21]
        },
        "posts_by_weekday": {
            index: {"posts_count": 2, "avg_views": 3500 + index * 200} for index in range(7)
        },
        "top_posts": [],
        "recent_posts": [],
    }


def test_render_channel_dashboard_png_returns_png_bytes() -> None:
    buffer = render_channel_dashboard_png(_sample_analytics())

    assert buffer is not None, "Дашборд должен строиться при наличии данных"
    payload = buffer.getvalue()
    assert payload.startswith(PNG_SIGNATURE), "Файл должен быть валидным PNG"
    assert len(payload) > 5_000, "PNG не должен быть пустым"


def test_render_channel_dashboard_returns_none_when_empty() -> None:
    empty_analytics: Dict[str, Any] = {
        "channel": {"title": "Empty"},
        "period": {},
        "members_history": [],
        "views_history": [],
        "content_breakdown": {},
        "posts_by_hour": {},
        "posts_by_weekday": {},
    }

    assert render_channel_dashboard_png(empty_analytics) is None


def test_render_channel_dashboard_returns_none_for_falsy_input() -> None:
    assert render_channel_dashboard_png({}) is None


def test_render_growth_overview_png_returns_png_bytes() -> None:
    rows = [
        {"title": "Demo", "username": "demo", "growth": 120, "growth_percent": 1.2, "engagement_rate": 3.6},
        {"title": "Other", "username": "other", "growth": -45, "growth_percent": -0.4, "engagement_rate": 2.1},
        {"title": "News", "username": "news", "growth": 300, "growth_percent": 5.5, "engagement_rate": 4.8},
    ]

    buffer = render_growth_overview_png(rows)

    assert buffer is not None
    payload = buffer.getvalue()
    assert payload.startswith(PNG_SIGNATURE)
    assert len(payload) > 5_000


def test_render_growth_overview_returns_none_for_empty_rows() -> None:
    assert render_growth_overview_png([]) is None
