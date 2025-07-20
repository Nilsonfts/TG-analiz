"""
Enhanced bot handlers for Channel Analytics with new functionality.
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile

from src.config import settings
from src.db.models import DatabaseManager, Channel
from src.collectors import CompositeCollector
from src.collectors.telegram_collector import TelegramCollector
from src.collectors.external_collectors import TelemetrCollector, TGStatCollector
from src.reports import ReportGenerator
from src.reports.export_service import DataExportService
from src.scheduler import SchedulerService
from src.utils.logging import get_bot_logger

logger = get_bot_logger()

# Initialize services
db_manager: Optional[DatabaseManager] = None
collector: Optional[CompositeCollector] = None
report_generator: Optional[ReportGenerator] = None
export_service: Optional[DataExportService] = None
scheduler_service: Optional[SchedulerService] = None

# Router for handlers
router = Router()


def check_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in settings.admin_user_ids


def init_services(db_manager_instance: DatabaseManager):
    """Initialize all services."""
    global db_manager, collector, report_generator, export_service, scheduler_service
    
    db_manager = db_manager_instance
    
    # Initialize collectors
    collectors = [TelegramCollector()]
    if settings.telemetr_api_key:
        collectors.append(TelemetrCollector())
    if settings.tgstat_api_key:
        collectors.append(TGStatCollector())
    
    collector = CompositeCollector(collectors)
    report_generator = ReportGenerator()
    export_service = DataExportService()
    scheduler_service = SchedulerService(db_manager)


@router.message(CommandStart())
async def start_command(message: Message):
    """Enhanced /start command."""
    logger.info("Start command received", user_id=message.from_user.id)
    
    # Check system status
    db_status = "✅" if db_manager else "❌"
    collector_status = "✅" if collector and await collector.health_check() else "❌"
    scheduler_status = "✅" if scheduler_service else "❌"
    
    # Count active channels
    try:
        async with db_manager.async_session() as session:
            from sqlalchemy import select, func
            result = await session.execute(
                select(func.count(Channel.id)).where(Channel.is_active == True)
            )
            active_channels = result.scalar() or 0
    except Exception:
        active_channels = 0
    
    welcome_text = (
        "🚀 <b>Channel Analytics Bot v2.0</b>\n\n"
        "Профессиональная система аналитики Telegram-каналов\n\n"
        f"📊 <b>Статус системы:</b>\n"
        f"• База данных: {db_status}\n"
        f"• Сборщики данных: {collector_status}\n"
        f"• Планировщик: {scheduler_status}\n"
        f"• Активных каналов: {active_channels}\n\n"
        f"🔧 <b>Доступные команды:</b>\n"
        f"• /add @channel - добавить канал\n"
        f"• /remove @channel - удалить канал\n"
        f"• /list_channels - список каналов\n"
        f"• /stats [today|week|month] - отчеты\n"
        f"• /export [week|month] - экспорт данных\n"
        f"• /health - состояние системы\n"
        f"• /help - подробная справка\n\n"
    )
    
    if check_admin(message.from_user.id):
        welcome_text += "👑 <i>У вас есть права администратора</i>"
    else:
        welcome_text += "ℹ️ <i>Для управления нужны права администратора</i>"
    
    await message.answer(welcome_text, parse_mode="HTML")


@router.message(Command("add"))
async def add_channel_command(message: Message):
    """Add channel to monitoring."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    logger.info("Add channel command", user_id=message.from_user.id)
    
    # Parse channel from command
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer(
            "❌ Укажите канал для добавления\n\n"
            "Примеры:\n"
            "• /add @channel_username\n"
            "• /add https://t.me/channel_username\n"
            "• /add -1001234567890"
        )
        return
    
    channel_input = args[0]
    
    # Parse channel ID/username
    channel_id = None
    username = None
    
    try:
        if channel_input.startswith('@'):
            username = channel_input[1:]
        elif channel_input.startswith('https://t.me/'):
            username = channel_input.replace('https://t.me/', '')
        elif channel_input.lstrip('-').isdigit():
            channel_id = int(channel_input)
        else:
            username = channel_input
        
        # Try to get channel info
        if username:
            # Convert username to ID using collector
            stats = await collector.collect_channel_stats(f"@{username}")
            if stats:
                channel_id = stats.channel_id
            else:
                await message.answer(f"❌ Канал @{username} не найден или недоступен")
                return
        
        if not channel_id:
            await message.answer("❌ Не удалось определить ID канала")
            return
        
        # Get channel stats
        stats = await collector.collect_channel_stats(channel_id)
        if not stats:
            await message.answer(f"❌ Не удалось получить данные канала {channel_id}")
            return
        
        # Add to database
        async with db_manager.async_session() as session:
            from sqlalchemy import select
            
            # Check if already exists
            existing = await session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            )
            existing_channel = existing.scalar_one_or_none()
            
            if existing_channel:
                if existing_channel.is_active:
                    await message.answer(f"ℹ️ Канал уже добавлен: {existing_channel.title}")
                    return
                else:
                    # Reactivate
                    existing_channel.is_active = True
                    existing_channel.title = stats.title
                    existing_channel.username = stats.username
                    existing_channel.description = stats.description
                    await session.commit()
                    
                    await message.answer(
                        f"✅ Канал реактивирован\n\n"
                        f"📺 <b>{stats.title}</b>\n"
                        f"🔗 @{stats.username or 'private'}\n"
                        f"👥 {stats.members_count:,} подписчиков"
                    )
                    return
            
            # Create new channel
            new_channel = Channel(
                channel_id=channel_id,
                username=stats.username,
                title=stats.title,
                description=stats.description,
                is_active=True,
                added_by_user_id=message.from_user.id
            )
            session.add(new_channel)
            await session.commit()
            
            await message.answer(
                f"✅ Канал добавлен в мониторинг\n\n"
                f"📺 <b>{stats.title}</b>\n"
                f"🔗 @{stats.username or 'private'}\n"
                f"👥 {stats.members_count:,} подписчиков\n\n"
                f"ℹ️ Сбор данных начнется автоматически"
            )
            
            logger.info("Channel added", channel_id=channel_id, title=stats.title)
    
    except Exception as e:
        logger.error("Failed to add channel", error=str(e), channel_input=channel_input)
        await message.answer(f"❌ Ошибка при добавлении канала: {str(e)}")


