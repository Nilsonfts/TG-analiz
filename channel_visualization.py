import io
import logging
from datetime import datetime, timedelta
from typing import Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from channel_analytics import ChannelAnalytics

logger = logging.getLogger(__name__)

# Настройка стиля графиков
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


class ChannelChartGenerator:
    """Генератор графиков для аналитики каналов"""

    def __init__(self, analytics: ChannelAnalytics):
        self.analytics = analytics

        # Настройка шрифтов для поддержки русского языка
        plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

    def setup_plot_style(self, figsize=(12, 8)):
        """Настройка стиля графика"""
        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("#f8f9fa")
        ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        return fig, ax

    def save_plot_to_bytes(self, fig) -> io.BytesIO:
        """Сохранение графика в байты"""
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        buf.seek(0)
        plt.close(fig)
        return buf

    async def generate_subscriber_growth_chart(
        self, channel_id: int, days: int = 30
    ) -> Optional[io.BytesIO]:
        """Генерация графика роста подписчиков"""
        try:
            growth_data = await self.analytics.get_subscriber_growth_data(
                channel_id, days
            )

            if not growth_data:
                return None

            # Подготовка данных
            dates = [item["date"] for item in growth_data]
            gained = [item["subscribers_gained"] for item in growth_data]
            lost = [item["subscribers_lost"] for item in growth_data]
            net_growth = [g - l for g, l in zip(gained, lost)]

            # Создание графика
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            fig.suptitle(
                "📈 Динамика роста подписчиков", fontsize=16, fontweight="bold"
            )

            # График 1: Чистый прирост
            ax1.plot(
                dates,
                net_growth,
                color="#2E86C1",
                linewidth=3,
                marker="o",
                markersize=6,
            )
            ax1.fill_between(dates, net_growth, alpha=0.3, color="#2E86C1")
            ax1.set_title("Чистый прирост подписчиков", fontsize=14, fontweight="bold")
            ax1.set_ylabel("Количество подписчиков", fontsize=12)
            ax1.grid(True, alpha=0.3)

            # Добавление линии тренда
            if len(dates) > 1:
                x_numeric = [i for i in range(len(dates))]
                z = np.polyfit(x_numeric, net_growth, 1)
                p = np.poly1d(z)
                ax1.plot(
                    dates,
                    p(x_numeric),
                    "--",
                    color="red",
                    alpha=0.8,
                    linewidth=2,
                    label="Тренд",
                )
                ax1.legend()

            # График 2: Приток и отток
            width = 0.35
            x = range(len(dates))

            bars1 = ax2.bar(
                [i - width / 2 for i in x],
                gained,
                width,
                label="Новые подписчики",
                color="#28B463",
                alpha=0.8,
            )
            bars2 = ax2.bar(
                [i + width / 2 for i in x],
                [-l for l in lost],
                width,
                label="Ушедшие подписчики",
                color="#E74C3C",
                alpha=0.8,
            )

            ax2.set_title("Приток и отток подписчиков", fontsize=14, fontweight="bold")
            ax2.set_ylabel("Количество подписчиков", fontsize=12)
            ax2.set_xlabel("Дата", fontsize=12)
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # Форматирование дат на оси X
            ax2.set_xticks(x)
            ax2.set_xticklabels([d.strftime("%d.%m") for d in dates], rotation=45)

            # Добавление значений на столбцы
            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 0.5,
                        f"{int(height)}",
                        ha="center",
                        va="bottom",
                        fontsize=10,
                    )

            for bar in bars2:
                height = bar.get_height()
                if height < 0:
                    ax2.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height - 0.5,
                        f"{int(-height)}",
                        ha="center",
                        va="top",
                        fontsize=10,
                    )

            plt.tight_layout()
            return self.save_plot_to_bytes(fig)

        except Exception as e:
            logger.error(f"Ошибка генерации графика роста подписчиков: {e}")
            return None

    async def generate_hourly_activity_chart(
        self, channel_id: int, days: int = 7
    ) -> Optional[io.BytesIO]:
        """Генерация графика почасовой активности"""
        try:
            hourly_data = await self.analytics.get_hourly_views_data(channel_id, days)

            if not hourly_data:
                return None

            # Группировка по часам
            hourly_stats = {}
            for item in hourly_data:
                hour = item["hour_of_day"]
                if hour not in hourly_stats:
                    hourly_stats[hour] = {"views": 0, "story_views": 0, "count": 0}
                hourly_stats[hour]["views"] += item["total_views"]
                hourly_stats[hour]["story_views"] += item["story_views"]
                hourly_stats[hour]["count"] += 1

            # Вычисление средних значений
            hours = []
            avg_views = []
            avg_story_views = []

            for hour in range(24):
                hours.append(hour)
                if hour in hourly_stats:
                    avg_views.append(
                        hourly_stats[hour]["views"] / hourly_stats[hour]["count"]
                    )
                    avg_story_views.append(
                        hourly_stats[hour]["story_views"] / hourly_stats[hour]["count"]
                    )
                else:
                    avg_views.append(0)
                    avg_story_views.append(0)

            # Создание графика
            fig, ax = plt.subplots(figsize=(14, 8))
            fig.suptitle(
                "⏰ Почасовая активность аудитории", fontsize=16, fontweight="bold"
            )

            # Столбчатая диаграмма
            width = 0.35
            x = np.arange(len(hours))

            bars1 = ax.bar(
                x - width / 2,
                avg_views,
                width,
                label="Просмотры постов",
                color="#3498DB",
                alpha=0.8,
            )
            bars2 = ax.bar(
                x + width / 2,
                avg_story_views,
                width,
                label="Просмотры историй",
                color="#E67E22",
                alpha=0.8,
            )

            ax.set_xlabel("Час дня", fontsize=12)
            ax.set_ylabel("Среднее количество просмотров", fontsize=12)
            ax.set_title(f"Активность за последние {days} дней", fontsize=14)
            ax.set_xticks(x)
            ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45)
            ax.legend()
            ax.grid(True, alpha=0.3)

            # Подсветка пиковых часов
            max_hour = hours[avg_views.index(max(avg_views))]
            ax.axvline(
                x=max_hour,
                color="red",
                linestyle="--",
                alpha=0.7,
                linewidth=2,
                label=f"Пик активности: {max_hour:02d}:00",
            )
            ax.legend()

            plt.tight_layout()
            return self.save_plot_to_bytes(fig)

        except Exception as e:
            logger.error(f"Ошибка генерации графика почасовой активности: {e}")
            return None

    async def generate_traffic_sources_chart(
        self, channel_id: int, days: int = 30
    ) -> Optional[io.BytesIO]:
        """Генерация графика источников трафика"""
        try:
            traffic_data = await self.analytics.get_traffic_sources_data(
                channel_id, days
            )

            if not traffic_data:
                return None

            # Подготовка данных
            sources = []
            subscribers = []
            views = []

            source_names = {
                "url": "URL ссылки",
                "search": "Поиск",
                "groups": "Группы",
                "channels": "Каналы",
                "private_chats": "Личные чаты",
                "other": "Другое",
            }

            for item in traffic_data:
                source_name = source_names.get(
                    item["source_type"], item["source_type"].title()
                )
                sources.append(source_name)
                subscribers.append(item["total_subscribers"])
                views.append(item["total_views"])

            # Создание графика
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
            fig.suptitle("🎯 Источники трафика канала", fontsize=16, fontweight="bold")

            # Круговая диаграмма подписчиков
            colors = plt.cm.Set3(np.linspace(0, 1, len(sources)))
            wedges1, texts1, autotexts1 = ax1.pie(
                subscribers,
                labels=sources,
                autopct="%1.1f%%",
                colors=colors,
                startangle=90,
            )
            ax1.set_title(
                "Распределение новых подписчиков", fontsize=14, fontweight="bold"
            )

            # Круговая диаграмма просмотров
            wedges2, texts2, autotexts2 = ax2.pie(
                views, labels=sources, autopct="%1.1f%%", colors=colors, startangle=90
            )
            ax2.set_title("Распределение просмотров", fontsize=14, fontweight="bold")

            # Улучшение внешнего вида текста
            for autotext in autotexts1 + autotexts2:
                autotext.set_color("white")
                autotext.set_fontweight("bold")
                autotext.set_fontsize(10)

            plt.tight_layout()
            return self.save_plot_to_bytes(fig)

        except Exception as e:
            logger.error(f"Ошибка генерации графика источников трафика: {e}")
            return None

    async def generate_engagement_trends_chart(
        self, channel_id: int, days: int = 30
    ) -> Optional[io.BytesIO]:
        """Генерация графика трендов вовлеченности"""
        try:
            # Получаем данные о просмотрах по дням
            start_date = datetime.now() - timedelta(days=days)

            # Создаем имитацию данных для демонстрации
            # В реальном проекте здесь будут реальные данные из БД
            dates = [start_date + timedelta(days=i) for i in range(days)]
            views = np.random.normal(1000, 200, days).astype(int)
            reactions = np.random.normal(50, 15, days).astype(int)
            shares = np.random.normal(20, 8, days).astype(int)

            # Сглаживание данных
            views = np.maximum(views, 0)
            reactions = np.maximum(reactions, 0)
            shares = np.maximum(shares, 0)

            # Создание графика
            fig, ax1 = plt.subplots(figsize=(14, 8))
            fig.suptitle(
                "📊 Тренды вовлеченности аудитории", fontsize=16, fontweight="bold"
            )

            # Основная ось - просмотры
            color1 = "#2E86C1"
            ax1.set_xlabel("Дата", fontsize=12)
            ax1.set_ylabel("Просмотры", color=color1, fontsize=12)
            line1 = ax1.plot(
                dates,
                views,
                color=color1,
                linewidth=3,
                marker="o",
                markersize=4,
                label="Просмотры",
            )
            ax1.tick_params(axis="y", labelcolor=color1)
            ax1.fill_between(dates, views, alpha=0.2, color=color1)

            # Вторая ось - реакции и репосты
            ax2 = ax1.twinx()
            color2 = "#E74C3C"
            color3 = "#28B463"

            ax2.set_ylabel("Реакции / Репосты", fontsize=12)
            line2 = ax2.plot(
                dates,
                reactions,
                color=color2,
                linewidth=2,
                marker="s",
                markersize=4,
                label="Реакции",
            )
            line3 = ax2.plot(
                dates,
                shares,
                color=color3,
                linewidth=2,
                marker="^",
                markersize=4,
                label="Репосты",
            )

            # Форматирование дат
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days // 10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

            # Легенда
            lines = line1 + line2 + line3
            labels = [l.get_label() for l in lines]
            ax1.legend(lines, labels, loc="upper left")

            # Сетка
            ax1.grid(True, alpha=0.3)

            plt.tight_layout()
            return self.save_plot_to_bytes(fig)

        except Exception as e:
            logger.error(f"Ошибка генерации графика трендов вовлеченности: {e}")
            return None

    async def generate_dashboard_chart(self, channel_id: int) -> Optional[io.BytesIO]:
        """Генерация комплексного дашборда"""
        try:
            # Получение сводных данных
            summary = await self.analytics.get_channel_summary(channel_id)

            if not summary:
                return None

            # Создание дашборда
            fig = plt.figure(figsize=(16, 12))
            fig.suptitle("📈 Дашборд аналитики канала", fontsize=18, fontweight="bold")

            # Создание сетки подграфиков
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

            # 1. Основные метрики (текстовый блок)
            ax1 = fig.add_subplot(gs[0, :])
            ax1.axis("off")

            subscribers = summary.get("subscribers_count", 0)
            growth = summary.get("subscriber_growth", 0)
            views = summary.get("total_views", 0)
            posts = summary.get("posts_count", 0)

            metrics_text = f"""
            👥 Подписчиков: {subscribers:,}    📈 Рост: {growth:+d}    👁 Просмотров: {views:,}    📝 Постов: {posts}
            """
            ax1.text(
                0.5,
                0.5,
                metrics_text,
                fontsize=16,
                ha="center",
                va="center",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8),
            )

            # 2. График роста (имитация данных)
            ax2 = fig.add_subplot(gs[1, 0])
            days = 7
            growth_data = [
                growth // days + np.random.randint(-5, 6) for _ in range(days)
            ]
            ax2.plot(range(days), growth_data, marker="o", linewidth=2, color="#2E86C1")
            ax2.set_title("Рост подписчиков", fontweight="bold")
            ax2.set_ylabel("Новые подписчики")
            ax2.grid(True, alpha=0.3)

            # 3. Почасовая активность (имитация)
            ax3 = fig.add_subplot(gs[1, 1])
            hours = range(24)
            activity = [
                max(
                    0,
                    100
                    + 50 * np.sin((h - 12) * np.pi / 12)
                    + np.random.randint(-20, 21),
                )
                for h in hours
            ]
            ax3.bar(hours, activity, color="#E67E22", alpha=0.7)
            ax3.set_title("Активность по часам", fontweight="bold")
            ax3.set_ylabel("Просмотры")
            ax3.set_xticks(range(0, 24, 4))

            # 4. Источники трафика
            ax4 = fig.add_subplot(gs[1, 2])
            sources = ["URL", "Поиск", "Группы", "Каналы"]
            values = [30, 25, 25, 20]
            colors = ["#3498DB", "#E74C3C", "#28B463", "#F39C12"]
            ax4.pie(values, labels=sources, autopct="%1.1f%%", colors=colors)
            ax4.set_title("Источники трафика", fontweight="bold")

            # 5. Тренд вовлеченности
            ax5 = fig.add_subplot(gs[2, :2])
            days_trend = 14
            engagement = [
                max(0, 50 + 10 * np.sin(i * np.pi / 7) + np.random.randint(-5, 6))
                for i in range(days_trend)
            ]
            ax5.plot(
                range(days_trend), engagement, marker="o", linewidth=2, color="#9B59B6"
            )
            ax5.fill_between(range(days_trend), engagement, alpha=0.3, color="#9B59B6")
            ax5.set_title("Тренд вовлеченности", fontweight="bold")
            ax5.set_ylabel("Вовлеченность (%)")
            ax5.grid(True, alpha=0.3)

            # 6. Топ часы
            ax6 = fig.add_subplot(gs[2, 2])
            top_hours = [12, 18, 21]
            top_values = [150, 140, 135]
            bars = ax6.bar(range(len(top_hours)), top_values, color="#16A085")
            ax6.set_title("Топ часы активности", fontweight="bold")
            ax6.set_ylabel("Просмотры")
            ax6.set_xticks(range(len(top_hours)))
            ax6.set_xticklabels([f"{h}:00" for h in top_hours])

            # Добавление значений на столбцы
            for bar, value in zip(bars, top_values):
                ax6.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 2,
                    str(value),
                    ha="center",
                    va="bottom",
                    fontweight="bold",
                )

            return self.save_plot_to_bytes(fig)

        except Exception as e:
            logger.error(f"Ошибка генерации дашборда: {e}")
            return None
