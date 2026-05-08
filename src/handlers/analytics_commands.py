"""
Расширенные команды бота для Channel Analytics
Полная реализация аналитических функций
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BufferedInputFile,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..db.database_service import DatabaseService
from ..config import settings
from .analytics_charts import (
    render_channel_dashboard_png,
    render_growth_overview_png,
    WEEKDAYS_RU,
)

logger = logging.getLogger(__name__)

# Состояния для FSM
class ChannelStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_days = State()

class AnalyticsCommands:
    """Расширенные команды для аналитики каналов"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.router = Router()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        
        # Команды администратора
        @self.router.message(Command("add"))
        async def add_channel_command(message: Message, state: FSMContext):
            """Добавление канала в мониторинг"""
            if not await self.is_admin(message.from_user.id):
                await message.answer("❌ Эта команда доступна только администраторам")
                return
            
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if not args:
                await message.answer(
                    "📝 <b>Добавление канала в мониторинг</b>\n\n"
                    "Использование: <code>/add @channel_username</code>\n"
                    "Или: <code>/add -1001234567890</code>\n\n"
                    "Пример: <code>/add @durov</code>",
                    parse_mode="HTML"
                )
                return
            
            channel_input = args[0]
            await self.add_channel_to_monitoring(message, channel_input)
        
        @self.router.message(Command("remove"))
        async def remove_channel_command(message: Message):
            """Удаление канала из мониторинга"""
            if not await self.is_admin(message.from_user.id):
                await message.answer("❌ Эта команда доступна только администраторам")
                return
            
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if not args:
                await message.answer(
                    "📝 <b>Удаление канала из мониторинга</b>\n\n"
                    "Использование: <code>/remove @channel_username</code>\n"
                    "Или: <code>/remove -1001234567890</code>",
                    parse_mode="HTML"
                )
                return
            
            channel_input = args[0]
            await self.remove_channel_from_monitoring(message, channel_input)
        
        @self.router.message(Command("list"))
        async def list_channels_command(message: Message):
            """Список всех отслеживаемых каналов"""
            if not await self.is_admin(message.from_user.id):
                await message.answer("❌ Эта команда доступна только администраторам")
                return
            
            await self.show_channels_list(message)
        
        @self.router.message(Command("stats"))
        async def channel_stats_command(message: Message):
            """Детальная статистика канала"""
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if not args:
                await message.answer(
                    "📊 <b>Статистика канала</b>\n\n"
                    "Использование: <code>/stats @channel_username [дни]</code>\n\n"
                    "Примеры:\n"
                    "• <code>/stats @durov</code> - за последние 7 дней\n"
                    "• <code>/stats @durov 30</code> - за последние 30 дней",
                    parse_mode="HTML"
                )
                return
            
            channel_input = args[0]
            days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
            days = min(days, 365)  # Максимум год
            
            await self.show_channel_stats(message, channel_input, days)
        
        # Пользовательские команды
        @self.router.message(Command("summary"))
        async def summary_command(message: Message):
            """Сводка по всем каналам"""
            await self.show_summary(message)
        
        @self.router.message(Command("growth"))
        async def growth_command(message: Message):
            """Статистика роста"""
            await self.show_growth_stats(message)
        
        @self.router.message(Command("channels"))
        async def channels_command(message: Message):
            """Публичный список каналов"""
            await self.show_public_channels_list(message)

        @self.router.message(Command("chart"))
        async def chart_command(message: Message):
            """Сводный график-дашборд по каналу."""
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            if not args:
                await message.answer(
                    "📊 <b>График канала</b>\n\n"
                    "Использование: <code>/chart @channel [дни]</code>\n\n"
                    "Пример: <code>/chart @durov 30</code>",
                    parse_mode="HTML",
                )
                return

            channel_input = args[0]
            days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7
            days = min(days, 365)
            await self.send_channel_chart(message, channel_input, days)

        @self.router.message(Command("growth_chart"))
        async def growth_chart_command(message: Message):
            """Сравнительный график роста всех каналов."""
            await self.send_growth_chart(message)
        
        # Callback обработчики
        @self.router.callback_query(F.data.startswith("channel_"))
        async def channel_callback_handler(callback: CallbackQuery):
            """Обработчик inline кнопок для каналов"""
            await self.handle_channel_callback(callback)
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        return user_id in settings.admin_user_ids
    
    async def add_channel_to_monitoring(self, message: Message, channel_input: str):
        """Добавление канала в мониторинг"""
        try:
            # Парсим входные данные
            if channel_input.startswith('@'):
                username = channel_input[1:]
                channel_id = await self.get_channel_id_by_username(username)
            elif channel_input.startswith('-100'):
                channel_id = int(channel_input)
                username = await self.get_username_by_channel_id(channel_id)
            else:
                await message.answer("❌ Неверный формат канала. Используйте @username или -1001234567890")
                return
            
            if not channel_id:
                await message.answer("❌ Не удалось найти канал. Проверьте корректность данных.")
                return
            
            # Получаем информацию о канале
            channel_info = await self.get_channel_info(channel_id)
            
            # Добавляем в базу данных
            channel = await self.db.add_channel(
                channel_id=channel_id,
                username=username,
                title=channel_info.get('title'),
                description=channel_info.get('description')
            )
            
            await message.answer(
                f"✅ <b>Канал добавлен в мониторинг!</b>\n\n"
                f"📺 <b>Название:</b> {channel_info.get('title', 'Не указано')}\n"
                f"👤 <b>Username:</b> @{username or 'Не указан'}\n"
                f"🆔 <b>ID:</b> <code>{channel_id}</code>\n"
                f"👥 <b>Подписчики:</b> {channel_info.get('members_count', 'Неизвестно')}\n\n"
                f"🔄 Сбор данных начнется автоматически",
                parse_mode="HTML"
            )
            
        except Exception as e:
            logger.error(f"Ошибка добавления канала: {e}")
            await message.answer(f"❌ Ошибка при добавлении канала: {str(e)}")
    
    async def remove_channel_from_monitoring(self, message: Message, channel_input: str):
        """Удаление канала из мониторинга"""
        try:
            # Парсим входные данные
            if channel_input.startswith('@'):
                username = channel_input[1:]
                channel_id = await self.get_channel_id_by_username(username)
            elif channel_input.startswith('-100'):
                channel_id = int(channel_input)
            else:
                await message.answer("❌ Неверный формат канала")
                return
            
            if not channel_id:
                await message.answer("❌ Канал не найден")
                return
            
            # Удаляем из мониторинга
            success = await self.db.remove_channel(channel_id)
            
            if success:
                await message.answer(
                    f"✅ <b>Канал удален из мониторинга</b>\n\n"
                    f"🆔 ID: <code>{channel_id}</code>\n"
                    f"📊 Исторические данные сохранены",
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Канал не найден в мониторинге")
                
        except Exception as e:
            logger.error(f"Ошибка удаления канала: {e}")
            await message.answer(f"❌ Ошибка при удалении канала: {str(e)}")
    
    async def show_channels_list(self, message: Message):
        """Показать список всех отслеживаемых каналов"""
        try:
            channels = await self.db.get_active_channels()
            
            if not channels:
                await message.answer(
                    "📋 <b>Список каналов в мониторинге</b>\n\n"
                    "❌ Нет активных каналов\n\n"
                    "Добавьте канал командой: <code>/add @channel</code>",
                    parse_mode="HTML"
                )
                return
            
            text = "📋 <b>Каналы в мониторинге:</b>\n\n"
            
            for i, channel in enumerate(channels, 1):
                username_display = f"@{channel.username}" if channel.username else "Без username"
                text += (
                    f"{i}. <b>{channel.title or 'Без названия'}</b>\n"
                    f"   👤 {username_display}\n"
                    f"   🆔 <code>{channel.channel_id}</code>\n"
                    f"   👥 {channel.subscribers_count:,} подписчиков\n\n"
                )
            
            # Добавляем inline кнопки для быстрых действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📊 Сводка", callback_data="summary_all"),
                    InlineKeyboardButton(text="📈 Рост", callback_data="growth_all")
                ],
                [
                    InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_list")
                ]
            ])
            
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка получения списка каналов: {e}")
            await message.answer(f"❌ Ошибка получения списка: {str(e)}")
    
    async def show_channel_stats(self, message: Message, channel_input: str, days: int):
        """Показать детальную статистику канала"""
        try:
            # Получаем ID канала
            if channel_input.startswith('@'):
                username = channel_input[1:]
                channel_id = await self.get_channel_id_by_username(username)
            elif channel_input.startswith('-100'):
                channel_id = int(channel_input)
            elif channel_input.lstrip('-').isdigit():
                channel_id = int(channel_input)
            else:
                await message.answer("❌ Неверный формат канала")
                return
            
            if not channel_id:
                await message.answer("❌ Канал не найден")
                return
            
            # Получаем аналитику
            analytics = await self.db.get_channel_analytics(channel_id, days)
            
            if not analytics:
                await message.answer("❌ Нет данных по этому каналу")
                return
            
            channel_info = analytics['channel']
            members_history = analytics['members_history']
            views_history = analytics['views_history']
            period = analytics.get('period', {})
            content_breakdown = analytics.get('content_breakdown', {})
            top_posts = analytics.get('top_posts', [])
            
            # Формируем отчет
            text = f"📊 <b>Статистика канала за {days} дней</b>\n\n"
            text += f"📺 <b>{channel_info['title']}</b>\n"
            if channel_info['username']:
                text += f"👤 @{channel_info['username']}\n"
            text += f"🆔 <code>{channel_info['id']}</code>\n\n"
            
            # Текущие показатели
            text += f"👥 <b>Подписчики:</b> {channel_info['subscribers']:,}\n"
            text += f"📝 <b>Постов:</b> {channel_info['posts_count']:,}\n\n"
            
            # Динамика подписчиков
            if period:
                text += f"📈 <b>Рост подписчиков:</b>\n"
                text += f"   • За период: {period.get('members_total_growth', 0):+,} ({period.get('members_growth_percent', 0):+.1f}%)\n"
                text += f"   • В день (среднее): {period.get('avg_daily_growth', 0):+.1f}\n"
                text += f"   • Дней роста/падения/стабильных: {period.get('growth_days', 0)}/{period.get('decline_days', 0)}/{period.get('stable_days', 0)}\n\n"
            
            # Просмотры
            if period:
                text += f"👁 <b>Охваты и вовлеченность:</b>\n"
                text += f"   • Постов за период: {period.get('total_posts', 0):,} (≈ {period.get('avg_posts_per_day', 0):.1f}/день)\n"
                text += f"   • Суммарные просмотры: {period.get('total_views', 0):,}\n"
                text += f"   • Средний охват поста: {period.get('avg_views_per_post', 0):,.0f}\n"
                text += f"   • Средние реакции/репосты: {period.get('avg_reactions_per_post', 0):.1f}/{period.get('avg_forwards_per_post', 0):.1f}\n"
                text += "\n"

                text += f"🎯 <b>ER-метрики:</b>\n"
                text += f"   • ER classic (от подписчиков): {period.get('er_classic', 0):.2f}%\n"
                text += f"   • ERR (от просмотров): {period.get('err', 0):.2f}%\n"
                text += f"   • VTR/Reach Rate (охват/подписчики): {period.get('vtr', 0):.2f}%\n"
                text += f"   • Средний ER поста: {period.get('avg_post_er', 0):.2f}%\n\n"

                best_hour = period.get('best_posting_hour')
                best_wd = period.get('best_posting_weekday')
                if best_hour is not None or best_wd is not None:
                    text += "⏰ <b>Лучшее время публикации:</b>\n"
                    if best_hour is not None:
                        text += (
                            f"   • Час: {int(best_hour):02d}:00 "
                            f"(ср. {period.get('best_posting_hour_avg_views', 0):,.0f} просмотров)\n"
                        )
                    if best_wd is not None:
                        weekday_name = WEEKDAYS_RU[int(best_wd)] if 0 <= int(best_wd) < 7 else str(best_wd)
                        text += (
                            f"   • День недели: {weekday_name} "
                            f"(ср. {period.get('best_posting_weekday_avg_views', 0):,.0f} просмотров)\n"
                        )
                    text += "\n"

            if content_breakdown:
                text += "🧩 <b>Контент-микс:</b>\n"
                sorted_content = sorted(
                    content_breakdown.items(),
                    key=lambda item: item[1].get('posts_count', 0),
                    reverse=True,
                )
                for content_type, stats in sorted_content[:5]:
                    text += (
                        f"   • {content_type}: {int(stats.get('posts_count', 0))} постов"
                        f", ср. {stats.get('avg_views', 0):,.0f} просмотров\n"
                    )
                text += "\n"
            
            # Топ постов
            if top_posts:
                text += "🏆 <b>Топ постов по охвату:</b>\n"
                for post in top_posts[:3]:
                    post_text = post['text'][:50] + '...' if post['text'] and len(post['text']) > 50 else (post['text'] or 'Без текста')
                    text += (
                        f"   • {post_text}\n"
                        f"     👁 {int(post['views']):,} | 👍 {int(post.get('reactions_count', 0)):,} | "
                        f"🔄 {int(post['forwards']):,} | ER {post.get('engagement_rate', 0):.2f}%\n"
                    )

            # Авто-рекомендации
            recommendations = self._build_recommendations(period, content_breakdown, top_posts)
            if recommendations:
                text += "\n💡 <b>Рекомендации:</b>\n"
                for tip in recommendations:
                    text += f"   • {tip}\n"

            text += f"\n🕐 <i>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
            
            # Inline кнопки для дополнительных действий
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📈 7 дней", callback_data=f"stats_{channel_id}_7"),
                    InlineKeyboardButton(text="📊 30 дней", callback_data=f"stats_{channel_id}_30")
                ],
                [
                    InlineKeyboardButton(text="📋 Экспорт CSV", callback_data=f"export_{channel_id}_csv"),
                    InlineKeyboardButton(text="📊 График", callback_data=f"chart_{channel_id}")
                ]
            ])
            
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await message.answer(f"❌ Ошибка получения статистики: {str(e)}")
    
    async def show_summary(self, message: Message):
        """Показать общую сводку по всем каналам с ER-метриками."""
        try:
            channels = await self.db.get_active_channels()

            if not channels:
                await message.answer("📊 Нет каналов в мониторинге")
                return

            rows: List[Dict[str, Any]] = []
            for channel in channels:
                analytics = await self.db.get_channel_analytics(channel.channel_id, 7)
                period = (analytics or {}).get("period", {}) if analytics else {}
                rows.append(
                    {
                        "channel": channel,
                        "title": channel.title or (
                            f"@{channel.username}" if channel.username else str(channel.channel_id)
                        ),
                        "username": channel.username,
                        "subscribers": int(channel.subscribers_count or 0),
                        "growth": int(period.get("members_total_growth", 0) or 0),
                        "growth_percent": float(period.get("members_growth_percent", 0.0) or 0.0),
                        "engagement_rate": float(period.get("engagement_rate", 0.0) or 0.0),
                        "er_classic": float(period.get("er_classic", 0.0) or 0.0),
                        "vtr": float(period.get("vtr", 0.0) or 0.0),
                        "avg_views_per_post": float(period.get("avg_views_per_post", 0.0) or 0.0),
                        "total_posts": int(period.get("total_posts", 0) or 0),
                    }
                )

            total_channels = len(rows)
            total_subscribers = sum(item["subscribers"] for item in rows)
            total_growth = sum(item["growth"] for item in rows)
            total_posts = sum(item["total_posts"] for item in rows)

            channels_with_er = [item for item in rows if item["engagement_rate"] > 0]
            avg_err = (
                sum(item["engagement_rate"] for item in channels_with_er) / len(channels_with_er)
                if channels_with_er else 0.0
            )
            channels_with_vtr = [item for item in rows if item["vtr"] > 0]
            avg_vtr = (
                sum(item["vtr"] for item in channels_with_vtr) / len(channels_with_vtr)
                if channels_with_vtr else 0.0
            )
            avg_views = (
                sum(item["avg_views_per_post"] for item in rows if item["avg_views_per_post"] > 0)
                / max(1, sum(1 for item in rows if item["avg_views_per_post"] > 0))
            )

            text = f"📊 <b>Сводка по {total_channels} каналам · 7 дней</b>\n\n"
            text += "👥 <b>Аудитория:</b>\n"
            text += f"   • Всего подписчиков: {total_subscribers:,}\n"
            text += f"   • Средне на канал: {total_subscribers // max(1, total_channels):,}\n"
            text += f"   • Прирост за 7 дн.: {total_growth:+,}\n\n"

            text += "📝 <b>Активность:</b>\n"
            text += f"   • Постов за период: {total_posts:,}\n"
            text += f"   • Средний охват поста: {avg_views:,.0f}\n\n"

            text += "🎯 <b>Вовлеченность (среднее по каналам):</b>\n"
            text += f"   • ERR: {avg_err:.2f}%\n"
            text += f"   • VTR / Reach Rate: {avg_vtr:.2f}%\n\n"

            top_subscribers = sorted(rows, key=lambda item: item["subscribers"], reverse=True)[:5]
            text += "🏆 <b>Топ по подписчикам:</b>\n"
            for index, item in enumerate(top_subscribers, 1):
                name = f"@{item['username']}" if item["username"] else item["title"][:24]
                text += f"   {index}. {name} — {item['subscribers']:,}\n"

            top_er = sorted(rows, key=lambda item: item["engagement_rate"], reverse=True)[:3]
            if any(item["engagement_rate"] > 0 for item in top_er):
                text += "\n💎 <b>Топ по ERR:</b>\n"
                for item in top_er:
                    if item["engagement_rate"] <= 0:
                        continue
                    name = f"@{item['username']}" if item["username"] else item["title"][:24]
                    text += f"   • {name} — {item['engagement_rate']:.2f}%\n"

            top_growth = sorted(rows, key=lambda item: item["growth"], reverse=True)[:3]
            text += "\n🚀 <b>Лидеры роста:</b>\n"
            for item in top_growth:
                name = f"@{item['username']}" if item["username"] else item["title"][:24]
                text += f"   • {name}: {item['growth']:+,} ({item['growth_percent']:+.2f}%)\n"

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📈 Графики роста", callback_data="growth_chart"),
                        InlineKeyboardButton(text="📊 Сводка-картинка", callback_data="summary_chart"),
                    ]
                ]
            )

            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Ошибка получения сводки: {e}")
            await message.answer(f"❌ Ошибка получения сводки: {str(e)}")

    async def send_summary_chart(self, message: Message) -> None:
        """Отправка сводного графика по всем каналам (тот же growth overview)."""
        await self.send_growth_chart(message)
    
    async def show_growth_stats(self, message: Message):
        """Показать статистику роста"""
        try:
            channels = await self.db.get_active_channels()
            if not channels:
                await message.answer("📈 Нет каналов в мониторинге", parse_mode="HTML")
                return

            analytics_rows = []
            for channel in channels:
                analytics = await self.db.get_channel_analytics(channel.channel_id, 7)
                if not analytics:
                    continue

                period = analytics.get('period', {})
                analytics_rows.append(
                    {
                        'title': channel.title or (f"@{channel.username}" if channel.username else str(channel.channel_id)),
                        'username': channel.username,
                        'growth': int(period.get('members_total_growth', 0)),
                        'growth_percent': float(period.get('members_growth_percent', 0.0)),
                        'engagement_rate': float(period.get('engagement_rate', 0.0)),
                        'avg_views_per_post': float(period.get('avg_views_per_post', 0.0)),
                    }
                )

            if not analytics_rows:
                await message.answer("📈 Недостаточно данных для анализа роста за 7 дней", parse_mode="HTML")
                return

            total_growth = sum(item['growth'] for item in analytics_rows)
            avg_growth_percent = sum(item['growth_percent'] for item in analytics_rows) / len(analytics_rows)
            avg_er = sum(item['engagement_rate'] for item in analytics_rows) / len(analytics_rows)

            top_growth = sorted(analytics_rows, key=lambda item: item['growth'], reverse=True)[:3]
            top_decline = sorted(analytics_rows, key=lambda item: item['growth'])[:3]

            text = "📈 <b>Рост каналов за 7 дней</b>\n\n"
            text += "🧮 <b>Общая динамика:</b>\n"
            text += f"   • Суммарный рост: {total_growth:+,}\n"
            text += f"   • Средний рост, %: {avg_growth_percent:+.2f}%\n"
            text += f"   • Средний ER: {avg_er:.2f}%\n\n"

            text += "🚀 <b>Лидеры роста:</b>\n"
            for row in top_growth:
                name = f"@{row['username']}" if row['username'] else row['title']
                text += f"   • {name}: {row['growth']:+,} ({row['growth_percent']:+.2f}%)\n"

            text += "\n⚠️ <b>Зоны риска:</b>\n"
            for row in top_decline:
                name = f"@{row['username']}" if row['username'] else row['title']
                text += f"   • {name}: {row['growth']:+,} ({row['growth_percent']:+.2f}%)\n"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📈 График роста", callback_data="growth_chart")],
            ])

            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

        except Exception as e:
            logger.error(f"Ошибка статистики роста: {e}")
            await message.answer(f"❌ Ошибка статистики роста: {str(e)}", parse_mode="HTML")
    
    async def show_public_channels_list(self, message: Message):
        """Публичный список каналов (для всех пользователей)"""
        try:
            channels = await self.db.get_active_channels()
            
            if not channels:
                await message.answer("📋 Пока нет каналов в мониторинге")
                return
            
            text = f"📋 <b>Отслеживаемые каналы ({len(channels)}):</b>\n\n"
            
            for i, channel in enumerate(channels[:10], 1):  # Показываем только 10
                username_display = f"@{channel.username}" if channel.username else "Канал"
                text += f"{i}. <b>{username_display}</b>\n"
                text += f"   👥 {channel.subscribers_count:,} подписчиков\n\n"
            
            if len(channels) > 10:
                text += f"... и еще {len(channels) - 10} каналов\n\n"
            
            text += "💡 Используйте /stats @channel для подробной статистики"
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка получения списка каналов: {e}")
            await message.answer(f"❌ Ошибка: {str(e)}")
    
    async def handle_channel_callback(self, callback: CallbackQuery):
        """Обработка callback запросов"""
        try:
            data = callback.data

            if data == "summary_all":
                await self.show_summary(callback.message)
            elif data == "summary_chart":
                await self.send_summary_chart(callback.message)
            elif data == "growth_all":
                await self.show_growth_stats(callback.message)
            elif data == "growth_chart":
                await self.send_growth_chart(callback.message)
            elif data == "refresh_list":
                await self.show_channels_list(callback.message)
            elif data.startswith("stats_"):
                parts = data.split("_")
                channel_id = int(parts[1])
                days = int(parts[2])
                await self.show_channel_stats(callback.message, str(channel_id), days)
            elif data.startswith("chart_"):
                parts = data.split("_")
                channel_id = int(parts[1])
                days = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 7
                await self.send_channel_chart(callback.message, str(channel_id), days)

            await callback.answer()

        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            await callback.answer("❌ Ошибка обработки запроса")
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===

    def _build_recommendations(
        self,
        period: Dict[str, Any],
        content_breakdown: Dict[str, Any],
        top_posts: List[Dict[str, Any]],
    ) -> List[str]:
        """Формирование контекстных рекомендаций по порогам."""
        tips: List[str] = []
        if not period:
            return tips

        er_classic = float(period.get("er_classic") or 0.0)
        err = float(period.get("err") or 0.0)
        vtr = float(period.get("vtr") or 0.0)
        growth_percent = float(period.get("members_growth_percent") or 0.0)
        avg_posts_per_day = float(period.get("avg_posts_per_day") or 0.0)
        total_posts = int(period.get("total_posts") or 0)

        if er_classic and er_classic < 1.0:
            tips.append("ER classic ниже 1% — пересмотреть форматы и СTA постов")
        elif er_classic and er_classic > 5.0:
            tips.append("Высокий ER classic — сохранить рубрики и регулярность")

        if vtr and vtr < 20.0:
            tips.append("Reach Rate < 20% — проверить уведомления и время выхода постов")

        if err and err < 1.5:
            tips.append("ERR ниже 1.5% — добавить опросы, реакции, обсуждения")

        if growth_percent < 0:
            tips.append("Подписчики уменьшаются — запустить контент-эксперимент или промо")
        elif 0 <= growth_percent < 1:
            tips.append("Рост подписчиков замедлен — усилить вирусные форматы и взаимные пиары")

        if total_posts == 0:
            tips.append("Нет постов в периоде — восстановить регулярный график публикаций")
        elif avg_posts_per_day < 0.5:
            tips.append("Меньше 1 поста за 2 дня — повысить частоту публикаций")
        elif avg_posts_per_day > 5:
            tips.append("Слишком много постов — риск выгорания аудитории, проверить дочитывания")

        if content_breakdown:
            best_type = max(
                content_breakdown.items(),
                key=lambda item: item[1].get("avg_views", 0),
            )
            type_name, type_stats = best_type
            if type_stats.get("avg_views", 0) > 0:
                tips.append(
                    f"Лучший тип контента — {type_name} "
                    f"(ср. {type_stats['avg_views']:,.0f} просмотров)"
                )

        if top_posts:
            top = top_posts[0]
            if top.get("engagement_rate", 0) > err and top.get("views", 0) > 0:
                tips.append("Повторить формат лидера по охвату — он опережает средний ER")

        return tips[:6]

    async def send_channel_chart(
        self,
        message: Message,
        channel_input: str,
        days: int = 7,
    ) -> None:
        """Отправка графика-дашборда канала картинкой."""
        try:
            channel_id = await self._resolve_channel_id(channel_input)
            if not channel_id:
                await message.answer("❌ Канал не найден")
                return

            analytics = await self.db.get_channel_analytics(channel_id, days)
            if not analytics:
                await message.answer("❌ Нет данных по этому каналу")
                return

            buffer = await asyncio.to_thread(render_channel_dashboard_png, analytics)
            if buffer is None:
                await message.answer("⚠️ Недостаточно данных для графика")
                return

            channel_info = analytics.get("channel", {})
            caption = (
                f"📊 Дашборд «{channel_info.get('title') or channel_id}» за {days} дн."
            )
            file = BufferedInputFile(buffer.getvalue(), filename=f"channel_{channel_id}_{days}d.png")
            await message.answer_photo(photo=file, caption=caption)

        except Exception as e:
            logger.error(f"Ошибка построения графика: {e}")
            await message.answer(f"❌ Ошибка построения графика: {str(e)}")

    async def send_growth_chart(self, message: Message) -> None:
        """Отправка сравнительного графика роста по всем каналам."""
        try:
            channels = await self.db.get_active_channels()
            if not channels:
                await message.answer("📋 Нет каналов в мониторинге")
                return

            rows: List[Dict[str, Any]] = []
            for channel in channels:
                analytics = await self.db.get_channel_analytics(channel.channel_id, 7)
                if not analytics:
                    continue
                period = analytics.get("period", {})
                rows.append(
                    {
                        "title": channel.title or str(channel.channel_id),
                        "username": channel.username,
                        "growth": int(period.get("members_total_growth", 0) or 0),
                        "growth_percent": float(period.get("members_growth_percent", 0.0) or 0.0),
                        "engagement_rate": float(period.get("engagement_rate", 0.0) or 0.0),
                    }
                )

            if not rows:
                await message.answer("⚠️ Недостаточно данных для сравнительного графика")
                return

            buffer = await asyncio.to_thread(render_growth_overview_png, rows)
            if buffer is None:
                await message.answer("⚠️ Не удалось построить график")
                return

            file = BufferedInputFile(buffer.getvalue(), filename="growth_overview_7d.png")
            await message.answer_photo(photo=file, caption="📈 Рост и вовлеченность каналов за 7 дн.")

        except Exception as e:
            logger.error(f"Ошибка построения графика роста: {e}")
            await message.answer(f"❌ Ошибка графика роста: {str(e)}")

    async def _resolve_channel_id(self, channel_input: str) -> Optional[int]:
        """Разбор username/id канала в channel_id."""
        if channel_input.startswith("@"):
            return await self.get_channel_id_by_username(channel_input[1:])
        if channel_input.lstrip("-").isdigit():
            return int(channel_input)
        return await self.get_channel_id_by_username(channel_input)

    async def get_channel_id_by_username(self, username: str) -> Optional[int]:
        """Получение ID канала по username из БД."""
        channel = await self.db.get_channel_by_username(username)
        return channel.channel_id if channel else None
    
    async def get_username_by_channel_id(self, channel_id: int) -> Optional[str]:
        """Получение username по ID канала из БД."""
        channel = await self.db.get_channel(channel_id)
        return channel.username if channel else None
    
    async def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """Получение информации о канале из БД."""
        channel = await self.db.get_channel(channel_id)
        if not channel:
            return {
                'title': f'Канал {channel_id}',
                'description': 'Описание недоступно',
                'members_count': 0
            }

        return {
            'title': channel.title or f'Канал {channel_id}',
            'description': channel.description or 'Описание недоступно',
            'members_count': channel.subscribers_count
        }
