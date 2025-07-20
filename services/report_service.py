import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Optional

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import rcParams

from database.models import (
    ContentAnalytics,
    GroupAnalytics,
    GroupPost,
    TelegramGroup,
    get_db,
)

logger = logging.getLogger(__name__)

# Настройка matplotlib для русского языка
rcParams["font.family"] = "DejaVu Sans"
plt.style.use("seaborn-v0_8")


class ReportService:
    """Сервис для генерации отчетов"""

    def __init__(self):
        self.charts_dir = "charts"
        os.makedirs(self.charts_dir, exist_ok=True)

    async def generate_daily_report(self) -> dict[str, Any]:
        """Генерация ежедневного отчета"""
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # Получение данных
            groups_data = await self._get_groups_analytics_for_period(yesterday, today)
            posts_data = await self._get_posts_analytics_for_period(yesterday, today)

            # Генерация текстового отчета
            text_report = await self._generate_daily_text_report(
                groups_data, posts_data, yesterday
            )

            # Генерация графика
            chart_path = await self._generate_daily_chart(groups_data, yesterday)

            return {"text": text_report, "chart": chart_path, "date": yesterday}

        except Exception as e:
            logger.error(f"Ошибка при генерации ежедневного отчета: {e}")
            return {"text": "❌ Ошибка при генерации отчета", "chart": None}

    async def generate_weekly_report(self) -> dict[str, Any]:
        """Генерация еженедельного отчета"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=7)

            # Получение данных за неделю
            groups_data = await self._get_groups_analytics_for_period(
                start_date, end_date
            )
            posts_data = await self._get_posts_analytics_for_period(
                start_date, end_date
            )
            content_data = await self._get_content_analytics_for_period(
                start_date, end_date
            )

            # Генерация текстового отчета
            text_report = await self._generate_weekly_text_report(
                groups_data, posts_data, content_data, start_date, end_date
            )

            # Генерация графика
            chart_path = await self._generate_weekly_chart(
                groups_data, start_date, end_date
            )

            return {
                "text": text_report,
                "chart": chart_path,
                "start_date": start_date,
                "end_date": end_date,
            }

        except Exception as e:
            logger.error(f"Ошибка при генерации еженедельного отчета: {e}")
            return {"text": "❌ Ошибка при генерации отчета", "chart": None}

    async def generate_monthly_report(self) -> dict[str, Any]:
        """Генерация ежемесячного отчета"""
        try:
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=30)

            # Получение данных за месяц
            groups_data = await self._get_groups_analytics_for_period(
                start_date, end_date
            )
            posts_data = await self._get_posts_analytics_for_period(
                start_date, end_date
            )
            content_data = await self._get_content_analytics_for_period(
                start_date, end_date
            )
            best_worst_posts = await self._get_best_worst_posts(start_date, end_date)

            # Генерация текстового отчета
            text_report = await self._generate_monthly_text_report(
                groups_data,
                posts_data,
                content_data,
                best_worst_posts,
                start_date,
                end_date,
            )

            # Генерация графика
            chart_path = await self._generate_monthly_chart(
                groups_data, start_date, end_date
            )

            return {
                "text": text_report,
                "chart": chart_path,
                "start_date": start_date,
                "end_date": end_date,
            }

        except Exception as e:
            logger.error(f"Ошибка при генерации ежемесячного отчета: {e}")
            return {"text": "❌ Ошибка при генерации отчета", "chart": None}

    async def generate_summary_report(self, target_date: date) -> dict[str, Any]:
        """Генерация отчета за конкретную дату"""
        try:
            next_date = target_date + timedelta(days=1)

            # Получение данных за конкретную дату
            groups_data = await self._get_groups_analytics_for_period(
                target_date, next_date
            )
            posts_data = await self._get_posts_analytics_for_period(
                target_date, next_date
            )

            # Генерация текстового отчета
            text_report = await self._generate_summary_text_report(
                groups_data, posts_data, target_date
            )

            # Генерация графика
            chart_path = await self._generate_daily_chart(groups_data, target_date)

            return {"text": text_report, "chart": chart_path, "date": target_date}

        except Exception as e:
            logger.error(f"Ошибка при генерации отчета за дату: {e}")
            return {"text": "❌ Ошибка при генерации отчета", "chart": None}

    async def _get_groups_analytics_for_period(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Получение аналитики групп за период"""
        db = get_db()
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            analytics = (
                db.query(GroupAnalytics)
                .join(TelegramGroup)
                .filter(
                    GroupAnalytics.date >= start_datetime,
                    GroupAnalytics.date < end_datetime,
                    TelegramGroup.is_active == True,
                )
                .all()
            )

            return [
                {
                    "group_id": a.group_id,
                    "group_title": a.group.title,
                    "date": a.date,
                    "members_count": a.members_count,
                    "members_growth": a.members_growth,
                    "members_growth_percent": a.members_growth_percent,
                    "posts_count": a.posts_count,
                    "avg_views": a.avg_views,
                    "avg_reactions": a.avg_reactions,
                    "total_views": a.total_views,
                }
                for a in analytics
            ]
        finally:
            db.close()

    async def _get_posts_analytics_for_period(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Получение аналитики постов за период"""
        db = get_db()
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            posts = (
                db.query(GroupPost)
                .join(TelegramGroup)
                .filter(
                    GroupPost.post_date >= start_datetime,
                    GroupPost.post_date < end_datetime,
                    TelegramGroup.is_active == True,
                )
                .all()
            )

            return [
                {
                    "group_title": p.group.title,
                    "content_type": p.content_type,
                    "views": p.views,
                    "reactions_count": p.reactions_count,
                    "comments_count": p.comments_count,
                    "post_date": p.post_date,
                    "has_links": p.has_links,
                }
                for p in posts
            ]
        finally:
            db.close()

    async def _get_content_analytics_for_period(
        self, start_date: date, end_date: date
    ) -> list[dict]:
        """Получение аналитики по типам контента за период"""
        db = get_db()
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            content_analytics = (
                db.query(ContentAnalytics)
                .filter(
                    ContentAnalytics.date >= start_datetime,
                    ContentAnalytics.date < end_datetime,
                )
                .all()
            )

            return [
                {
                    "content_type": ca.content_type,
                    "posts_count": ca.posts_count,
                    "avg_views": ca.avg_views,
                    "avg_reactions": ca.avg_reactions,
                    "total_views": ca.total_views,
                    "total_reactions": ca.total_reactions,
                }
                for ca in content_analytics
            ]
        finally:
            db.close()

    async def _get_best_worst_posts(self, start_date: date, end_date: date) -> dict:
        """Получение лучших и худших постов за период"""
        db = get_db()
        try:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.min.time())

            posts = (
                db.query(GroupPost)
                .join(TelegramGroup)
                .filter(
                    GroupPost.post_date >= start_datetime,
                    GroupPost.post_date < end_datetime,
                    TelegramGroup.is_active == True,
                )
                .order_by(GroupPost.views.desc())
                .all()
            )

            if not posts:
                return {"best": [], "worst": []}

            # Топ-5 лучших постов по просмотрам
            best_posts = posts[:5]
            # 5 худших постов по просмотрам
            worst_posts = posts[-5:] if len(posts) > 5 else []

            return {
                "best": [
                    {
                        "group_title": p.group.title,
                        "content_type": p.content_type,
                        "views": p.views,
                        "reactions_count": p.reactions_count,
                        "post_date": p.post_date,
                        "text_preview": (p.text[:50] + "...")
                        if p.text and len(p.text) > 50
                        else p.text,
                    }
                    for p in best_posts
                ],
                "worst": [
                    {
                        "group_title": p.group.title,
                        "content_type": p.content_type,
                        "views": p.views,
                        "reactions_count": p.reactions_count,
                        "post_date": p.post_date,
                        "text_preview": (p.text[:50] + "...")
                        if p.text and len(p.text) > 50
                        else p.text,
                    }
                    for p in worst_posts
                ],
            }
        finally:
            db.close()

    async def _generate_daily_text_report(
        self, groups_data: list[dict], posts_data: list[dict], date: date
    ) -> str:
        """Генерация текстового ежедневного отчета"""
        if not groups_data:
            return f"📊 <b>Ежедневный отчет за {date.strftime('%d.%m.%Y')}</b>\n\n❌ Нет данных за указанную дату"

        # Агрегация данных
        total_members = sum(g["members_count"] for g in groups_data)
        total_growth = sum(g["members_growth"] for g in groups_data)
        total_posts = sum(g["posts_count"] for g in groups_data)
        avg_views = (
            sum(g["avg_views"] for g in groups_data) / len(groups_data)
            if groups_data
            else 0
        )
        avg_reactions = (
            sum(g["avg_reactions"] for g in groups_data) / len(groups_data)
            if groups_data
            else 0
        )

        # Анализ типов контента
        content_stats = {}
        for post in posts_data:
            content_type = post["content_type"]
            content_stats[content_type] = content_stats.get(content_type, 0) + 1

        growth_emoji = "📈" if total_growth > 0 else "📉" if total_growth < 0 else "➡️"

        report = f"""📊 <b>Ежедневный отчет за {date.strftime('%d.%m.%Y')}</b>

👥 <b>Подписчики:</b>
• Общее количество: {total_members:,}
• Изменение за день: {growth_emoji} {total_growth:+,}

📝 <b>Активность:</b>
• Опубликовано постов: {total_posts}
• Среднее количество просмотров: {avg_views:.1f}
• Среднее количество реакций: {avg_reactions:.1f}

📊 <b>Популярные типы контента:</b>"""

        if content_stats:
            sorted_content = sorted(
                content_stats.items(), key=lambda x: x[1], reverse=True
            )
            for content_type, count in sorted_content[:3]:
                content_name = {
                    "text": "Текст",
                    "photo": "Фото",
                    "video": "Видео",
                    "document": "Документы",
                    "audio": "Аудио",
                }.get(content_type, content_type.title())
                report += f"\n• {content_name}: {count} постов"
        else:
            report += "\n• Нет данных о контенте"

        # Рекомендации
        recommendations = []
        if total_growth < 0:
            recommendations.append(
                "Рост подписчиков замедлился. Рекомендуется проанализировать контент-стратегию"
            )
        if avg_reactions < 10:
            recommendations.append(
                "Низкая вовлеченность аудитории. Попробуйте более интерактивный контент"
            )
        if total_posts == 0:
            recommendations.append(
                "Активность публикаций низкая. Рекомендуется увеличить частоту постов"
            )

        if recommendations:
            report += "\n\n💡 <b>Рекомендации:</b>"
            for rec in recommendations:
                report += f"\n• {rec}"

        report += f"\n\n🕐 <i>Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

        return report

    async def _generate_weekly_text_report(
        self,
        groups_data: list[dict],
        posts_data: list[dict],
        content_data: list[dict],
        start_date: date,
        end_date: date,
    ) -> str:
        """Генерация текстового еженедельного отчета"""
        period_str = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"

        if not groups_data:
            return f"📊 <b>Еженедельный отчет за {period_str}</b>\n\n❌ Нет данных за указанный период"

        # Агрегация данных по дням
        daily_stats = {}
        for g in groups_data:
            date_key = g["date"].date()
            if date_key not in daily_stats:
                daily_stats[date_key] = {"members": 0, "growth": 0, "posts": 0}
            daily_stats[date_key]["members"] += g["members_count"]
            daily_stats[date_key]["growth"] += g["members_growth"]
            daily_stats[date_key]["posts"] += g["posts_count"]

        # Общая статистика
        total_growth = sum(day["growth"] for day in daily_stats.values())
        total_posts = sum(day["posts"] for day in daily_stats.values())
        avg_daily_posts = total_posts / 7 if total_posts > 0 else 0

        # Анализ контента
        content_summary = {}
        for content in content_data:
            content_type = content["content_type"]
            if content_type not in content_summary:
                content_summary[content_type] = {
                    "posts": 0,
                    "avg_views": 0,
                    "avg_reactions": 0,
                }
            content_summary[content_type]["posts"] += content["posts_count"]
            content_summary[content_type]["avg_views"] += content["avg_views"]
            content_summary[content_type]["avg_reactions"] += content["avg_reactions"]

        growth_emoji = "📈" if total_growth > 0 else "📉" if total_growth < 0 else "➡️"

        report = f"""📊 <b>Еженедельный отчет за {period_str}</b>

👥 <b>Динамика подписчиков:</b>
• Изменение за неделю: {growth_emoji} {total_growth:+,}
• Среднедневной прирост: {total_growth/7:+.1f}

📝 <b>Активность публикаций:</b>
• Всего постов за неделю: {total_posts}
• Среднее количество постов в день: {avg_daily_posts:.1f}

📊 <b>Анализ контента:</b>"""

        if content_summary:
            sorted_content = sorted(
                content_summary.items(), key=lambda x: x[1]["posts"], reverse=True
            )
            for content_type, stats in sorted_content:
                content_name = {
                    "text": "Текст",
                    "photo": "Фото",
                    "video": "Видео",
                    "document": "Документы",
                    "audio": "Аудио",
                }.get(content_type, content_type.title())

                avg_views = stats["avg_views"] / len(
                    [c for c in content_data if c["content_type"] == content_type]
                )
                report += f"\n• {content_name}: {stats['posts']} постов, ср. просмотров: {avg_views:.0f}"

        # Анализ трендов
        report += "\n\n📈 <b>Тренды недели:</b>"
        sorted_days = sorted(daily_stats.items())

        # Найти лучший и худший день
        best_day = max(sorted_days, key=lambda x: x[1]["growth"])
        worst_day = min(sorted_days, key=lambda x: x[1]["growth"])

        report += f"\n• Лучший день: {best_day[0].strftime('%d.%m')} ({best_day[1]['growth']:+} подписчиков)"
        report += f"\n• Худший день: {worst_day[0].strftime('%d.%m')} ({worst_day[1]['growth']:+} подписчиков)"

        # Рекомендации
        recommendations = []
        if total_growth < 0:
            recommendations.append(
                "Отрицательная динамика подписчиков. Нужно пересмотреть контент-стратегию"
            )
        if avg_daily_posts < 1:
            recommendations.append(
                "Низкая активность публикаций. Рекомендуется публиковать минимум 1-2 поста в день"
            )

        if recommendations:
            report += "\n\n💡 <b>Рекомендации:</b>"
            for rec in recommendations:
                report += f"\n• {rec}"

        report += f"\n\n🕐 <i>Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"

        return report

    async def _generate_monthly_text_report(
        self,
        groups_data: list[dict],
        posts_data: list[dict],
        content_data: list[dict],
        best_worst_posts: dict,
        start_date: date,
        end_date: date,
    ) -> str:
        """Генерация текстового ежемесячного отчета"""
        period_str = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"

        if not groups_data:
            return f"📊 <b>Ежемесячный отчет за {period_str}</b>\n\n❌ Нет данных за указанный период"

        # Подробная аналитика (базируется на еженедельном отчете, но расширена)
        weekly_report = await self._generate_weekly_text_report(
            groups_data, posts_data, content_data, start_date, end_date
        )

        # Заменяем заголовок
        monthly_report = weekly_report.replace(
            "Еженедельный отчет", "Ежемесячный отчет"
        )
        monthly_report = monthly_report.replace("за неделю", "за месяц")

        # Добавляем анализ лучших/худших постов
        if best_worst_posts["best"]:
            monthly_report += "\n\n🏆 <b>Топ-3 поста месяца:</b>"
            for i, post in enumerate(best_worst_posts["best"][:3], 1):
                monthly_report += f"\n{i}. {post['views']:,} просмотров, {post['reactions_count']} реакций"
                if post["text_preview"]:
                    monthly_report += f" - {post['text_preview']}"

        if best_worst_posts["worst"]:
            monthly_report += "\n\n📉 <b>Посты с низкой активностью:</b>"
            for post in best_worst_posts["worst"][:3]:
                monthly_report += f"\n• {post['views']} просмотров - требует анализа"

        return monthly_report

    async def _generate_summary_text_report(
        self, groups_data: list[dict], posts_data: list[dict], date: date
    ) -> str:
        """Генерация текстового отчета за конкретную дату"""
        return await self._generate_daily_text_report(groups_data, posts_data, date)

    async def _generate_daily_chart(
        self, groups_data: list[dict], date: date
    ) -> Optional[str]:
        """Генерация графика для ежедневного отчета"""
        if not groups_data:
            return None

        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
            fig.suptitle(
                f'Ежедневная аналитика - {date.strftime("%d.%m.%Y")}',
                fontsize=16,
                fontweight="bold",
            )

            # График 1: Количество подписчиков по группам
            groups = [g["group_title"][:20] for g in groups_data]
            members = [g["members_count"] for g in groups_data]

            ax1.bar(range(len(groups)), members, color="skyblue")
            ax1.set_title("Количество подписчиков")
            ax1.set_xticks(range(len(groups)))
            ax1.set_xticklabels(groups, rotation=45, ha="right")
            ax1.ticklabel_format(style="plain", axis="y")

            # График 2: Прирост подписчиков
            growth = [g["members_growth"] for g in groups_data]
            colors = ["green" if g > 0 else "red" if g < 0 else "gray" for g in growth]

            ax2.bar(range(len(groups)), growth, color=colors)
            ax2.set_title("Прирост подписчиков")
            ax2.set_xticks(range(len(groups)))
            ax2.set_xticklabels(groups, rotation=45, ha="right")
            ax2.axhline(y=0, color="black", linestyle="-", alpha=0.3)

            # График 3: Количество постов
            posts = [g["posts_count"] for g in groups_data]
            ax3.bar(range(len(groups)), posts, color="orange")
            ax3.set_title("Количество постов")
            ax3.set_xticks(range(len(groups)))
            ax3.set_xticklabels(groups, rotation=45, ha="right")

            # График 4: Средние просмотры
            avg_views = [g["avg_views"] for g in groups_data]
            ax4.bar(range(len(groups)), avg_views, color="lightcoral")
            ax4.set_title("Средние просмотры")
            ax4.set_xticks(range(len(groups)))
            ax4.set_xticklabels(groups, rotation=45, ha="right")

            plt.tight_layout()

            # Сохранение графика
            chart_path = os.path.join(
                self.charts_dir, f'daily_report_{date.strftime("%Y%m%d")}.png'
            )
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()

            return chart_path

        except Exception as e:
            logger.error(f"Ошибка при генерации ежедневного графика: {e}")
            return None

    async def _generate_weekly_chart(
        self, groups_data: list[dict], start_date: date, end_date: date
    ) -> Optional[str]:
        """Генерация графика для еженедельного отчета"""
        if not groups_data:
            return None

        try:
            # Подготовка данных по дням
            df = pd.DataFrame(groups_data)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            daily_data = (
                df.groupby("date")
                .agg(
                    {"members_growth": "sum", "posts_count": "sum", "avg_views": "mean"}
                )
                .reset_index()
            )

            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
            period_str = (
                f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}"
            )
            fig.suptitle(
                f"Еженедельная аналитика - {period_str}", fontsize=16, fontweight="bold"
            )

            # График 1: Динамика прироста подписчиков
            ax1.plot(
                daily_data["date"],
                daily_data["members_growth"],
                marker="o",
                linewidth=2,
                color="blue",
            )
            ax1.set_title("Динамика прироста подписчиков")
            ax1.set_ylabel("Прирост")
            ax1.grid(True, alpha=0.3)
            ax1.axhline(y=0, color="red", linestyle="--", alpha=0.5)

            # График 2: Количество постов по дням
            ax2.bar(
                daily_data["date"], daily_data["posts_count"], color="orange", alpha=0.7
            )
            ax2.set_title("Активность публикаций")
            ax2.set_ylabel("Количество постов")
            ax2.grid(True, alpha=0.3)

            # График 3: Средние просмотры
            ax3.plot(
                daily_data["date"],
                daily_data["avg_views"],
                marker="s",
                linewidth=2,
                color="green",
            )
            ax3.set_title("Средние просмотры постов")
            ax3.set_ylabel("Просмотры")
            ax3.set_xlabel("Дата")
            ax3.grid(True, alpha=0.3)

            # Форматирование дат на осях
            for ax in [ax1, ax2, ax3]:
                ax.tick_params(axis="x", rotation=45)

            plt.tight_layout()

            # Сохранение графика
            chart_path = os.path.join(
                self.charts_dir,
                f'weekly_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.png',
            )
            plt.savefig(chart_path, dpi=300, bbox_inches="tight")
            plt.close()

            return chart_path

        except Exception as e:
            logger.error(f"Ошибка при генерации еженедельного графика: {e}")
            return None

    async def _generate_monthly_chart(
        self, groups_data: list[dict], start_date: date, end_date: date
    ) -> Optional[str]:
        """Генерация графика для ежемесячного отчета"""
        # Используем еженедельный график как базу, но с расширенным анализом
        return await self._generate_weekly_chart(groups_data, start_date, end_date)
