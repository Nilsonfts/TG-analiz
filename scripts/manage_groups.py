#!/usr/bin/env python3
"""
Утилита для управления группами в мониторинге
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from telethon import TelegramClient

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import get_db, TelegramGroup

load_dotenv()

class GroupManager:
    def __init__(self):
        self.api_id = int(os.getenv('API_ID'))
        self.api_hash = os.getenv('API_HASH')
        self.client = TelegramClient('session', self.api_id, self.api_hash)
    
    async def add_group_by_username(self, username: str):
        """Добавление группы по username"""
        try:
            await self.client.start()
            
            # Получение информации о группе
            entity = await self.client.get_entity(username)
            
            db = get_db()
            try:
                # Проверка, есть ли уже такая группа
                existing = db.query(TelegramGroup).filter(
                    TelegramGroup.group_id == entity.id
                ).first()
                
                if existing:
                    print(f"⚠️  Группа {username} уже добавлена в мониторинг")
                    return
                
                # Создание новой записи
                group = TelegramGroup(
                    group_id=entity.id,
                    username=getattr(entity, 'username', None),
                    title=getattr(entity, 'title', username),
                    description=getattr(entity, 'about', ''),
                    members_count=getattr(entity, 'participants_count', 0)
                )
                
                db.add(group)
                db.commit()
                
                print(f"✅ Группа '{group.title}' добавлена в мониторинг")
                print(f"   ID: {group.group_id}")
                print(f"   Участников: {group.members_count}")
                
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Ошибка при добавлении группы: {e}")
        finally:
            await self.client.disconnect()
    
    async def list_groups(self):
        """Список всех групп в мониторинге"""
        db = get_db()
        try:
            groups = db.query(TelegramGroup).all()
            
            if not groups:
                print("📭 Нет групп в мониторинге")
                return
            
            print("📊 Группы в мониторинге:")
            print("-" * 60)
            
            for group in groups:
                status = "🟢" if group.is_active else "🔴"
                print(f"{status} {group.title}")
                print(f"   ID: {group.group_id}")
                print(f"   Username: @{group.username or 'не указан'}")
                print(f"   Участников: {group.members_count:,}")
                print(f"   Статус: {'Активна' if group.is_active else 'Неактивна'}")
                print("-" * 60)
                
        finally:
            db.close()
    
    async def toggle_group_status(self, group_id: int, is_active: bool):
        """Изменение статуса группы"""
        db = get_db()
        try:
            group = db.query(TelegramGroup).filter(
                TelegramGroup.group_id == group_id
            ).first()
            
            if not group:
                print(f"❌ Группа с ID {group_id} не найдена")
                return
            
            group.is_active = is_active
            db.commit()
            
            status = "активирована" if is_active else "деактивирована"
            print(f"✅ Группа '{group.title}' {status}")
            
        finally:
            db.close()

async def main():
    """Главная функция"""
    manager = GroupManager()
    
    if len(sys.argv) < 2:
        print("🤖 Утилита управления группами")
        print("\nИспользование:")
        print("  python manage_groups.py add @username     # Добавить группу")
        print("  python manage_groups.py list              # Список групп") 
        print("  python manage_groups.py enable GROUP_ID   # Активировать группу")
        print("  python manage_groups.py disable GROUP_ID  # Деактивировать группу")
        return
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) > 2:
        username = sys.argv[2].replace('@', '')
        await manager.add_group_by_username(username)
    
    elif command == "list":
        await manager.list_groups()
    
    elif command == "enable" and len(sys.argv) > 2:
        group_id = int(sys.argv[2])
        await manager.toggle_group_status(group_id, True)
    
    elif command == "disable" and len(sys.argv) > 2:
        group_id = int(sys.argv[2])
        await manager.toggle_group_status(group_id, False)
    
    else:
        print("❌ Неверная команда или недостаточно аргументов")

if __name__ == "__main__":
    asyncio.run(main())
