# 🤖 TG-analiz - НОВАЯ РАБОЧАЯ ВЕРСИЯ

[![Railway Deploy](https://img.shields.io/badge/Railway-Deploy-blueviolet?logo=railway&logoColor=white)](https://railway.app/new/template?template=https://github.com/Nilsonfts/TG-analiz)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram&logoColor=white)](https://core.telegram.org/bots)

> **🚀 НОВАЯ РАБОЧАЯ ВЕРСИЯ с исправленными проблемами и реальными данными**

## ✅ ЧТО ИСПРАВЛЕНО В НОВОЙ ВЕРСИИ:

### 🔧 **КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ:**
- ✅ **Исправлена переменная `story_forwards`** - была не инициализирована 
- ✅ **Команда `/summary`** - теперь показывает реальные данные вместо фиксированных
- ✅ **Команда `/insights`** - расчеты на основе реальной аналитики
- ✅ **Команда `/growth`** - прогнозы на основе активности канала
- ✅ **Команда `/channel_info`** - улучшенное получение информации о канале
- ✅ **Команда `/smm`** - исправлена терминология и добавлены объяснения API

### 📺 **ТЕРМИНОЛОГИЯ "STORIES" → "СТОРИС":**
- ✅ Унифицирована русскоязычная терминология
- ✅ Все отчеты используют "СТОРИС" вместо "Stories"
- ✅ Обновлено логирование и сообщения

### 📊 **ОБЪЯСНЕНИЯ ОГРАНИЧЕНИЙ API:**
- ✅ Во всех отчетах добавлены пояснения об ограничениях Telegram API
- ✅ Пользователи понимают откуда берутся данные
- ✅ Четкое разделение: реальные данные vs оценочные

## 🚀 Quick Deploy

**Deploy in 1 minute:**

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Nilsonfts/TG-analiz)

1. Click "Deploy on Railway" ↑
2. Add `BOT_TOKEN` from [@BotFather](https://t.me/BotFather)
3. Add `CHANNEL_ID`, `API_ID`, `API_HASH`, `SESSION_STRING`
4. Your bot is live! 🎉

## 🤖 Команды бота

- `/start` - Информация о боте и статус
- `/status` - Проверка всех систем
- `/summary` - 📊 **Краткая сводка канала (РЕАЛЬНЫЕ ДАННЫЕ)**
- `/growth` - 📈 **Анализ роста с прогнозами (РЕАЛЬНЫЕ ДАННЫЕ)**
- `/insights` - 🧠 **Маркетинговые инсайты (РЕАЛЬНЫЕ ДАННЫЕ)**
- `/analiz` - 📊 Визуальная аналитика (PNG графики)
- `/charts` - Интерактивные графики
- `/smm` - 📊 **Еженедельный SMM-отчет (ИСПРАВЛЕН)**
- `/daily_report` - 📅 Ежедневный отчет
- `/monthly_report` - 📆 Месячный отчет
- `/channel_info` - **Информация о канале (УЛУЧШЕНО)**
- `/help` - Справка по командам

## 📊 Что определяется как "СТОРИС":

В Telegram каналах **"СТОРИС"** = **визуальный контент**:
- 📹 **Короткие видео** (≤60 секунд)
- 📸 **Фото без текста** или с коротким текстом (<50 символов)
- 🎥 **Кружки** = круглые видео-сообщения (выделены отдельно)

## ⚠️ Ограничения Telegram API:

- **Точные подписки/отписки** недоступны через публичный API
- **Уведомления** недоступны через публичный API  
- **СТОРИС** определяются алгоритмом (указано выше)
- **Данные о подписках** - оценочные, на основе активности

## 🛠 Setup

### Prerequisites

- Python 3.12+
- Railway Account (free tier available)
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Telegram API credentials from [my.telegram.org/apps](https://my.telegram.org/apps)

### Environment Variables

Добавьте в Railway Variables:

```env
# Обязательные
BOT_TOKEN=your_bot_token_from_botfather
CHANNEL_ID=your_channel_id
API_ID=your_api_id
API_HASH=your_api_hash
SESSION_STRING=your_session_string

# Опциональные  
ADMIN_USERS=196614680,208281210,1334453330
TIMEZONE=Europe/Moscow
REPORTS_CHAT_ID=196614680
```

## 📈 Features

- **Real-time Analytics** - Live channel statistics via Telethon API
- **Interactive Commands** - Rich command interface with inline keyboards  
- **Railway Ready** - Optimized for Railway deployment with health checks
- **Fixed Data** - All commands now show real data instead of hardcoded values
- **API Explanations** - Clear explanations of Telegram API limitations
- **Russian Terminology** - Consistent use of "СТОРИС" throughout the app

## 🔧 Technical Improvements

- ✅ Fixed uninitialized `story_forwards` variable
- ✅ Improved `get_real_channel_stats()` function
- ✅ Real analytics data in all commands
- ✅ Unified terminology across all reports
- ✅ Added API limitation explanations
- ✅ Enhanced error handling and logging

## 🚀 Deployment

1. **Fork this repository**
2. **Deploy to Railway:**
   - Connect your GitHub account
   - Import your forked repository
   - Add environment variables
   - Deploy!

3. **Test your bot:**
   ```
   /start - Check if bot responds
   /status - Verify all systems
   /summary - Test real data collection
   ```

## 📞 Support

If you encounter any issues:

1. Check `/status` command for diagnostics
2. Verify all environment variables are set
3. Check Railway logs for errors

---

**🎉 НОВАЯ РАБОЧАЯ ВЕРСИЯ готова к использованию!**

*Все основные проблемы исправлены, данные теперь реальные, терминология унифицирована.*
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Telegram API credentials (api_id, api_hash)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Nilsonfts/TG-analiz.git
   cd TG-analiz
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token | ✅ |
| `API_ID` | Telegram API ID | ✅ |
| `API_HASH` | Telegram API hash | ✅ |
| `CHANNEL_ID` | Target channel ID/username | ❌ |
| `ADMIN_USERS` | Comma-separated admin user IDs | ❌ |
| `PORT` | HTTP server port (default: 8080) | ❌ |

## 🚀 Railway Deployment

1. **Connect to Railway**
   ```bash
   # Railway automatically deploys from main branch
   ```

2. **Set environment variables in Railway dashboard**
   - Add all required variables from the table above

3. **Deploy**
   ```bash
   git push origin main
   # Railway auto-deploys
   ```

## 🧪 Development

### Code Quality

```bash
# Linting
ruff check .
ruff format .

# Type checking  
mypy main.py --strict

# Testing
pytest --cov=. --cov-report=html
```

### Project Structure

```
TG-analiz/
├── main.py                 # Main bot application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container configuration
├── pyproject.toml         # Tool configurations
├── .github/workflows/     # CI/CD pipeline
├── tests/                 # Test suite
│   ├── conftest.py       # Test configuration
│   └── test_main.py      # Main tests
├── utils/                # Utility modules
├── services/             # Service layer
└── database/             # Database models
```

## 🔧 Configuration

### Ruff (Linting & Formatting)
Configured in `pyproject.toml` with Python 3.12 target, 88 character line length.

### MyPy (Type Checking)
Strict mode enabled with comprehensive type checking rules.

### Pytest (Testing)
Configured with coverage reporting and custom markers for integration tests.

## 📊 Monitoring

- **Health Check**: `GET /health` - Returns bot status
- **Railway Logs**: Available in Railway dashboard
- **Coverage Reports**: Generated in `htmlcov/` directory

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes with tests
4. Run quality checks: `ruff check . && mypy main.py --strict && pytest`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [Telethon](https://github.com/LonamiWebs/Telethon) - Telegram API client
- [Railway](https://railway.app) - Deployment platform

---

**Made with ❤️ for the Telegram community**
