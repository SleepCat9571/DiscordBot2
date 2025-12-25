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

# --- 1. 設定（環境変数から取得） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_IDS = {
    "news": int(os.getenv("CH_NEWS")) if os.getenv("CH_NEWS") else None,
    "greeting": int(os.getenv("CH_GREETING")) if os.getenv("CH_GREETING") else None,
    "log": int(os.getenv("CH_LOG")) if os.getenv("CH_LOG") else None,
    "welcome": int(os.getenv("CH_WELCOME")) if os.getenv("CH_WELCOME") else None,
    "guard": int(os.getenv("CH_GUARD")) if os.getenv("CH_GUARD") else None,
    "youtube": int(os.getenv("CH_YOUTUBE")) if os.getenv("CH_YOUTUBE") else None,
    "verify": int(os.getenv("CH_VERIFY")) if os.getenv("CH_VERIFY") else None,
}

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"] # 禁止用語
WEATHER_AREAS = {"東京": "130000", "大阪": "270000", "福岡": "400000", "札幌": "016000", "名古屋": "230000", "広島": "340000", "仙台": "040000"}

# --- 2. Flask（Render維持用） ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run_web(): app.run(host='0.0.0.0', port=8080)

# --- 3. ボットクラス定義 ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all() # 全ての権限を有効化
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # スラッシュコマンドの同期
        await self.tree.sync()
        self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ {self.user.name} 起動完了")

    # --- 定期タスク (ニュース・天気・挨拶) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')

        # 朝 08:00 の天気とニュース
        if current_time == "08:00":
            ch = self.get_channel(CH_IDS["news"])
            if ch:
                msg = "🌅 **朝の定期通知**\n\n【天気予報】\n"
                for area, code in WEATHER_AREAS.items():
                    try:
                        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                        res = requests.get(url).json()
                        w = res[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                        msg += f"・{area}: {w}\n"
                    except: msg += f"・{area}: 取得失敗\n"
                msg += "\n📰 今日のニュースをチェックしましょう！"
                await ch.send(msg)

        # 昼 12:00 の挨拶
        if current_time == "12:00":
            ch = self.get_channel(CH_IDS["greeting"])
            if ch: await ch.send("🍱 12時になりました。お昼休憩にしましょう！")

bot = MyBot()

# --- 4. イベント処理 ---

# 歓迎・離脱メッセージ
@bot.event
async def on_member_join(member):
    ch = bot.get_channel(CH_IDS["welcome"])
    if ch: await ch.send(f"🎊 {member.mention} さん、サーバーへようこそ！")

@bot.event
async def on_member_remove(member):
    ch = bot.get_channel(CH_IDS["welcome"])
    if ch: await ch.send(f"👋 {member.name} さんがサーバーを離れました。")

# 管理ログ (VC入退室)
@bot.event
async def on_voice_state_update(member, before, after):
    ch = bot.get_channel(CH_IDS["log"])
    if not ch: return
    if before.channel is None and after.channel is not None:
        await ch.send(f"🎤 **{member.display_name}** が **{after.channel.name}** に参加")
    elif before.channel is not None and after.channel is None:
        await ch.send(f"👋 **{member.display_name}** が退出")

# 自動守護 (NGワード監視)
@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.delete()
            await message.author.timeout(timedelta(minutes=10))
            log = bot.get_channel(CH_IDS["guard"])
            if log: await log.send(f"🛡️ {message.author.mention} を不適切発言で10分ミュートしました。")
        except: pass
    await bot.process_commands(message)

# --- 5. スラッシュコマンド（エンタメ・ツール） ---

@bot.tree.command(name="omikuji", description="今日のおみくじを引く")
async def omikuji(interaction: discord.Interaction):
    res = random.choice(["大吉", "中吉", "小吉", "末吉", "凶"])
    await interaction.response.send_message(f"🔮 運勢は... **{res}** です！")

@bot.tree.command(name="translate", description="文章を翻訳します")
async def translate(interaction: discord.Interaction, text: str, lang: str = "ja"):
    translated = GoogleTranslator(source='auto', target=lang).translate(text)
    await interaction.response.send_message(f"🌐 **翻訳結果 ({lang})**:\n{translated}")

@bot.tree.command(name="timer", description="指定した秒数後に通知します")
async def timer(interaction: discord.Interaction, seconds: int):
    await interaction.response.send_message(f"⏰ {seconds}秒後に通知します。")
    await asyncio.sleep(seconds)
    await interaction.channel.send(f"🔔 {interaction.user.mention} 時間になりました！")

@bot.tree.command(name="verify", description="サーバーの認証を行います")
async def verify(interaction: discord.Interaction):
    if interaction.channel_id != CH_IDS["verify"]:
        return await interaction.response.send_message("専用の認証チャンネルで実行してください。", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Member") # ロール名を指定
    if role:
        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ 認証が完了しました！", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ ロールが見つかりません。", ephemeral=True)

@bot.tree.command(name="youtube", description="おすすめ動画を通知")
async def youtube_suggest(interaction: discord.Interaction):
    ch = bot.get_channel(CH_IDS["youtube"])
    if ch:
        await ch.send("🎥 本日のおすすめ動画！\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ")
        await interaction.response.send_message("送信しました！", ephemeral=True)

# --- 6. 実行 ---
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    if TOKEN: bot.run(TOKEN)
