import logging
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from database.models import User, get_db
from services.report_service import ReportService
from services.scheduler_service import SchedulerService
from utils.auth import admin_required, is_admin

logger = logging.getLogger(__name__)

# Инициализация сервисов
report_service = ReportService()
scheduler_service = SchedulerService()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user

    # Сохранение пользователя в базу данных
    db = get_db()
    try:
        db_user = db.query(User).filter(User.user_id == user.id).first()
        if not db_user:
            db_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                is_admin=is_admin(user.id),
            )
            db.add(db_user)
            db.commit()
    except Exception as e:
        logger.error(f"Ошибка при сохранении пользователя: {e}")
        db.rollback()
    finally:
        db.close()

    welcome_text = f"""
🤖 <b>Добро пожаловать в Telegram Analytics Bot!</b>

Привет, {user.first_name}! Я помогу вам получать подробную аналитику по Telegram-группам.

<b>📊 Доступные отчеты:</b>
• Ежедневные отчеты
• Еженедельные отчеты
• Ежемесячные отчеты

<b>🔧 Основные команды:</b>
/daily - Ежедневный отчёт
/weekly - Еженедельный отчёт
/monthly - Ежемесячный отчёт
/summary - Отчёт за конкретную дату
/subscribe - Подписка на автоматические отчёты
/unsubscribe - Отмена подписки
/help - Справка по всем командам

<b>⚡ Что я умею:</b>
📈 Анализ роста подписчиков
👁️ Статистика просмотров постов
❤️ Аналитика реакций и комментариев
📱 Анализ типов контента
📊 Создание графиков и диаграмм

Для начала работы используйте команды выше!
    """

    if is_admin(user.id):
        welcome_text += "\n🔑 <b>Вы авторизованы как администратор</b>"

    await update.message.reply_text(welcome_text, parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    help_text = """
📖 <b>Справка по командам</b>

<b>🔸 Основные команды:</b>
/start - Запуск бота и регистрация
/help - Показать эту справку

<b>🔸 Отчеты:</b>
/daily - Получить ежедневный отчёт (за последние 24 часа)
/weekly - Получить еженедельный отчёт (за последние 7 дней)
/monthly - Получить ежемесячный отчёт (за последние 30 дней)
/summary ГГГГ-ММ-ДД - Отчёт за конкретную дату

<i>Пример:</i> /summary 2024-01-15

<b>🔸 Подписки:</b>
/subscribe [тип] - Подписка на автоматические отчёты
    • daily - ежедневные отчёты (в 09:00)
    • weekly - еженедельные отчёты (понедельник в 09:00)
    • monthly - ежемесячные отчёты (1 число в 09:00)

/unsubscribe [тип] - Отмена подписки

<i>Примеры:</i>
/subscribe daily
/subscribe weekly
/unsubscribe monthly

<b>📊 Содержание отчетов:</b>
• Количество подписчиков и их изменение
• Статистика просмотров постов
• Анализ реакций и комментариев
• Популярность типов контента
• Графики динамики показателей
• Рекомендации по улучшению

<b>⏰ Расписание автоматических отчетов:</b>
• Ежедневные: каждый день в 09:00
• Еженедельные: каждый понедельник в 09:00
• Ежемесячные: 1 число каждого месяца в 09:00

<i>❓ Если у вас есть вопросы, обратитесь к администратору.</i>
    """

    await update.message.reply_text(help_text, parse_mode="HTML")


@admin_required
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /daily"""
    try:
        await update.message.reply_text("📊 Генерирую ежедневный отчёт...")

        report = await report_service.generate_daily_report()

        await update.message.reply_text(report["text"], parse_mode="HTML")

        if report.get("chart"):
            await update.message.reply_photo(
                photo=report["chart"], caption="📈 Графики ежедневной аналитики"
            )

    except Exception as e:
        logger.error(f"Ошибка при генерации ежедневного отчёта: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации отчёта. Попробуйте позже."
        )


@admin_required
async def weekly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /weekly"""
    try:
        await update.message.reply_text("📊 Генерирую еженедельный отчёт...")

        report = await report_service.generate_weekly_report()

        await update.message.reply_text(report["text"], parse_mode="HTML")

        if report.get("chart"):
            await update.message.reply_photo(
                photo=report["chart"], caption="📈 Графики еженедельной аналитики"
            )

    except Exception as e:
        logger.error(f"Ошибка при генерации еженедельного отчёта: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации отчёта. Попробуйте позже."
        )


@admin_required
async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /monthly"""
    try:
        await update.message.reply_text("📊 Генерирую ежемесячный отчёт...")

        report = await report_service.generate_monthly_report()

        await update.message.reply_text(report["text"], parse_mode="HTML")

        if report.get("chart"):
            await update.message.reply_photo(
                photo=report["chart"], caption="📈 Графики ежемесячной аналитики"
            )

    except Exception as e:
        logger.error(f"Ошибка при генерации ежемесячного отчёта: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации отчёта. Попробуйте позже."
        )


@admin_required
async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /summary"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите дату в формате ГГГГ-ММ-ДД\n" "Пример: /summary 2024-01-15"
        )
        return

    try:
        date_str = context.args[0]
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        await update.message.reply_text(f"📊 Генерирую отчёт за {date_str}...")

        report = await report_service.generate_summary_report(target_date)

        await update.message.reply_text(report["text"], parse_mode="HTML")

        if report.get("chart"):
            await update.message.reply_photo(
                photo=report["chart"], caption=f"📈 Аналитика за {date_str}"
            )

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД\n"
            "Пример: /summary 2024-01-15"
        )
    except Exception as e:
        logger.error(f"Ошибка при генерации отчёта за дату: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при генерации отчёта. Попробуйте позже."
        )


@admin_required
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /subscribe"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите тип подписки: daily, weekly или monthly\n"
            "Пример: /subscribe daily"
        )
        return

    subscription_type = context.args[0].lower()
    if subscription_type not in ["daily", "weekly", "monthly"]:
        await update.message.reply_text(
            "❌ Неверный тип подписки. Доступны: daily, weekly, monthly"
        )
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    try:
        success = await scheduler_service.add_subscription(
            user_id, subscription_type, chat_id
        )

        if success:
            schedule_info = {
                "daily": "ежедневно в 09:00",
                "weekly": "каждый понедельник в 09:00",
                "monthly": "1 число каждого месяца в 09:00",
            }

            await update.message.reply_text(
                f"✅ Подписка на {subscription_type} отчёты активирована!\n"
                f"📅 Отчёты будут приходить {schedule_info[subscription_type]}"
            )
        else:
            await update.message.reply_text(
                "❌ Подписка уже существует или произошла ошибка"
            )

    except Exception as e:
        logger.error(f"Ошибка при оформлении подписки: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при оформлении подписки. Попробуйте позже."
        )


@admin_required
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /unsubscribe"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите тип подписки: daily, weekly или monthly\n"
            "Пример: /unsubscribe daily"
        )
        return

    subscription_type = context.args[0].lower()
    if subscription_type not in ["daily", "weekly", "monthly"]:
        await update.message.reply_text(
            "❌ Неверный тип подписки. Доступны: daily, weekly, monthly"
        )
        return

    user_id = update.effective_user.id

    try:
        success = await scheduler_service.remove_subscription(
            user_id, subscription_type
        )

        if success:
            await update.message.reply_text(
                f"✅ Подписка на {subscription_type} отчёты отменена!"
            )
        else:
            await update.message.reply_text("❌ Подписка не найдена или уже отменена")

    except Exception as e:
        logger.error(f"Ошибка при отмене подписки: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при отмене подписки. Попробуйте позже."
        )
