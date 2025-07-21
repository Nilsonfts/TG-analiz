"""
Расширенные команды бота для Channel Analytics
Полная реализация аналитических функций
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from ..db.database_service import DatabaseService
from ..config import settings

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
            if members_history:
                first_day = members_history[0]
                last_day = members_history[-1]
                growth = last_day['count'] - first_day['count']
                growth_percent = (growth / first_day['count'] * 100) if first_day['count'] > 0 else 0
                
                text += f"📈 <b>Рост подписчиков:</b>\n"
                text += f"   • За период: {growth:+,} ({growth_percent:+.1f}%)\n"
                text += f"   • В день: {growth / days:+.1f} в среднем\n\n"
            
            # Просмотры
            if views_history:
                avg_views = sum(v['avg_views'] for v in views_history) / len(views_history)
                total_posts = sum(v['posts_count'] for v in views_history)
                
                text += f"👁 <b>Просмотры:</b>\n"
                text += f"   • Среднее за пост: {avg_views:,.0f}\n"
                text += f"   • Постов за период: {total_posts}\n\n"
            
            # Последние посты
            recent_posts = analytics['recent_posts'][:3]
            if recent_posts:
                text += f"📝 <b>Последние посты:</b>\n"
                for post in recent_posts:
                    post_text = post['text'][:50] + '...' if post['text'] and len(post['text']) > 50 else (post['text'] or 'Без текста')
                    text += f"   • {post_text}\n"
                    text += f"     👁 {post['views']:,} | 🔄 {post['forwards']:,}\n"
            
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
        """Показать общую сводку по всем каналам"""
        try:
            channels = await self.db.get_active_channels()
            
            if not channels:
                await message.answer("📊 Нет каналов в мониторинге")
                return
            
            text = f"📊 <b>Сводка по {len(channels)} каналам</b>\n\n"
            
            total_subscribers = sum(ch.subscribers_count for ch in channels)
            total_posts = sum(ch.posts_count for ch in channels)
            
            text += f"👥 <b>Общие показатели:</b>\n"
            text += f"   • Подписчики: {total_subscribers:,}\n"
            text += f"   • Посты: {total_posts:,}\n"
            text += f"   • Среднее на канал: {total_subscribers // len(channels):,}\n\n"
            
            # Топ каналов по подписчикам
            top_channels = sorted(channels, key=lambda x: x.subscribers_count, reverse=True)[:5]
            text += f"🏆 <b>Топ каналов по подписчикам:</b>\n"
            for i, ch in enumerate(top_channels, 1):
                username_display = f"@{ch.username}" if ch.username else ch.title[:20]
                text += f"   {i}. {username_display} - {ch.subscribers_count:,}\n"
            
            await message.answer(text, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"Ошибка получения сводки: {e}")
            await message.answer(f"❌ Ошибка получения сводки: {str(e)}")
    
    async def show_growth_stats(self, message: Message):
        """Показать статистику роста"""
        await message.answer(
            "📈 <b>Статистика роста</b>\n\n"
            "🚧 Функция в разработке\n"
            "Скоро будет доступен подробный анализ роста всех каналов",
            parse_mode="HTML"
        )
    
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
            elif data == "growth_all":
                await self.show_growth_stats(callback.message)
            elif data == "refresh_list":
                await self.show_channels_list(callback.message)
            elif data.startswith("stats_"):
                parts = data.split("_")
                channel_id = int(parts[1])
                days = int(parts[2])
                # Здесь нужно получить username по channel_id
                await self.show_channel_stats(callback.message, str(channel_id), days)
            
            await callback.answer()
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            await callback.answer("❌ Ошибка обработки запроса")
    
    # === ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ===
    
    async def get_channel_id_by_username(self, username: str) -> Optional[int]:
        """Получение ID канала по username (заглушка)"""
        # TODO: Реализовать через Telethon API
        return None
    
    async def get_username_by_channel_id(self, channel_id: int) -> Optional[str]:
        """Получение username по ID канала (заглушка)"""
        # TODO: Реализовать через Telethon API
        return None
    
    async def get_channel_info(self, channel_id: int) -> Dict[str, Any]:
        """Получение информации о канале (заглушка)"""
        # TODO: Реализовать через Telethon API
        return {
            'title': f'Канал {channel_id}',
            'description': 'Описание недоступно',
            'members_count': 0
        }
