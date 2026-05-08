"""Smoke-тесты для расчета расширенной аналитики канала.

Тестируем чисто арифметическую часть `get_channel_analytics`, мокая
session/Channel/Post/Members/Views, чтобы не требовать БД.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

import pytest

from src.db.database_service import DatabaseService


class _FakeScalars:
    def __init__(self, items: List[Any]) -> None:
        self._items = items

    def all(self) -> List[Any]:
        return list(self._items)

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None


class _FakeResult:
    def __init__(self, items: List[Any]) -> None:
        self._items = items

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._items)

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None


class _FakeSession:
    """Минимальная имитация AsyncSession для get_channel_analytics."""

    def __init__(self, channel: Any, members: List[Any], views: List[Any], posts: List[Any]) -> None:
        self._channel = channel
        self._members = members
        self._views = views
        self._posts = posts
        self._call_index = 0

    async def execute(self, _stmt: Any) -> _FakeResult:
        # Порядок запросов в get_channel_analytics:
        # 1) channel, 2) members_history, 3) views_history,
        # 4) period_posts, 5) recent_posts.
        order = [
            [self._channel] if self._channel else [],
            self._members,
            self._views,
            self._posts,
            list(reversed(self._posts))[:10],
        ]
        result = _FakeResult(order[self._call_index])
        self._call_index += 1
        return result


class _SimpleAttr:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def _build_service_with_session(session: _FakeSession) -> DatabaseService:
    service = DatabaseService("postgresql+asyncpg://test/test")

    @asynccontextmanager
    async def _session_factory():
        yield session

    service.get_session = _session_factory  # type: ignore[assignment]
    return service


def _make_post(message_id: int, hour: int, weekday_offset: int, views: int, reactions: int, forwards: int) -> _SimpleAttr:
    base = datetime(2026, 5, 4, hour, 0)  # 4 May 2026 = Monday
    return _SimpleAttr(
        post_id=message_id,
        text=f"post {message_id}",
        media_type="photo" if message_id % 2 == 0 else "text",
        views=views,
        forwards=forwards,
        reactions={"like": reactions},
        posted_at=base + timedelta(days=weekday_offset),
    )


@pytest.mark.asyncio
async def test_channel_analytics_period_metrics() -> None:
    today = date.today()

    channel = _SimpleAttr(
        channel_id=1,
        username="demo",
        title="Demo",
        subscribers_count=1000,
        posts_count=10,
    )
    members = [
        _SimpleAttr(date=datetime.combine(today - timedelta(days=offset), datetime.min.time()),
                    members_count=1000 - offset * 10,
                    members_growth=10)
        for offset in range(6, -1, -1)
    ]
    views = [
        _SimpleAttr(date=datetime.combine(today - timedelta(days=offset), datetime.min.time()),
                    avg_views=200,
                    total_views=400,
                    posts_count=2,
                    total_reactions=20,
                    total_forwards=4)
        for offset in range(6, -1, -1)
    ]
    posts = [
        _make_post(1, hour=10, weekday_offset=0, views=500, reactions=20, forwards=5),
        _make_post(2, hour=19, weekday_offset=1, views=900, reactions=60, forwards=10),
        _make_post(3, hour=19, weekday_offset=1, views=1100, reactions=80, forwards=15),
        _make_post(4, hour=12, weekday_offset=2, views=300, reactions=10, forwards=2),
    ]

    session = _FakeSession(channel, members, views, posts)
    service = _build_service_with_session(session)

    analytics = await service.get_channel_analytics(channel_id=1, days=7)

    assert analytics["channel"]["id"] == 1
    period = analytics["period"]

    # Подписчики
    assert period["members_total_growth"] == members[-1].members_count - members[0].members_count
    assert period["growth_days"] == len(members)

    # Агрегаты просмотров берутся из views_history
    assert period["total_views"] == sum(v.total_views for v in views)
    assert period["total_posts"] == sum(v.posts_count for v in views)
    assert period["avg_views_per_post"] == period["total_views"] / period["total_posts"]

    # ER-метрики
    assert period["err"] == pytest.approx(period["engagement_rate"])
    assert period["er_classic"] == pytest.approx(
        (period["total_reactions"] + period["total_forwards"]) / channel.subscribers_count * 100
    )
    assert period["vtr"] == pytest.approx(
        period["avg_views_per_post"] / channel.subscribers_count * 100
    )
    assert 0 < period["avg_post_er"] < 100

    # Лучшее время публикации — 19:00 даёт максимум среднего охвата
    assert period["best_posting_hour"] == 19
    assert period["best_posting_weekday"] in {0, 1, 2}

    # Контент-микс собран
    assert set(analytics["content_breakdown"].keys()) == {"text", "photo"}
    assert analytics["content_breakdown"]["photo"]["posts_count"] == 2

    # Топ постов отсортирован по охвату
    top_views = [post["views"] for post in analytics["top_posts"]]
    assert top_views == sorted(top_views, reverse=True)


@pytest.mark.asyncio
async def test_channel_analytics_returns_empty_for_unknown_channel() -> None:
    session = _FakeSession(channel=None, members=[], views=[], posts=[])
    service = _build_service_with_session(session)

    result = await service.get_channel_analytics(channel_id=42, days=7)

    assert result == {}