@router.message(Command("remove"))
async def remove_channel_command(message: Message):
    """Remove channel from monitoring."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    if not args:
        await message.answer("❌ Укажите канал для удаления\n\nПример: /remove @channel_username")
        return
    
    channel_input = args[0]
    
    try:
        async with db_manager.async_session() as session:
            from sqlalchemy import select
            
            # Find channel
            if channel_input.startswith('@'):
                username = channel_input[1:]
                result = await session.execute(
                    select(Channel).where(
                        Channel.username == username,
                        Channel.is_active == True
                    )
                )
            elif channel_input.lstrip('-').isdigit():
                channel_id = int(channel_input)
                result = await session.execute(
                    select(Channel).where(
                        Channel.channel_id == channel_id,
                        Channel.is_active == True
                    )
                )
            else:
                await message.answer("❌ Неверный формат канала")
                return
            
            channel = result.scalar_one_or_none()
            if not channel:
                await message.answer("❌ Канал не найден в мониторинге")
                return
            
            # Deactivate channel
            channel.is_active = False
            await session.commit()
            
            await message.answer(
                f"✅ Канал удален из мониторинга\n\n"
                f"📺 <b>{channel.title}</b>\n"
                f"🔗 @{channel.username or 'private'}\n\n"
                f"ℹ️ Исторические данные сохранены"
            )
            
            logger.info("Channel removed", channel_id=channel.channel_id)
    
    except Exception as e:
        logger.error("Failed to remove channel", error=str(e))
        await message.answer(f"❌ Ошибка при удалении канала: {str(e)}")


@router.message(Command("list_channels"))
async def list_channels_command(message: Message):
    """List all monitored channels."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    try:
        async with db_manager.async_session() as session:
            from sqlalchemy import select, desc
            
            result = await session.execute(
                select(Channel).where(Channel.is_active == True).order_by(desc(Channel.added_at))
            )
            channels = result.scalars().all()
            
            if not channels:
                await message.answer("📭 Нет каналов в мониторинге\n\nДобавьте канал командой /add @channel")
                return
            
            text = f"📊 <b>Каналы в мониторинге ({len(channels)})</b>\n\n"
            
            for i, channel in enumerate(channels[:20], 1):  # Limit to 20
                text += (
                    f"{i}. <b>{channel.title}</b>\n"
                    f"   🔗 @{channel.username or 'private'}\n"
                    f"   🆔 <code>{channel.channel_id}</code>\n"
                    f"   📅 Добавлен: {channel.added_at.strftime('%d.%m.%Y')}\n\n"
                )
            
            if len(channels) > 20:
                text += f"... и еще {len(channels) - 20} каналов"
            
            # Add action buttons
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats_all"),
                        InlineKeyboardButton(text="📈 Сводный отчет", callback_data="report_summary")
                    ]
                ]
            )
            
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    
    except Exception as e:
        logger.error("Failed to list channels", error=str(e))
        await message.answer(f"❌ Ошибка при получении списка каналов: {str(e)}")


