import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
import threading
import random
import asyncio
from flask import Flask

# --- 1. 設定（環境変数の読み込み） ---
# トークンはどちらの名前でも動くようにチェックします
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

def get_id(key):
    val = os.getenv(key)
    return int(val) if val and val.isdigit() else None

# 使用するチャンネルIDリスト
CH_NEWS = get_id("CH_NEWS")
CH_LOG = get_id("CH_LOG")

# --- 2. Flask（Render稼働維持用） ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. ボットクラス定義 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # スラッシュコマンドを同期
        await self.tree.sync()
        self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ ログイン成功: {self.user.name}")

    # 定期実行タスク
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst).strftime('%H:%M')
        
        if now == "08:00" and CH_NEWS:
            ch = self.get_channel(CH_NEWS)
            if ch: await ch.send("🌅 おはようございます！8時になりました。")

    @bot.event
    async def on_message(self, message):
        if message.author.bot: return
        await self.process_commands(message)

bot = MyBot()

# --- 4. スラッシュコマンド ---
@bot.tree.command(name="omikuji", description="おみくじを引きます")
async def omikuji(interaction: discord.Interaction):
    res = random.choice(["大吉", "中吉", "小吉", "吉", "凶"])
    await interaction.response.send_message(f"🔮 運勢は **{res}** です！")

# --- 5. 実行処理 ---
if __name__ == "__main__":
    # Webサーバー起動
    t = threading.Thread(target=run_web, daemon=True)
    t.start()

    if TOKEN:
        print("🤖 Botの起動を開始します...")
        bot.run(TOKEN)
    else:
        # トークンがない場合、ログに分かりやすく表示
        print("❌ 【重大エラー】トークンが見つかりません。")
        print("RenderのEnvironment設定で 'DISCORD_BOT_TOKEN' が登録されているか確認してください。")
