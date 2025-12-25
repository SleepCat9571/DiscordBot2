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
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

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
        # command_prefix は ! に設定
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 起動時にスラッシュコマンドを同期
        await self.tree.sync()
        if not self.scheduled_task.is_running():
            self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ ログイン成功: {self.user.name}")

    # 定期実行タスク（挨拶など）
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst).strftime('%H:%M')
        if now == "08:00":
            print("朝の定期処理を実行します")

    # メッセージを受け取った時の処理（クラス内なので self を使う）
    async def on_message(self, message):
        if message.author.bot:
            return
        await self.process_commands(message)

# ボットのインスタンスを作成
bot = MyBot()

# --- 4. スラッシュコマンド（ここからは bot.tree を使う） ---

@bot.tree.command(name="omikuji", description="おみくじを引きます")
async def omikuji(interaction: discord.Interaction):
    res = random.choice(["大吉", "中吉", "小吉", "吉", "凶"])
    await interaction.response.send_message(f"🔮 運勢は **{res}** です！")

@bot.tree.command(name="timer", description="指定した秒数後にメンションします")
async def timer(interaction: discord.Interaction, 秒: int):
    await interaction.response.send_message(f"⏰ {秒}秒のタイマーを開始しました。")
    await asyncio.sleep(秒)
    await interaction.channel.send(f"🔔 {interaction.user.mention} 時間になりました！")

# --- 5. 実行処理 ---
if __name__ == "__main__":
    # Webサーバー起動
    t = threading.Thread(target=run_web, daemon=True)
    t.start()

    if TOKEN:
        print("🤖 Botの起動を開始します...")
        bot.run(TOKEN)
    else:
        print("❌ トークンが見つかりません。RenderのEnvironment設定を確認してください。")