@router.message(Command("stats"))
async def stats_command(message: Message):
    """Generate statistics reports."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else ["today"]
    period = args[0] if args[0] in ["today", "week", "month"] else "today"
    
    status_msg = await message.answer("🔄 Генерирую отчет...")
    
    try:
        async with db_manager.async_session() as session:
            if period == "today":
                report = await report_generator.generate_daily_report(session)
            elif period == "week":
                report = await report_generator.generate_weekly_report(session)
            elif period == "month":
                report = await report_generator.generate_monthly_report(session)
            
            if not report:
                await status_msg.edit_text("❌ Не удалось сгенерировать отчет")
                return
            
            # Send markdown report
            await status_msg.edit_text(
                f"📊 Отчет за {period}\n\n" + report["markdown"][:4000],  # Telegram limit
                parse_mode="HTML"
            )
            
            # Send charts if available
            if "charts" in report and report["charts"]:
                for chart_path in report["charts"]:
                    try:
                        chart_file = FSInputFile(chart_path)
                        await message.answer_photo(chart_file)
                    except Exception as e:
                        logger.error("Failed to send chart", error=str(e), chart=chart_path)
    
    except Exception as e:
        logger.error("Failed to generate stats", error=str(e), period=period)
        await status_msg.edit_text(f"❌ Ошибка при генерации отчета: {str(e)}")


@router.message(Command("export"))
async def export_command(message: Message):
    """Export data to CSV."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else ["month"]
    export_type = args[0] if args[0] in ["week", "month", "quarter", "year", "all"] else "month"
    
    status_msg = await message.answer("🔄 Экспортирую данные...")
    
    try:
        async with db_manager.async_session() as session:
            # Get all active channels
            from sqlalchemy import select
            result = await session.execute(
                select(Channel.channel_id).where(Channel.is_active == True)
            )
            channel_ids = [row[0] for row in result.fetchall()]
            
            if not channel_ids:
                await status_msg.edit_text("❌ Нет активных каналов для экспорта")
                return
            
            # Export data
            export_path = await export_service.export_multiple_channels(
                session, channel_ids, export_type, "csv"
            )
            
            if not export_path:
                await status_msg.edit_text("❌ Ошибка при экспорте данных")
                return
            
            # Send file
            export_file = FSInputFile(export_path)
            await message.answer_document(
                export_file,
                caption=f"📊 Экспорт данных за {export_type}\n"
                       f"Каналов: {len(channel_ids)}\n"
                       f"Сгенерирован: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}"
            )
            
            await status_msg.delete()
    
    except Exception as e:
        logger.error("Failed to export data", error=str(e), export_type=export_type)
        await status_msg.edit_text(f"❌ Ошибка при экспорте: {str(e)}")


@router.message(Command("health"))
async def health_command(message: Message):
    """Check system health."""
    if not check_admin(message.from_user.id):
        await message.answer("❌ Недостаточно прав доступа")
        return
    
    try:
        # Check database
        db_status = "❌"
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import select
                await session.execute(select(1))
                db_status = "✅"
        except Exception:
            pass
        
        # Check collector
        collector_status = "✅" if collector and await collector.health_check() else "❌"
        
        # Check scheduler
        scheduler_status = "✅" if scheduler_service and scheduler_service._running else "❌"
        
        # Get scheduler jobs info
        jobs_info = ""
        if scheduler_service:
            job_status = scheduler_service.get_job_status()
            if job_status["status"] == "running":
                jobs_info = f"\n\n🕒 <b>Запланированные задачи:</b>\n"
                for job in job_status.get("jobs", []):
                    next_run = job.get("next_run")
                    if next_run:
                        next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                        time_str = next_run_dt.strftime('%d.%m %H:%M')
                    else:
                        time_str = "Не запланировано"
                    jobs_info += f"• {job['name']}: {time_str}\n"
        
        # Count channels and data
        channels_count = 0
        data_points = 0
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import select, func
                
                # Count channels
                result = await session.execute(
                    select(func.count(Channel.id)).where(Channel.is_active == True)
                )
                channels_count = result.scalar() or 0
                
                # Count data points (last 7 days)
                from src.db.models import MembersDaily
                week_ago = datetime.utcnow().date() - timedelta(days=7)
                result = await session.execute(
                    select(func.count(MembersDaily.id)).where(MembersDaily.date >= week_ago)
                )
                data_points = result.scalar() or 0
        except Exception:
            pass
        
        health_text = (
            f"🏥 <b>Состояние системы</b>\n\n"
            f"🗄️ База данных: {db_status}\n"
            f"📡 Сборщики данных: {collector_status}\n"
            f"⏰ Планировщик: {scheduler_status}\n\n"
            f"📊 <b>Статистика:</b>\n"
            f"• Активных каналов: {channels_count}\n"
            f"• Точек данных (7 дней): {data_points}\n"
            f"• Время работы: {datetime.utcnow().strftime('%d.%m.%Y %H:%M UTC')}"
            f"{jobs_info}"
        )
        
        # Add action buttons
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Обновить", callback_data="health_refresh"),
                    InlineKeyboardButton(text="🔧 Диагностика", callback_data="health_detailed")
                ]
            ]
        )
        
        await message.answer(health_text, parse_mode="HTML", reply_markup=keyboard)
    
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        await message.answer(f"❌ Ошибка при проверке состояния: {str(e)}")


