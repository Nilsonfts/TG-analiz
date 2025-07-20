"""Test configuration for pytest."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_bot_token():
    """Mock bot token for testing."""
    return "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client."""
    client = AsyncMock()
    client.get_entity = AsyncMock()
    client.get_dialogs = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_env_vars(mock_bot_token):
    """Mock environment variables."""
    env_vars = {
        "BOT_TOKEN": mock_bot_token,
        "API_ID": "12345",
        "API_HASH": "abcdef123456",
        "CHANNEL_ID": "@testchannel",
        "ADMIN_USERS": "123456789,987654321",
        "PORT": "8080",
    }
    
    # Apply the mocked environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Clean up
    for key in env_vars:
        os.environ.pop(key, None)


@pytest.fixture
def mock_update():
    """Mock Telegram Update object."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.callback_query = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Mock Telegram Context object."""
    context = MagicMock()
    context.bot = MagicMock()
    context.bot.send_message = AsyncMock()
    return context
