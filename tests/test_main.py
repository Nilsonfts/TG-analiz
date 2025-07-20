"""Tests for main bot functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from main import (
    channel_info_command,
    charts_command,
    get_real_channel_stats,
    growth_command,
    help_command,
    init_telethon,
    start_command,
    summary_command,
)


class TestBotCommands:
    """Test bot command handlers."""

    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test /start command."""
        await start_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Добро пожаловать" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_help_command(self, mock_update, mock_context):
        """Test /help command."""
        await help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Доступные команды" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_summary_command(self, mock_update, mock_context):
        """Test /summary command."""
        await summary_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Сводка аналитики" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_growth_command(self, mock_update, mock_context):
        """Test /growth command."""
        await growth_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Рост канала" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_charts_command(self, mock_update, mock_context):
        """Test /charts command."""
        await charts_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()


class TestTelethonIntegration:
    """Test Telethon integration."""

    @pytest.mark.asyncio
    async def test_init_telethon_success(self, mock_env_vars):
        """Test successful Telethon initialization."""
        with patch("main.TelegramClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.start = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await init_telethon()
            assert result is True
            mock_client.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_telethon_no_credentials(self):
        """Test Telethon initialization without credentials."""
        with patch.dict("os.environ", {}, clear=True):
            result = await init_telethon()
            assert result is False

    @pytest.mark.asyncio
    async def test_get_real_channel_stats_no_client(self):
        """Test getting channel stats without client."""
        with patch("main.telethon_client", None):
            result = await get_real_channel_stats()
            assert result is None

    @pytest.mark.asyncio
    async def test_channel_info_command(self, mock_update, mock_context, mock_env_vars):
        """Test /channel_info command."""
        await channel_info_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert "Информация о канале" in call_args[0][0]


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_command_with_exception(self, mock_update, mock_context):
        """Test command handling when an exception occurs."""
        mock_update.message.reply_text.side_effect = Exception("Test error")

        # Should not raise exception
        try:
            await start_command(mock_update, mock_context)
        except Exception as e:
            pytest.fail(f"Command should handle exceptions gracefully: {e}")


@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring external dependencies."""

    @pytest.mark.asyncio
    async def test_main_without_bot_token(self):
        """Test main function without bot token."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("main.start_http_server") as mock_http:
                with patch("main.logger") as mock_logger:
                    from main import main

                    await main()
                    mock_logger.error.assert_called()
                    mock_http.assert_called_once()
