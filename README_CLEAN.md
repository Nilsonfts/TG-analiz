# TG-analiz 📊

[![CI/CD Pipeline](https://github.com/Nilsonfts/TG-analiz/actions/workflows/ci.yml/badge.svg)](https://github.com/Nilsonfts/TG-analiz/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Railway Deploy](https://img.shields.io/badge/deploy-railway-blueviolet)](https://railway.app)

Comprehensive Telegram bot for channel analytics with Railway deployment support.

## 🚀 Features

- **Real-time Analytics** - Live channel statistics via Telethon API
- **Interactive Commands** - Rich command interface with inline keyboards  
- **Railway Ready** - Optimized for Railway deployment with health checks
- **Type Safe** - Full typing support with mypy strict mode
- **Test Coverage** - Comprehensive test suite with 90%+ coverage
- **CI/CD Pipeline** - Automated testing, linting, and deployment

## 📋 Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and bot introduction |
| `/summary` | Channel analytics summary |
| `/growth` | Growth statistics and trends |
| `/charts` | Interactive data visualization |
| `/channel_info` | Detailed channel information |
| `/help` | Commands reference |

## 🛠 Setup

### Prerequisites

- Python 3.12+
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
