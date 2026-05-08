"""
Генератор графиков аналитики канала в виде PNG (BytesIO).

Все графики строятся через matplotlib с backend "Agg",
чтобы работало в headless-окружении (Railway, Docker, CI).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # headless backend, должен быть выставлен до pyplot

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _setup_style() -> None:
    plt.rcParams["font.family"] = ["DejaVu Sans", "Arial Unicode MS", "Tahoma"]
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "#f9fafb"
    plt.rcParams["axes.edgecolor"] = "#cbd5e1"
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.color"] = "#e2e8f0"
    plt.rcParams["grid.linestyle"] = "--"
    plt.rcParams["grid.linewidth"] = 0.6


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _empty_axis(ax, message: str) -> None:
    ax.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        transform=ax.transAxes,
        fontsize=12,
        color="#94a3b8",
    )
    ax.set_xticks([])
    ax.set_yticks([])


def _annotate_bars(ax, bars, formatter=lambda value: f"{value:,.0f}") -> None:
    for bar in bars:
        height = bar.get_height()
        if height == 0:
            continue
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            formatter(height),
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
            color="#1f2937",
        )


def _plot_members(ax, members_history: List[Dict[str, Any]]) -> None:
    ax.set_title("👥 Подписчики", fontsize=13, fontweight="bold")
    if not members_history:
        _empty_axis(ax, "Нет данных")
        return

    dates = [_parse_date(item["date"]) for item in members_history]
    values = [int(item["count"]) for item in members_history]

    ax.plot(dates, values, color="#2563eb", linewidth=2.2, marker="o", markersize=4)
    ax.fill_between(dates, values, color="#2563eb", alpha=0.12)
    ax.set_ylabel("Подписчики")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))


def _plot_views(ax, views_history: List[Dict[str, Any]]) -> None:
    ax.set_title("👁 Средний охват поста", fontsize=13, fontweight="bold")
    if not views_history:
        _empty_axis(ax, "Нет данных")
        return

    dates = [_parse_date(item["date"]) for item in views_history]
    values = [float(item.get("avg_views") or 0) for item in views_history]

    bars = ax.bar(dates, values, color="#10b981", alpha=0.85, width=0.7)
    _annotate_bars(ax, bars)
    ax.set_ylabel("Просмотры")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))


def _plot_engagement(ax, period: Dict[str, Any]) -> None:
    ax.set_title("🎯 Engagement Rate", fontsize=13, fontweight="bold")

    er_classic = float(period.get("er_classic") or 0.0)
    err = float(period.get("err") or 0.0)
    vtr = float(period.get("vtr") or 0.0)
    avg_post_er = float(period.get("avg_post_er") or 0.0)

    labels = ["ER classic", "ERR (по\nпросмотрам)", "VTR\n(охват)", "Средний\nER поста"]
    values = [er_classic, err, vtr, avg_post_er]
    colors = ["#f59e0b", "#3b82f6", "#8b5cf6", "#ef4444"]

    if all(value == 0 for value in values):
        _empty_axis(ax, "Нет данных")
        return

    bars = ax.bar(labels, values, color=colors, alpha=0.85)
    _annotate_bars(ax, bars, formatter=lambda value: f"{value:.2f}%")
    ax.set_ylabel("Процент")
    ax.set_ylim(0, max(values) * 1.25 if max(values) > 0 else 1)


def _plot_content_mix(ax, content_breakdown: Dict[str, Dict[str, Any]]) -> None:
    ax.set_title("🧩 Контент-микс", fontsize=13, fontweight="bold")

    if not content_breakdown:
        _empty_axis(ax, "Нет постов в периоде")
        return

    sorted_items = sorted(
        content_breakdown.items(),
        key=lambda item: item[1].get("posts_count", 0),
        reverse=True,
    )
    labels = [item[0] for item in sorted_items]
    sizes = [int(item[1].get("posts_count", 0)) for item in sorted_items]
    palette = ["#2563eb", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#0ea5e9", "#22c55e"]
    colors = [palette[i % len(palette)] for i in range(len(labels))]

    ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"fontsize": 10},
    )
    ax.axis("equal")


def _plot_best_hours(ax, posts_by_hour: Dict[int, Dict[str, Any]]) -> None:
    ax.set_title("⏰ Средний охват по часам", fontsize=13, fontweight="bold")

    if not posts_by_hour:
        _empty_axis(ax, "Нет данных")
        return

    hours = list(range(24))
    avg_views = [float(posts_by_hour.get(hour, {}).get("avg_views") or 0) for hour in hours]

    if all(value == 0 for value in avg_views):
        _empty_axis(ax, "Нет данных")
        return

    bars = ax.bar(hours, avg_views, color="#6366f1", alpha=0.85)
    best_index = max(range(24), key=lambda idx: avg_views[idx])
    bars[best_index].set_color("#f97316")
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Час суток")
    ax.set_ylabel("Средний охват поста")


def _plot_best_weekdays(ax, posts_by_weekday: Dict[int, Dict[str, Any]]) -> None:
    ax.set_title("📅 Средний охват по дням недели", fontsize=13, fontweight="bold")

    if not posts_by_weekday:
        _empty_axis(ax, "Нет данных")
        return

    indices = list(range(7))
    avg_views = [float(posts_by_weekday.get(index, {}).get("avg_views") or 0) for index in indices]

    if all(value == 0 for value in avg_views):
        _empty_axis(ax, "Нет данных")
        return

    bars = ax.bar(WEEKDAYS_RU, avg_views, color="#0ea5e9", alpha=0.85)
    best_index = max(indices, key=lambda idx: avg_views[idx])
    bars[best_index].set_color("#f97316")
    ax.set_ylabel("Средний охват поста")


def render_channel_dashboard_png(analytics: Dict[str, Any]) -> Optional[io.BytesIO]:
    """
    Строит сводный дашборд канала и возвращает PNG в BytesIO.

    Возвращает None, если данных слишком мало для построения.
    """
    if not analytics:
        return None

    channel = analytics.get("channel") or {}
    period = analytics.get("period") or {}
    members_history = analytics.get("members_history") or []
    views_history = analytics.get("views_history") or []
    content_breakdown = analytics.get("content_breakdown") or {}
    posts_by_hour = analytics.get("posts_by_hour") or {}
    posts_by_weekday = analytics.get("posts_by_weekday") or {}

    if not any([members_history, views_history, content_breakdown, posts_by_hour]):
        return None

    _setup_style()

    fig, axes = plt.subplots(3, 2, figsize=(13, 14))
    fig.subplots_adjust(hspace=0.55, wspace=0.3, top=0.92, bottom=0.06, left=0.07, right=0.97)

    title = channel.get("title") or "Канал"
    username = channel.get("username")
    days = period.get("days") or 7
    header = f"📊 Аналитика канала «{title}» за {days} дн."
    if username:
        header += f"  ·  @{username}"
    fig.suptitle(header, fontsize=16, fontweight="bold")

    _plot_members(axes[0][0], members_history)
    _plot_views(axes[0][1], views_history)
    _plot_engagement(axes[1][0], period)
    _plot_content_mix(axes[1][1], content_breakdown)
    _plot_best_hours(axes[2][0], posts_by_hour)
    _plot_best_weekdays(axes[2][1], posts_by_weekday)

    fig.text(
        0.5,
        0.015,
        f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        ha="center",
        fontsize=9,
        color="#64748b",
    )

    buffer = io.BytesIO()
    try:
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)

    buffer.seek(0)
    return buffer


def render_growth_overview_png(rows: List[Dict[str, Any]]) -> Optional[io.BytesIO]:
    """
    Строит сравнительный график роста по всем активным каналам.
    rows: список словарей с ключами title/username/growth/growth_percent/engagement_rate.
    """
    if not rows:
        return None

    _setup_style()

    sorted_rows = sorted(rows, key=lambda item: item.get("growth", 0), reverse=True)
    labels = [
        f"@{row['username']}" if row.get("username") else (row.get("title") or "—")
        for row in sorted_rows
    ]
    growth_values = [int(row.get("growth", 0)) for row in sorted_rows]
    er_values = [float(row.get("engagement_rate", 0.0)) for row in sorted_rows]

    fig, (ax_growth, ax_er) = plt.subplots(2, 1, figsize=(12, 8))
    fig.subplots_adjust(hspace=0.5, top=0.92)
    fig.suptitle("📈 Рост и вовлеченность каналов за 7 дней", fontsize=15, fontweight="bold")

    growth_colors = ["#10b981" if value >= 0 else "#ef4444" for value in growth_values]
    bars = ax_growth.bar(labels, growth_values, color=growth_colors, alpha=0.85)
    ax_growth.axhline(0, color="#64748b", linewidth=0.8)
    ax_growth.set_title("Прирост подписчиков", fontsize=12, fontweight="bold")
    ax_growth.set_ylabel("Подписчики")
    ax_growth.tick_params(axis="x", rotation=30)
    _annotate_bars(ax_growth, bars, formatter=lambda value: f"{int(value):+,}")

    er_bars = ax_er.bar(labels, er_values, color="#3b82f6", alpha=0.85)
    ax_er.set_title("Engagement Rate (ERR)", fontsize=12, fontweight="bold")
    ax_er.set_ylabel("ERR, %")
    ax_er.tick_params(axis="x", rotation=30)
    _annotate_bars(ax_er, er_bars, formatter=lambda value: f"{value:.2f}%")

    buffer = io.BytesIO()
    try:
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    finally:
        plt.close(fig)
    buffer.seek(0)
    return buffer
