import os
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes


def get_admin_users() -> list[int]:
    """Получение списка ID администраторов"""
    admin_users_str = os.getenv("ADMIN_USERS", "")
    if not admin_users_str:
        return []

    try:
        return [
            int(user_id.strip())
            for user_id in admin_users_str.split(",")
            if user_id.strip()
        ]
    except ValueError:
        return []


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    admin_users = get_admin_users()
    return user_id in admin_users


def admin_required(func):
    """Декоратор для проверки прав администратора"""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        if not is_admin(user_id):
            await update.message.reply_text(
                "❌ У вас нет прав для выполнения этой команды.\n"
                "Только администраторы могут использовать эту функцию."
            )
            return

        return await func(update, context)

    return wrapper


async def check_user_permissions(update: Update) -> bool:
    """Проверка прав пользователя"""
    user_id = update.effective_user.id
    return is_admin(user_id)
