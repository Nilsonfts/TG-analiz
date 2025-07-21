#!/usr/bin/env python3
"""
🔐 Генератор SESSION_STRING для Telethon

Этот скрипт поможет вам получить SESSION_STRING для Railway.
Запустите его локально и следуйте инструкциям.
"""
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

# Читаем данные из .env
API_ID = "26538038"
API_HASH = "e5b03c352c0c0bbc9bf73f306cdf442b"

async def generate_session():
    print("🔐 Генератор SESSION_STRING для Telethon")
    print("="*50)
    print("📱 Вам понадобится:")
    print("   • Номер телефона")
    print("   • Код подтверждения из SMS")
    print("   • Пароль двухфакторной аутентификации (если включен)")
    print("="*50)
    
    # Создаем клиент со строковой сессией
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    
    try:
        print("🚀 Подключение к Telegram...")
        await client.start()
        
        # Получаем информацию о пользователе
        me = await client.get_me()
        print(f"✅ Успешно авторизован как: {me.first_name}")
        if me.username:
            print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        
        # Получаем строку сессии
        session_string = client.session.save()
        
        print("\n" + "="*60)
        print("🎉 SESSION_STRING УСПЕШНО СОЗДАН!")
        print("="*60)
        print("📋 Скопируйте эту строку и добавьте в Railway Variables:")
        print("")
        print(f"SESSION_STRING={session_string}")
        print("")
        print("="*60)
        print("💡 Инструкция:")
        print("1. Перейдите в Railway Dashboard")
        print("2. Выберите ваш проект")
        print("3. Variables → Add Variable")
        print("4. Name: SESSION_STRING")
        print("5. Value: (вставьте строку выше)")
        print("6. Deploy!")
        print("="*60)
        
        # Тестируем доступ к каналу
        try:
            channel_id = -1002155183792  # Ваш канал
            channel = await client.get_entity(channel_id)
            print(f"✅ Доступ к каналу подтвержден: {channel.title}")
            
            # Получаем базовую статистику
            participants = await client.get_participants(channel, limit=0)
            print(f"📊 Участников в канале: {participants.total}")
            
        except Exception as e:
            print(f"⚠️ Ошибка доступа к каналу: {e}")
            print("💡 Убедитесь, что бот добавлен в канал как администратор")
            
    except KeyboardInterrupt:
        print("\n❌ Прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()
        print("👋 Отключение от Telegram")

if __name__ == "__main__":
    print("🚀 Запуск генератора сессии...")
    try:
        asyncio.run(generate_session())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        print("💡 Убедитесь, что у вас установлен telethon: pip install telethon")
