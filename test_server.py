#!/usr/bin/env python3
"""
Простой тест HTTP сервера
"""

import asyncio
import os
from aiohttp import web

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

async def root_handler(request):
    """Root endpoint"""
    return web.Response(text="Test server is running", status=200)

async def start_server():
    """Запуск тестового сервера"""
    app = web.Application()
    
    # Добавление маршрутов
    app.router.add_get('/', root_handler)
    app.router.add_get('/health', health_check)
    
    # Запуск сервера
    port = int(os.getenv('PORT', 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Test server started on port {port}")
    
    # Поддержание работы
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(start_server())
