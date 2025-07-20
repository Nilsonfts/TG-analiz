import logging
from datetime import datetime

from database.models import User, UserSubscription, get_db

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для управления подписками и расписанием отчетов"""

    async def add_subscription(
        self, user_id: int, subscription_type: str, chat_id: int
    ) -> bool:
        """Добавление подписки пользователя"""
        db = get_db()
        try:
            # Поиск пользователя
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                # Создание нового пользователя
                user = User(user_id=user_id, is_admin=False)
                db.add(user)
                db.flush()

            # Проверка существующей подписки
            existing_subscription = (
                db.query(UserSubscription)
                .filter(
                    UserSubscription.user_id == user.id,
                    UserSubscription.subscription_type == subscription_type,
                    UserSubscription.is_active == True,
                )
                .first()
            )

            if existing_subscription:
                # Обновление существующей подписки
                existing_subscription.chat_id = chat_id
                existing_subscription.updated_at = datetime.utcnow()
                logger.info(
                    f"Обновлена подписка пользователя {user_id} на {subscription_type}"
                )
            else:
                # Создание новой подписки
                subscription = UserSubscription(
                    user_id=user.id,
                    subscription_type=subscription_type,
                    chat_id=chat_id,
                    is_active=True,
                )
                db.add(subscription)
                logger.info(
                    f"Создана подписка пользователя {user_id} на {subscription_type}"
                )

            db.commit()
            return True

        except Exception as e:
            logger.error(f"Ошибка при добавлении подписки: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    async def remove_subscription(self, user_id: int, subscription_type: str) -> bool:
        """Удаление подписки пользователя"""
        db = get_db()
        try:
            # Поиск пользователя
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return False

            # Поиск подписки
            subscription = (
                db.query(UserSubscription)
                .filter(
                    UserSubscription.user_id == user.id,
                    UserSubscription.subscription_type == subscription_type,
                    UserSubscription.is_active == True,
                )
                .first()
            )

            if subscription:
                subscription.is_active = False
                subscription.updated_at = datetime.utcnow()
                db.commit()
                logger.info(
                    f"Отменена подписка пользователя {user_id} на {subscription_type}"
                )
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Ошибка при удалении подписки: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    async def get_daily_subscribers(self) -> list[dict]:
        """Получение списка подписчиков на ежедневные отчеты"""
        return await self._get_subscribers_by_type("daily")

    async def get_weekly_subscribers(self) -> list[dict]:
        """Получение списка подписчиков на еженедельные отчеты"""
        return await self._get_subscribers_by_type("weekly")

    async def get_monthly_subscribers(self) -> list[dict]:
        """Получение списка подписчиков на ежемесячные отчеты"""
        return await self._get_subscribers_by_type("monthly")

    async def _get_subscribers_by_type(self, subscription_type: str) -> list[dict]:
        """Получение подписчиков по типу подписки"""
        db = get_db()
        try:
            subscriptions = (
                db.query(UserSubscription)
                .join(User)
                .filter(
                    UserSubscription.subscription_type == subscription_type,
                    UserSubscription.is_active == True,
                    User.is_active == True,
                )
                .all()
            )

            return [
                {
                    "user_id": sub.user.user_id,
                    "chat_id": sub.chat_id,
                    "username": sub.user.username,
                    "first_name": sub.user.first_name,
                }
                for sub in subscriptions
            ]

        except Exception as e:
            logger.error(f"Ошибка при получении подписчиков {subscription_type}: {e}")
            return []
        finally:
            db.close()

    async def get_user_subscriptions(self, user_id: int) -> list[dict]:
        """Получение всех подписок пользователя"""
        db = get_db()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return []

            subscriptions = (
                db.query(UserSubscription)
                .filter(
                    UserSubscription.user_id == user.id,
                    UserSubscription.is_active == True,
                )
                .all()
            )

            return [
                {
                    "subscription_type": sub.subscription_type,
                    "chat_id": sub.chat_id,
                    "created_at": sub.created_at,
                }
                for sub in subscriptions
            ]

        except Exception as e:
            logger.error(f"Ошибка при получении подписок пользователя {user_id}: {e}")
            return []
        finally:
            db.close()

    async def cleanup_inactive_subscriptions(self) -> int:
        """Очистка неактивных подписок"""
        db = get_db()
        try:
            # Удаление подписок неактивных пользователей
            inactive_count = (
                db.query(UserSubscription)
                .join(User)
                .filter(User.is_active == False)
                .update({"is_active": False}, synchronize_session=False)
            )

            db.commit()
            logger.info(f"Очищено {inactive_count} неактивных подписок")
            return inactive_count

        except Exception as e:
            logger.error(f"Ошибка при очистке подписок: {e}")
            db.rollback()
            return 0
        finally:
            db.close()

    async def get_subscription_statistics(self) -> dict:
        """Получение статистики по подпискам"""
        db = get_db()
        try:
            stats = {}

            for sub_type in ["daily", "weekly", "monthly"]:
                count = (
                    db.query(UserSubscription)
                    .filter(
                        UserSubscription.subscription_type == sub_type,
                        UserSubscription.is_active == True,
                    )
                    .count()
                )
                stats[sub_type] = count

            total_users = db.query(User).filter(User.is_active == True).count()
            total_subscriptions = (
                db.query(UserSubscription)
                .filter(UserSubscription.is_active == True)
                .count()
            )

            stats["total_users"] = total_users
            stats["total_subscriptions"] = total_subscriptions

            return stats

        except Exception as e:
            logger.error(f"Ошибка при получении статистики подписок: {e}")
            return {}
        finally:
            db.close()

    async def toggle_user_status(self, user_id: int, is_active: bool) -> bool:
        """Изменение статуса пользователя (активный/неактивный)"""
        db = get_db()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                user.is_active = is_active
                user.updated_at = datetime.utcnow()

                # Если пользователь деактивирован, деактивируем его подписки
                if not is_active:
                    db.query(UserSubscription).filter(
                        UserSubscription.user_id == user.id
                    ).update({"is_active": False}, synchronize_session=False)

                db.commit()
                logger.info(
                    f"Статус пользователя {user_id} изменен на {'активный' if is_active else 'неактивный'}"
                )
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Ошибка при изменении статуса пользователя: {e}")
            db.rollback()
            return False
        finally:
            db.close()
