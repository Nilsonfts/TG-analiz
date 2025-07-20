import asyncio
import logging
from datetime import datetime, timedelta

from telethon import TelegramClient
from telethon.errors import ChannelPrivateError, FloodWaitError
from telethon.tl.types import MessageMediaDocument, MessageMediaPhoto

from database.models import (
    ContentAnalytics,
    GroupAnalytics,
    GroupPost,
    PostReaction,
    TelegramGroup,
    get_db,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Сервис для сбора аналитических данных из Telegram"""

    def __init__(self):
        self.monitored_groups = []  # Список групп для мониторинга

    async def collect_data(self, client: TelegramClient):
        """Основной метод сбора данных"""
        try:
            await self._update_monitored_groups()

            for group_data in self.monitored_groups:
                try:
                    await self._collect_group_data(client, group_data)
                    await asyncio.sleep(2)  # Задержка между группами
                except Exception as e:
                    logger.error(
                        f"Ошибка при сборе данных для группы {group_data['title']}: {e}"
                    )

        except Exception as e:
            logger.error(f"Ошибка в сборе данных: {e}")

    async def _update_monitored_groups(self):
        """Обновление списка отслеживаемых групп"""
        db = get_db()
        try:
            groups = (
                db.query(TelegramGroup).filter(TelegramGroup.is_active is True).all()
            )
            self.monitored_groups = [
                {
                    "id": group.id,
                    "group_id": group.group_id,
                    "username": group.username,
                    "title": group.title,
                }
                for group in groups
            ]
        finally:
            db.close()

    async def _collect_group_data(self, client: TelegramClient, group_data: dict):
        """Сбор данных для конкретной группы"""
        try:
            # Получение информации о группе
            entity = await client.get_entity(group_data["group_id"])

            if not hasattr(entity, "participants_count"):
                logger.warning(
                    f"Не удается получить количество участников для {group_data['title']}"
                )
                return

            # Обновление информации о группе
            await self._update_group_info(group_data["id"], entity)

            # Сбор статистики постов
            await self._collect_posts_data(client, group_data, entity)

            # Сохранение аналитики
            await self._save_group_analytics(group_data["id"], entity)

        except ChannelPrivateError:
            logger.warning(f"Группа {group_data['title']} стала приватной")
        except FloodWaitError as e:
            logger.warning(
                f"FloodWait для группы {group_data['title']}: {e.seconds} секунд"
            )
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Ошибка при сборе данных группы {group_data['title']}: {e}")

    async def _update_group_info(self, group_id: int, entity):
        """Обновление информации о группе"""
        db = get_db()
        try:
            group = db.query(TelegramGroup).filter(TelegramGroup.id == group_id).first()
            if group:
                group.members_count = getattr(entity, "participants_count", 0)
                group.title = getattr(entity, "title", group.title)
                group.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о группе: {e}")
            db.rollback()
        finally:
            db.close()

    async def _collect_posts_data(
        self, client: TelegramClient, group_data: dict, entity
    ):
        """Сбор данных о постах"""
        try:
            # Получение последних постов (за последние 24 часа)
            yesterday = datetime.now() - timedelta(days=1)

            posts = []
            async for message in client.iter_messages(entity, limit=100):
                if message.date < yesterday:
                    break

                if message.message or message.media:
                    posts.append(message)

            # Обработка каждого поста
            for post in posts:
                await self._process_post(group_data["id"], post)

        except Exception as e:
            logger.error(f"Ошибка при сборе постов: {e}")

    async def _process_post(self, group_id: int, message):
        """Обработка отдельного поста"""
        db = get_db()
        try:
            # Проверка, есть ли уже этот пост в базе
            existing_post = (
                db.query(GroupPost)
                .filter(
                    GroupPost.group_id == group_id, GroupPost.message_id == message.id
                )
                .first()
            )

            if existing_post:
                # Обновление метрик существующего поста
                existing_post.views = getattr(message, "views", 0)
                existing_post.updated_at = datetime.utcnow()

                # Обновление реакций если есть
                if hasattr(message, "reactions") and message.reactions:
                    await self._update_post_reactions(
                        existing_post.id, message.reactions
                    )
            else:
                # Создание нового поста
                content_type = self._determine_content_type(message)

                new_post = GroupPost(
                    group_id=group_id,
                    post_id=message.id,
                    message_id=message.id,
                    content_type=content_type,
                    text=message.message or "",
                    media_count=1 if message.media else 0,
                    has_links=self._has_links(message.message or ""),
                    views=getattr(message, "views", 0),
                    post_date=message.date,
                    reactions_count=0,
                    comments_count=0,
                    forwards_count=getattr(message, "forwards", 0),
                )

                db.add(new_post)
                db.flush()  # Получаем ID поста

                # Сохранение реакций если есть
                if hasattr(message, "reactions") and message.reactions:
                    await self._save_post_reactions(new_post.id, message.reactions)

            db.commit()

        except Exception as e:
            logger.error(f"Ошибка при обработке поста: {e}")
            db.rollback()
        finally:
            db.close()

    def _determine_content_type(self, message) -> str:
        """Определение типа контента поста"""
        if message.media:
            if isinstance(message.media, MessageMediaPhoto):
                return "photo"
            elif isinstance(message.media, MessageMediaDocument):
                if hasattr(message.media.document, "mime_type"):
                    mime_type = message.media.document.mime_type
                    if mime_type.startswith("video/"):
                        return "video"
                    elif mime_type.startswith("audio/"):
                        return "audio"
                    else:
                        return "document"
                return "document"
            else:
                return "media"
        elif message.message:
            return "text"
        else:
            return "other"

    def _has_links(self, text: str) -> bool:
        """Проверка наличия ссылок в тексте"""
        link_indicators = ["http://", "https://", "www.", ".com", ".ru", ".org", "t.me"]
        return any(indicator in text.lower() for indicator in link_indicators)

    async def _save_post_reactions(self, post_id: int, reactions):
        """Сохранение реакций поста"""
        db = get_db()
        try:
            for reaction in reactions.results:
                if hasattr(reaction, "reaction"):
                    reaction_type = str(reaction.reaction)
                    count = reaction.count

                    post_reaction = PostReaction(
                        post_id=post_id, reaction_type=reaction_type, count=count
                    )
                    db.add(post_reaction)

            db.commit()
        except Exception as e:
            logger.error(f"Ошибка при сохранении реакций: {e}")
            db.rollback()
        finally:
            db.close()

    async def _update_post_reactions(self, post_id: int, reactions):
        """Обновление реакций поста"""
        db = get_db()
        try:
            # Удаление старых реакций
            db.query(PostReaction).filter(PostReaction.post_id == post_id).delete()

            # Добавление новых реакций
            for reaction in reactions.results:
                if hasattr(reaction, "reaction"):
                    reaction_type = str(reaction.reaction)
                    count = reaction.count

                    post_reaction = PostReaction(
                        post_id=post_id, reaction_type=reaction_type, count=count
                    )
                    db.add(post_reaction)

            db.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении реакций: {e}")
            db.rollback()
        finally:
            db.close()

    async def _save_group_analytics(self, group_id: int, entity):
        """Сохранение аналитики группы"""
        db = get_db()
        try:
            today = datetime.utcnow().date()

            # Проверка, есть ли уже запись за сегодня
            existing_analytics = (
                db.query(GroupAnalytics)
                .filter(
                    GroupAnalytics.group_id == group_id,
                    GroupAnalytics.date >= datetime.combine(today, datetime.min.time()),
                    GroupAnalytics.date
                    < datetime.combine(today + timedelta(days=1), datetime.min.time()),
                )
                .first()
            )

            current_members = getattr(entity, "participants_count", 0)

            # Получение предыдущих данных для расчета роста
            yesterday = today - timedelta(days=1)
            previous_analytics = (
                db.query(GroupAnalytics)
                .filter(
                    GroupAnalytics.group_id == group_id,
                    GroupAnalytics.date
                    >= datetime.combine(yesterday, datetime.min.time()),
                    GroupAnalytics.date
                    < datetime.combine(
                        yesterday + timedelta(days=1), datetime.min.time()
                    ),
                )
                .first()
            )

            members_growth = 0
            members_growth_percent = 0.0

            if previous_analytics:
                members_growth = current_members - previous_analytics.members_count
                if previous_analytics.members_count > 0:
                    members_growth_percent = (
                        members_growth / previous_analytics.members_count
                    ) * 100

            # Получение статистики постов за сегодня
            posts_stats = await self._get_daily_posts_stats(group_id, today)

            if existing_analytics:
                # Обновление существующей записи
                existing_analytics.members_count = current_members
                existing_analytics.members_growth = members_growth
                existing_analytics.members_growth_percent = members_growth_percent
                existing_analytics.posts_count = posts_stats["posts_count"]
                existing_analytics.avg_views = posts_stats["avg_views"]
                existing_analytics.avg_reactions = posts_stats["avg_reactions"]
                existing_analytics.total_views = posts_stats["total_views"]
            else:
                # Создание новой записи
                analytics = GroupAnalytics(
                    group_id=group_id,
                    date=datetime.utcnow(),
                    members_count=current_members,
                    members_growth=members_growth,
                    members_growth_percent=members_growth_percent,
                    posts_count=posts_stats["posts_count"],
                    avg_views=posts_stats["avg_views"],
                    avg_reactions=posts_stats["avg_reactions"],
                    total_views=posts_stats["total_views"],
                )
                db.add(analytics)

            # Сохранение аналитики по типам контента
            await self._save_content_analytics(group_id, today)

            db.commit()

        except Exception as e:
            logger.error(f"Ошибка при сохранении аналитики: {e}")
            db.rollback()
        finally:
            db.close()

    async def _get_daily_posts_stats(self, group_id: int, date) -> dict:
        """Получение статистики постов за день"""
        db = get_db()
        try:
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date + timedelta(days=1), datetime.min.time())

            posts = (
                db.query(GroupPost)
                .filter(
                    GroupPost.group_id == group_id,
                    GroupPost.post_date >= start_date,
                    GroupPost.post_date < end_date,
                )
                .all()
            )

            if not posts:
                return {
                    "posts_count": 0,
                    "avg_views": 0.0,
                    "avg_reactions": 0.0,
                    "total_views": 0,
                }

            total_views = sum(post.views for post in posts)
            total_reactions = sum(post.reactions_count for post in posts)

            return {
                "posts_count": len(posts),
                "avg_views": total_views / len(posts) if posts else 0.0,
                "avg_reactions": total_reactions / len(posts) if posts else 0.0,
                "total_views": total_views,
            }

        finally:
            db.close()

    async def _save_content_analytics(self, group_id: int, date):
        """Сохранение аналитики по типам контента"""
        db = get_db()
        try:
            start_date = datetime.combine(date, datetime.min.time())
            end_date = datetime.combine(date + timedelta(days=1), datetime.min.time())

            # Группировка постов по типам контента
            posts = (
                db.query(GroupPost)
                .filter(
                    GroupPost.group_id == group_id,
                    GroupPost.post_date >= start_date,
                    GroupPost.post_date < end_date,
                )
                .all()
            )

            content_stats = {}
            for post in posts:
                content_type = post.content_type
                if content_type not in content_stats:
                    content_stats[content_type] = {
                        "posts_count": 0,
                        "total_views": 0,
                        "total_reactions": 0,
                    }

                content_stats[content_type]["posts_count"] += 1
                content_stats[content_type]["total_views"] += post.views
                content_stats[content_type]["total_reactions"] += post.reactions_count

            # Сохранение в базу данных
            for content_type, stats in content_stats.items():
                avg_views = (
                    stats["total_views"] / stats["posts_count"]
                    if stats["posts_count"] > 0
                    else 0
                )
                avg_reactions = (
                    stats["total_reactions"] / stats["posts_count"]
                    if stats["posts_count"] > 0
                    else 0
                )

                # Проверка существующей записи
                existing = (
                    db.query(ContentAnalytics)
                    .filter(
                        ContentAnalytics.group_id == group_id,
                        ContentAnalytics.date >= start_date,
                        ContentAnalytics.date < end_date,
                        ContentAnalytics.content_type == content_type,
                    )
                    .first()
                )

                if existing:
                    existing.posts_count = stats["posts_count"]
                    existing.avg_views = avg_views
                    existing.avg_reactions = avg_reactions
                    existing.total_views = stats["total_views"]
                    existing.total_reactions = stats["total_reactions"]
                else:
                    content_analytics = ContentAnalytics(
                        group_id=group_id,
                        date=datetime.utcnow(),
                        content_type=content_type,
                        posts_count=stats["posts_count"],
                        avg_views=avg_views,
                        avg_reactions=avg_reactions,
                        total_views=stats["total_views"],
                        total_reactions=stats["total_reactions"],
                    )
                    db.add(content_analytics)

            db.commit()

        except Exception as e:
            logger.error(f"Ошибка при сохранении аналитики контента: {e}")
            db.rollback()
        finally:
            db.close()

    async def add_group_to_monitoring(self, group_identifier: str) -> bool:
        """Добавление группы в мониторинг"""
        # Здесь можно добавить логику для добавления новых групп
        # Например, через username или ID группы
        pass
