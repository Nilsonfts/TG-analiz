import logging

from channel_analytics import ChannelAnalytics

logger = logging.getLogger(__name__)


class ChannelReportService:
    """Сервис для генерации красивых отчетов каналов"""

    def __init__(self, analytics: ChannelAnalytics):
        self.analytics = analytics

    def format_number(self, num: int) -> str:
        """Красивое форматирование чисел"""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(num)

    def get_growth_emoji(self, percentage: float) -> str:
        """Эмодзи для роста"""
        if percentage > 10:
            return "🚀"
        elif percentage > 5:
            return "📈"
        elif percentage > 0:
            return "⬆️"
        elif percentage == 0:
            return "➡️"
        else:
            return "📉"

    def get_engagement_emoji(self, percentage: float) -> str:
        """Эмодзи для вовлеченности"""
        if percentage > 80:
            return "🔥"
        elif percentage > 60:
            return "✨"
        elif percentage > 40:
            return "📢"
        elif percentage > 20:
            return "⚡"
        else:
            return "💤"

    async def generate_channel_summary_report(self, channel_id: int) -> str:
        """Генерация сводного отчета канала"""
        try:
            summary = await self.analytics.get_channel_summary(channel_id)

            if not summary:
                return "❌ Канал не найден или нет данных"

            # Базовая информация
            title = summary.get("title", "Неизвестный канал")[:50]
            subscribers = self.format_number(summary.get("subscribers_count", 0))
            posts = summary.get("posts_count", 0)

            # Рост подписчиков
            summary.get("subscriber_growth", 0)
            growth_percent = summary.get("growth_percentage", 0)
            growth_emoji = self.get_growth_emoji(growth_percent)

            # Просмотры
            self.format_number(summary.get("total_views", 0))
            self.format_number(summary.get("story_views", 0))

            # Реакции
            summary.get("reactions_count", 0)

            # Уведомления
            notifications_percent = summary.get("notifications_enabled_percent", 0)
            self.get_engagement_emoji(notifications_percent)

            report = f"""📊 <b>СВОДНЫЙ ОТЧЁТ КАНАЛА</b>

📁 <b>Канал:</b> {title}
👥 <b>Участников:</b> {subscribers}

📈 <b>ОБЩАЯ СТАТИСТИКА:</b>
• Всего сообщений: {posts}
• Уникальных пользователей: {subscribers}
• Среднее в день: {summary.get('total_views', 0) // 7:.0f} просмотров

{growth_emoji} <b>АКТИВНОСТЬ:</b>
• Самый активный: N/A
• Вовлечённость: {notifications_percent:.1f}%

⏰ <b>ПИКОВЫЕ ЧАСЫ:</b>
Данных недостаточно

📅 <b>СЕГОДНЯ:</b>
• Сообщений: 0
• Активных пользователей: 0

💡 <b>РЕКОМЕНДАЦИИ:</b>
• 🔥 Стимулируйте обсуждения - активность низкая
• 👥 Низкая вовлечённость - привлекайте участников

📊 <b>Используйте:</b>
• /charts - графики
• /export - экспорт данных
• /alerts - проверка алертов"""

            return report

        except Exception as e:
            logger.error(f"Ошибка генерации сводного отчета: {e}")
            return f"❌ Ошибка генерации отчета: {e}"

    async def generate_growth_report(self, channel_id: int) -> str:
        """Генерация отчета роста подписчиков"""
        try:
            summary = await self.analytics.get_channel_summary(channel_id)
            growth_data = await self.analytics.get_subscriber_growth_data(channel_id, 7)

            if not summary:
                return "❌ Канал не найден"

            title = summary.get("title", "Неизвестный канал")[:30]
            current_subs = summary.get("subscribers_count", 0)
            growth = summary.get("subscriber_growth", 0)
            growth_percent = summary.get("growth_percentage", 0)
            growth_emoji = self.get_growth_emoji(growth_percent)

            # Анализ тренда
            if len(growth_data) >= 2:
                recent_trend = (
                    growth_data[-1]["subscribers_gained"]
                    - growth_data[-2]["subscribers_gained"]
                )
                trend_emoji = (
                    "📈" if recent_trend > 0 else "📉" if recent_trend < 0 else "➡️"
                )
            else:
                trend_emoji = "➡️"

            report = f"""📈 <b>РОСТ ПОДПИСЧИКОВ</b>

📁 <b>Канал:</b> {title}

{growth_emoji} <b>СТАТИСТИКА ЗА 7 ДНЕЙ:</b>
• Текущие подписчики: {self.format_number(current_subs)}
• Прирост: {growth:+d} ({growth_percent:+.2f}%)
• Среднее в день: {growth/7:.1f}

{trend_emoji} <b>ТРЕНД:</b>
• Направление: {"Рост" if growth > 0 else "Падение" if growth < 0 else "Стабильно"}
• Скорость: {"Быстрая" if abs(growth_percent) > 10 else "Умеренная" if abs(growth_percent) > 2 else "Медленная"}

📊 <b>ПОСЛЕДНИЕ ДНИ:</b>"""

            # Добавляем данные по дням
            for day_data in growth_data[-5:]:  # Последние 5 дней
                date = day_data["date"].strftime("%d.%m")
                gained = day_data["subscribers_gained"]
                lost = day_data["subscribers_lost"]
                net = gained - lost
                emoji = "✅" if net > 0 else "❌" if net < 0 else "➖"
                report += f"\n{emoji} {date}: {net:+d} ({gained} новых, {lost} ушло)"

            # Рекомендации
            recommendations = await self.analytics.generate_recommendations(channel_id)
            report += "\n\n💡 <b>РЕКОМЕНДАЦИИ:</b>"
            for rec in recommendations[:3]:
                report += f"\n• {rec}"

            report += "\n\n📊 Используйте /charts для графиков роста"

            return report

        except Exception as e:
            logger.error(f"Ошибка генерации отчета роста: {e}")
            return f"❌ Ошибка генерации отчета: {e}"

    async def generate_engagement_report(self, channel_id: int) -> str:
        """Генерация отчета вовлеченности"""
        try:
            summary = await self.analytics.get_channel_summary(channel_id)
            hourly_data = await self.analytics.get_hourly_views_data(channel_id, 7)

            if not summary:
                return "❌ Канал не найден"

            title = summary.get("title", "Неизвестный канал")[:30]
            total_views = summary.get("total_views", 0)
            story_views = summary.get("story_views", 0)
            subscribers = summary.get("subscribers_count", 1)
            notifications_percent = summary.get("notifications_enabled_percent", 0)

            # Расчет охвата
            reach_percent = (total_views / subscribers * 100) if subscribers > 0 else 0
            reach_emoji = self.get_engagement_emoji(reach_percent)

            notifications_emoji = self.get_engagement_emoji(notifications_percent)

            report = f"""⚡ <b>ВОВЛЕЧЕННОСТЬ АУДИТОРИИ</b>

📁 <b>Канал:</b> {title}

{reach_emoji} <b>ОХВАТ ЗА 7 ДНЕЙ:</b>
• Просмотры постов: {self.format_number(total_views)}
• Просмотры историй: {self.format_number(story_views)}
• Охват аудитории: {reach_percent:.1f}%
• Реакции на посты: {summary.get('reactions_count', 0)}

{notifications_emoji} <b>УВЕДОМЛЕНИЯ:</b>
• Включены: {notifications_percent:.1f}%
• Вовлеченность: {"Высокая" if notifications_percent > 60 else "Средняя" if notifications_percent > 30 else "Низкая"}

⏰ <b>ПИКОВЫЕ ЧАСЫ АКТИВНОСТИ:</b>"""

            # Находим топ-3 часа
            if hourly_data:
                sorted_hours = sorted(
                    hourly_data, key=lambda x: x["total_views"], reverse=True
                )
                for i, hour_data in enumerate(sorted_hours[:3], 1):
                    hour = hour_data["hour_of_day"]
                    views = hour_data["total_views"]
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    report += f"\n{emoji} {hour:02d}:00 - {self.format_number(views)} просмотров"
            else:
                report += "\nДанных недостаточно"

            # Анализ вовлеченности
            if reach_percent > 50:
                engagement_level = "🔥 Отличная"
            elif reach_percent > 30:
                engagement_level = "✨ Хорошая"
            elif reach_percent > 15:
                engagement_level = "📢 Средняя"
            else:
                engagement_level = "💤 Низкая"

            report += f"""

📊 <b>АНАЛИЗ:</b>
• Уровень вовлеченности: {engagement_level}
• Средние просмотры: {total_views // 7:.0f}/день
• Коэффициент реакций: {(summary.get('reactions_count', 0) / max(1, summary.get('posts_count', 1)) * 100):.1f}%"""

            # Рекомендации
            recommendations = await self.analytics.generate_recommendations(channel_id)
            report += "\n\n💡 <b>РЕКОМЕНДАЦИИ:</b>"
            for rec in recommendations[:2]:
                report += f"\n• {rec}"

            return report

        except Exception as e:
            logger.error(f"Ошибка генерации отчета вовлеченности: {e}")
            return f"❌ Ошибка генерации отчета: {e}"

    async def generate_traffic_report(self, channel_id: int) -> str:
        """Генерация отчета источников трафика"""
        try:
            summary = await self.analytics.get_channel_summary(channel_id)
            traffic_data = await self.analytics.get_traffic_sources_data(channel_id, 30)

            if not summary:
                return "❌ Канал не найден"

            title = summary.get("title", "Неизвестный канал")[:30]

            # Эмодзи для источников
            source_emojis = {
                "url": "🔗",
                "search": "🔍",
                "groups": "👥",
                "channels": "📢",
                "private_chats": "💬",
                "other": "🌐",
            }

            source_names = {
                "url": "URL ссылки",
                "search": "Поиск",
                "groups": "Группы",
                "channels": "Каналы",
                "private_chats": "Личные чаты",
                "other": "Другое",
            }

            report = f"""🎯 <b>ИСТОЧНИКИ ТРАФИКА</b>

📁 <b>Канал:</b> {title}
📅 <b>Период:</b> Последние 30 дней

📊 <b>ИСТОЧНИКИ ПОДПИСЧИКОВ:</b>"""

            if traffic_data:
                total_subs = sum(item["total_subscribers"] for item in traffic_data)

                for item in traffic_data:
                    source = item["source_type"]
                    subs = item["total_subscribers"]
                    views = item["total_views"]
                    percentage = (subs / total_subs * 100) if total_subs > 0 else 0

                    emoji = source_emojis.get(source, "📊")
                    name = source_names.get(source, source.title())

                    report += f"\n{emoji} <b>{name}:</b> {subs} ({percentage:.1f}%)"
            else:
                report += "\nДанных недостаточно"

            report += """

📈 <b>ПРОСМОТРЫ ПО ИСТОЧНИКАМ:</b>"""

            if traffic_data:
                total_views = sum(item["total_views"] for item in traffic_data)

                for item in traffic_data:
                    source = item["source_type"]
                    views = item["total_views"]
                    percentage = (views / total_views * 100) if total_views > 0 else 0

                    emoji = source_emojis.get(source, "📊")
                    name = source_names.get(source, source.title())

                    report += f"\n{emoji} {name}: {self.format_number(views)} ({percentage:.1f}%)"

            # Анализ и рекомендации
            if traffic_data:
                top_source = max(traffic_data, key=lambda x: x["total_subscribers"])
                top_source_name = source_names.get(
                    top_source["source_type"], "Неизвестно"
                )

                report += f"""

🔍 <b>АНАЛИЗ:</b>
• Основной источник: {top_source_name}
• Всего источников: {len(traffic_data)}
• Эффективность: {"Высокая" if len(traffic_data) > 3 else "Средняя" if len(traffic_data) > 1 else "Низкая"}

💡 <b>РЕКОМЕНДАЦИИ:</b>"""

                if len(traffic_data) <= 2:
                    report += "\n• 🎯 Диверсифицируйте источники трафика"
                    report += "\n• 📢 Развивайте партнерства с другими каналами"
                else:
                    report += "\n• ✅ Хорошее разнообразие источников"
                    report += (
                        f"\n• 🚀 Усиливайте работу с топ-источником: {top_source_name}"
                    )

            return report

        except Exception as e:
            logger.error(f"Ошибка генерации отчета трафика: {e}")
            return f"❌ Ошибка генерации отчета: {e}"

    async def generate_recommendations_report(self, channel_id: int) -> str:
        """Генерация отчета с AI-рекомендациями"""
        try:
            summary = await self.analytics.get_channel_summary(channel_id)
            recommendations = await self.analytics.generate_recommendations(channel_id)

            if not summary:
                return "❌ Канал не найден"

            title = summary.get("title", "Неизвестный канал")[:30]

            # Анализ текущего состояния
            growth = summary.get("growth_percentage", 0)
            notifications = summary.get("notifications_enabled_percent", 0)
            subscribers = summary.get("subscribers_count", 0)

            # Определение уровня канала
            if subscribers > 100000:
                level = "🏆 Крупный канал"
            elif subscribers > 10000:
                level = "⭐ Средний канал"
            elif subscribers > 1000:
                level = "📈 Растущий канал"
            else:
                level = "🌱 Новый канал"

            report = f"""🤖 <b>AI-РЕКОМЕНДАЦИИ</b>

📁 <b>Канал:</b> {title}
📊 <b>Уровень:</b> {level}

🎯 <b>ТЕКУЩЕЕ СОСТОЯНИЕ:</b>
• Подписчики: {self.format_number(subscribers)}
• Рост за неделю: {growth:+.1f}%
• Вовлеченность: {notifications:.1f}%
• Статус: {"🔥 Активно растет" if growth > 5 else "📈 Стабильный рост" if growth > 0 else "⚠️ Нужна оптимизация"}

💡 <b>ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ:</b>"""

            for i, rec in enumerate(recommendations, 1):
                report += f"\n{i}. {rec}"

            # Дополнительные советы по уровню канала
            report += "\n\n🎓 <b>СТРАТЕГИЧЕСКИЕ СОВЕТЫ:</b>"

            if subscribers < 1000:
                report += "\n• 🎯 Определите нишу и целевую аудиторию"
                report += "\n• 📝 Создавайте регулярный контент-план"
                report += "\n• 🤝 Ищите партнерства с похожими каналами"
            elif subscribers < 10000:
                report += "\n• 📊 Анализируйте лучшие посты и повторяйте успех"
                report += "\n• 🎬 Экспериментируйте с разными форматами"
                report += "\n• 💬 Активно взаимодействуйте с аудиторией"
            else:
                report += "\n• 🚀 Масштабируйте успешные стратегии"
                report += "\n• 📈 Оптимизируйте монетизацию"
                report += "\n• 🌐 Развивайте экосистему вокруг канала"

            # Следующие шаги
            report += f"""

📋 <b>ПЛАН ДЕЙСТВИЙ НА НЕДЕЛЮ:</b>
1. 📊 Проанализируйте статистику через /charts
2. 🎯 Оптимизируйте время публикации постов
3. 💬 Увеличьте интерактивность контента
4. 📢 Проведите активность для вовлечения аудитории

⏰ <b>Рекомендуемая частота анализа:</b> {"Ежедневно" if subscribers > 50000 else "2-3 раза в неделю" if subscribers > 5000 else "Еженедельно"}"""

            return report

        except Exception as e:
            logger.error(f"Ошибка генерации отчета рекомендаций: {e}")
            return f"❌ Ошибка генерации отчета: {e}"
