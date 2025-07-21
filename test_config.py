#!/usr/bin/env python3
"""
Test configuration with your environment variables
"""
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Simulate your environment variables
os.environ.update({
    "BOT_TOKEN": "7404427944:AAFb67F8Kk8T3naTLtgSsz0VkCpbeGCPf68",
    "API_ID": "26538038", 
    "API_HASH": "e5b03c352c0c0bbc9bf73f306cdf442b",
    "ADMIN_USERS": "196614680",
    "REPORTS_CHAT_ID": "196614680",
    "DATABASE_URL": "postgresql://postgres:aTuoNuuGXeSjnCqwnpjirbtknzBBCACw@railway.app:5432/railway"
})

try:
    from src.config import settings
    
    print("🎯 Configuration Test Results:")
    print(f"✅ BOT_TOKEN: {'*' * 10}...{settings.bot_token[-8:] if settings.bot_token else 'MISSING'}")
    print(f"✅ TELEGRAM_API_ID: {settings.telegram_api_id}")
    print(f"✅ TELEGRAM_API_HASH: {'*' * 10}...{settings.telegram_api_hash[-8:] if settings.telegram_api_hash else 'MISSING'}")
    print(f"✅ ADMIN_USER_IDS: {settings.admin_user_ids}")
    print(f"✅ REPORT_CHAT_ID: {settings.report_chat_id}")
    print(f"✅ DATABASE_URL: {settings.database_url[:20]}...")
    
    if settings.bot_token and settings.telegram_api_id and settings.telegram_api_hash:
        print("\n🚀 All required settings configured! Bot should work.")
    else:
        print("\n⚠️ Missing required settings. Check environment variables.")
        
except Exception as e:
    print(f"❌ Configuration error: {e}")
    import traceback
    traceback.print_exc()
