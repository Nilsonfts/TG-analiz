# 🚀 Quick Deploy to Railway

## 1-Minute Setup

### Step 1: Deploy on Railway
1. Go to [Railway.app](https://railway.app)
2. Click "Deploy from GitHub repo"
3. Select: `Nilsonfts/TG-analiz`
4. Choose branch: `main`

### Step 2: Add Bot Token
1. In Railway dashboard → Variables
2. Add: `BOT_TOKEN` = `your_bot_token_from_@BotFather`
3. Click "Deploy"

### Step 3: Test
1. Health check: `https://your-app.railway.app/health`
2. Open your bot in Telegram
3. Send `/start`

## ✅ Done!

Your bot is now live and ready to use.

**Need the bot token?** Message [@BotFather](https://t.me/BotFather) on Telegram:
1. `/newbot`
2. Choose name and username
3. Copy the token

---

**All commands work:** `/start` `/summary` `/growth` `/charts` `/help`

**Advanced setup:** See `RAILWAY_DEPLOYMENT.md` for channel analytics features.
