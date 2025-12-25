import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
import os
import requests
import threading
import random
import asyncio
from flask import Flask
from deep_translator import GoogleTranslator

# --- 1. 設定（環境変数の読み込み） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")

def get_id(key):
    val = os.getenv(key)
    return int(val) if val and val.isdigit() else None

CH_IDS = {
    "news": get_id("CH_NEWS"),
    "greeting": get_id("CH_GREETING"),
    "log": get_id("CH_LOG"),
    "welcome": get_id("CH_WELCOME"),
    "guard": get_id("CH_GUARD"),
    "verify": get_id("CH_VERIFY"),
}

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"]
WEATHER_AREAS = {"東京": "130000", "大阪": "270000", "福岡": "400000", "札幌": "016000"}

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
        # 起動時にスラッシュコマンドを同期
        await self.tree.sync()
        if not self.scheduled_task.is_running():
            self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ ログイン成功: {self.user.name}")

# --- 定期タスク (08:00 ニュース＆天気) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst).strftime('%H:%M')

        # 朝 08:00 実行
        if now == "08:00" and CH_IDS["news"]:
            ch = self.get_channel(CH_IDS["news"])
            if not ch: return

            # --- A. 天気予報の取得 ---
            weather_msg = "🌅 **朝の定期連絡です**\n\n🌡️ **各地の天気**\n"
            for area, code in WEATHER_AREAS.items():
                try:
                    w_url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                    res = requests.get(w_url).json()
                    w = res[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                    weather_msg += f"・{area}: {w}\n"
                except: weather_msg += f"・{area}: 取得失敗\n"

            # --- B. ニュース速報の取得 (Google News RSS) ---
            news_msg = "\n📰 **最新の主要ニュース**\n"
            try:
                # 日本の主要ニュースRSS
                news_url = "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"
                from bs4 import BeautifulSoup
                import xml.etree.ElementTree as ET

                res = requests.get(news_url)
                root = ET.fromstring(res.text)
                # 上位5件を取得
                for item in root.findall('.//item')[:5]:
                    title = item.find('title').text
                    link = item.find('link').text
                    news_msg += f"・{title}\n<{link}>\n"
            except Exception as e:
                news_msg += "ニュースの取得中にエラーが発生しました。"
                print(f"News Error: {e}")

            # まとめて送信
            await ch.send(weather_msg + news_msg)

        # 昼 12:00 挨拶
        if now == "12:00" and CH_IDS["greeting"]:
            ch = self.get_channel(CH_IDS["greeting"])
            if ch: await ch.send("🍱 12:00になりました。お昼休憩にしましょう！")

    # --- イベント処理 ---
    async def on_member_join(self, member):
        ch = self.get_channel(CH_IDS["welcome"])
        if ch: await ch.send(f"🎊 {member.mention} さん、サーバーへようこそ！")

    async def on_voice_state_update(self, member, before, after):
        ch = self.get_channel(CH_IDS["log"])
        if not ch: return
        if before.channel is None and after.channel is not None:
            await ch.send(f"🎤 **{member.display_name}** が `{after.channel.name}` に参加")
        elif before.channel is not None and after.channel is None:
            await ch.send(f"👋 **{member.display_name}** が退出")

    async def on_message(self, message):
        if message.author.bot: return
        # 禁止用語監視
        if any(word in message.content for word in BAD_WORDS):
            try:
                await message.delete()
                await message.author.timeout(timedelta(minutes=10), reason="禁止用語使用")
                log = self.get_channel(CH_IDS["guard"])
                if log: await log.send(f"🛡️ {message.author.mention} を禁止用語使用で10分ミュートしました。")
            except: pass
        await self.process_commands(message)

bot = MyBot()

# --- 4. スラッシュコマンド ---

@bot.tree.command(name="omikuji", description="今日のおみくじを引きます")
async def omikuji(interaction: discord.Interaction):
    res = random.choice(["大吉", "中吉", "小吉", "末吉", "凶"])
    await interaction.response.send_message(f"🔮 {interaction.user.mention} さんの運勢は **{res}** です！")

@bot.tree.command(name="timer", description="指定秒数後に通知します")
async def timer(interaction: discord.Interaction, 秒: int):
    await interaction.response.send_message(f"⏰ {秒}秒のタイマーを開始。")
    await asyncio.sleep(秒)
    await interaction.channel.send(f"🔔 {interaction.user.mention} 時間になりました！")

@bot.tree.command(name="translate", description="文章を日本語に翻訳します")
async def translate(interaction: discord.Interaction, text: str):
    try:
        translated = GoogleTranslator(source='auto', target='ja').translate(text)
        await interaction.response.send_message(f"🌐 **翻訳結果**:\n{translated}")
    except:
        await interaction.response.send_message("翻訳に失敗しました。", ephemeral=True)

@bot.tree.command(name="verify", description="サーバーの認証（ロール付与）を行います")
async def verify(interaction: discord.Interaction):
    if interaction.channel_id != CH_IDS["verify"]:
        return await interaction.response.send_message("専用の認証チャンネルで使ってください。", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Member")
    if role:
        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ 認証完了！ロールを付与しました。", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 'Member'ロールが見つかりません。", ephemeral=True)

# 管理者用：強制コマンド同期 (!sync)
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ スラッシュコマンドを同期しました。")

# --- 5. 実行処理 ---
if __name__ == "__main__":
    t = threading.Thread(target=run_web, daemon=True)
    t.start()
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ トークンが見つかりません。")