@router.message(Command("help"))
async def help_command(message: Message):
    """Enhanced help command."""
    help_text = (
        "📚 <b>Справка по Channel Analytics Bot</b>\n\n"
        
        "🔧 <b>Управление каналами:</b>\n"
        "• /add @channel - добавить канал в мониторинг\n"
        "• /remove @channel - удалить канал\n"
        "• /list_channels - список отслеживаемых каналов\n\n"
        
        "📊 <b>Отчеты и статистика:</b>\n"
        "• /stats today - ежедневный отчет\n"
        "• /stats week - недельный отчет с графиками\n"
        "• /stats month - месячный отчет\n\n"
        
        "📁 <b>Экспорт данных:</b>\n"
        "• /export week - экспорт за неделю\n"
        "• /export month - экспорт за месяц\n"
        "• /export quarter - экспорт за квартал\n"
        "• /export year - экспорт за год\n\n"
        
        "⚙️ <b>Система:</b>\n"
        "• /health - состояние системы\n"
        "• /help - эта справка\n\n"
        
        "📈 <b>Автоматические отчеты:</b>\n"
        f"• Ежедневный сбор: {settings.daily_job_hour:02d}:00 UTC\n"
        f"• Недельные отчеты: Пн {settings.weekly_job_hour:02d}:00 UTC\n"
        f"• Месячные отчеты: 1 число {settings.monthly_job_hour:02d}:00 UTC\n\n"
        
        "🔔 <b>Уведомления:</b>\n"
        "• Автоматические отчеты в чат\n"
        "• Алерты при падении метрик\n"
        "• Критические ошибки системы\n\n"
        
        "💡 <b>Поддерживаемые источники данных:</b>\n"
        "• Telegram Bot API\n"
        "• Telethon (расширенные данные)\n"
    )
    
    if settings.telemetr_api_key:
        help_text += "• Telemetr.me API ✅\n"
    else:
        help_text += "• Telemetr.me API ❌\n"
    
    if settings.tgstat_api_key:
        help_text += "• TGStat.ru API ✅\n"
    else:
        help_text += "• TGStat.ru API ❌\n"
    
    help_text += (
        f"\n📧 <b>Администраторы:</b> {len(settings.admin_user_ids)} пользователей\n"
        f"🗂️ <b>База данных:</b> PostgreSQL\n"
        f"☁️ <b>Платформа:</b> Railway\n\n"
        f"<i>Версия: 2.0.0 | {datetime.utcnow().strftime('%Y-%m-%d')}</i>"
    )
    
    await message.answer(help_text, parse_mode="HTML")


# Callback query handlers
@router.callback_query(F.data == "health_refresh")
async def health_refresh_callback(callback: CallbackQuery):
    """Refresh health status."""
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав доступа")
        return
    
    await callback.answer("🔄 Обновляю состояние...")
    # Trigger health command logic
    await health_command(callback.message)


@router.callback_query(F.data == "health_detailed")
async def health_detailed_callback(callback: CallbackQuery):
    """Show detailed health information."""
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав доступа")
        return
    
    try:
        detailed_info = "🔍 <b>Детальная диагностика</b>\n\n"
        
        # Database details
        try:
            async with db_manager.async_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT version()"))
                db_version = result.scalar()
                detailed_info += f"🗄️ <b>База данных:</b>\n"
                detailed_info += f"• Версия: PostgreSQL\n"
                detailed_info += f"• Соединение: активно\n\n"
        except Exception as e:
            detailed_info += f"🗄️ <b>База данных:</b>\n• Ошибка: {str(e)}\n\n"
        
        # Collector details
        if collector:
            for i, c in enumerate(collector.collectors):
                health = await c.health_check()
                detailed_info += f"📡 <b>Сборщик {i+1}:</b> {c.__class__.__name__}\n"
                detailed_info += f"• Статус: {'✅' if health else '❌'}\n"
        
        await callback.message.answer(detailed_info, parse_mode="HTML")
        await callback.answer()
    
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "stats_all")
async def stats_all_callback(callback: CallbackQuery):
    """Show statistics for all channels."""
    if not check_admin(callback.from_user.id):
        await callback.answer("❌ Недостаточно прав доступа")
        return
    
    await callback.answer("📊 Генерирую статистику...")
    # Trigger stats command with today period
    message_copy = callback.message
    message_copy.text = "/stats today"
    await stats_command(message_copy)
