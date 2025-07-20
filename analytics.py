import asyncio
import logging
from datetime import datetime, timedelta

from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError

from config import Config
from database import Database, TelegramGroup

logger = logging.getLogger(__name__)


class AnalyticsCollector:
    """Класс для сбора аналитических данных"""

    def __init__(self, config: Config, database: Database):
        self.config = config
        self.db = database
        self.client = None

    async def init_client(self):
        """Инициализация Telegram клиента"""
        if not self.client:
            self.client = TelegramClient(
                "bot_session", self.config.api_id, self.config.api_hash
            )
            await self.client.start(bot_token=self.config.bot_token)
            logger.info("Telegram клиент инициализирован")

    async def collect_group_messages(self, group: TelegramGroup, hours_back: int = 24):
        """Сбор сообщений из группы за указанный период"""
        try:
            await self.init_client()

            # Получаем сущность группы
            entity = await self.client.get_entity(group.group_id)

            # Определяем временной диапазон
            offset_date = datetime.now() - timedelta(hours=hours_back)

            messages = []
            async for message in self.client.iter_messages(
                entity,
                offset_date=offset_date,
                limit=self.config.max_messages_per_request,
            ):
                message_data = {
                    "message_id": message.id,
                    "group_id": group.group_id,
                    "user_id": message.from_id.user_id if message.from_id else None,
                    "username": None,
                    "text": message.message if message.message else "",
                    "date": message.date,
                    "reply_to_message_id": message.reply_to_msg_id
                    if message.reply_to
                    else None,
                    "forward_from_user_id": None,
                    "views": message.views if hasattr(message, "views") else 0,
                    "reactions": {},
                }

                # Получаем username если доступен
                if message.sender:
                    message_data["username"] = getattr(message.sender, "username", None)

                # Информация о пересылке
                if message.forward:
                    if hasattr(message.forward, "from_id") and message.forward.from_id:
                        message_data[
                            "forward_from_user_id"
                        ] = message.forward.from_id.user_id

                # Реакции (если есть)
                if hasattr(message, "reactions") and message.reactions:
                    reactions = {}
                    for reaction in message.reactions.results:
                        emoji = (
                            reaction.reaction.emoticon
                            if hasattr(reaction.reaction, "emoticon")
                            else str(reaction.reaction)
                        )
                        reactions[emoji] = reaction.count
                    message_data["reactions"] = reactions

                messages.append(message_data)

            # Сохраняем сообщения в базу данных
            if messages:
                await self.db.save_messages(messages)
                logger.info(
                    f"Собрано {len(messages)} сообщений из группы {group.title}"
                )

            return len(messages)

        except FloodWaitError as e:
            logger.warning(f"FloodWaitError: ожидание {e.seconds} секунд")
            await asyncio.sleep(e.seconds)
            return 0
        except ChannelPrivateError:
            logger.error(f"Группа {group.group_id} стала приватной")
            return 0
        except Exception as e:
            logger.error(f"Ошибка при сборе данных из группы {group.group_id}: {e}")
            return 0

    async def update_group_info(self, group: TelegramGroup):
        """Обновление информации о группе"""
        try:
            await self.init_client()
            entity = await self.client.get_entity(group.group_id)

            # Обновляем информацию о группе
            group.title = entity.title
            group.username = getattr(entity, "username", None)

            # Получаем количество участников
            if hasattr(entity, "participants_count"):
                group.members_count = entity.participants_count
            else:
                # Для каналов может потребоваться другой подход
                try:
                    full_info = await self.client.get_stats(entity)
                    if hasattr(full_info, "followers"):
                        group.members_count = full_info.followers.current
                except:
                    pass

            # Сохраняем обновленную информацию
            await self.db.add_group(group)

        except Exception as e:
            logger.error(
                f"Ошибка при обновлении информации о группе {group.group_id}: {e}"
            )

    async def collect_all_data(self):
        """Сбор данных со всех активных групп"""
        try:
            groups = await self.db.get_active_groups()
            total_messages = 0

            for group in groups:
                # Обновляем информацию о группе
                await self.update_group_info(group)

                # Собираем сообщения
                messages_count = await self.collect_group_messages(group)
                total_messages += messages_count

                # Небольшая пауза между группами
                await asyncio.sleep(2)

            logger.info(
                f"Сбор аналитики завершен. Обработано {total_messages} сообщений из {len(groups)} групп"
            )

        except Exception as e:
            logger.error(f"Ошибка при сборе аналитики: {e}")
        finally:
            if self.client:
                await self.client.disconnect()
                self.client = None

    async def calculate_daily_analytics(self, group_id: int, date: datetime):
        """Расчет дневной аналитики для группы"""
        try:
            stats = await self.db.get_daily_stats(group_id, date)

            # Дополнительные вычисления
            hourly_activity = await self.calculate_hourly_activity(group_id, date)

            analytics_data = {
                "group_id": group_id,
                "date": date.date(),
                "messages_count": stats["messages_count"],
                "users_count": stats["users_count"],
                "active_users": [user["user_id"] for user in stats["top_users"]],
                "top_users": stats["top_users"],
                "hourly_activity": hourly_activity,
            }

            return analytics_data

        except Exception as e:
            logger.error(f"Ошибка при расчете аналитики для группы {group_id}: {e}")
            return None

    async def calculate_hourly_activity(
        self, group_id: int, date: datetime
    ) -> dict[str, int]:
        """Расчет почасовой активности"""
        # Упрощенная версия - можно расширить
        return {str(i): 0 for i in range(24)}
