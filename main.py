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

# --- 1. 設定（環境変数） ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
# チャンネルIDを辞書で管理（設定がない場合はNone）
def get_env_id(key):
    val = os.getenv(key)
    return int(val) if val and val.isdigit() else None

CHANNELS = {
    "news": get_env_id("CH_NEWS"),
    "greeting": get_env_id("CH_GREETING"),
    "log": get_env_id("CH_LOG"),
    "welcome": get_env_id("CH_WELCOME"),
    "guard": get_env_id("CH_GUARD"),
    "youtube": get_env_id("CH_YOUTUBE"),
    "verify": get_env_id("CH_VERIFY"),
}

BAD_WORDS = ["死ね", "殺す", "バカ", "ゴミ", "カス"]
WEATHER_AREAS = {"東京": "130000", "大阪": "270000", "福岡": "400000", "札幌": "016000"}

# --- 2. Flask（Renderのスリープ防止用） ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_web():
    # Renderが指定するポートで起動
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- 3. ボットクラス定義 ---
class MyBot(commands.Bot):
    def __init__(self):
        # 全てのインテントを有効化（Developer Portalでの設定も忘れずに）
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # 起動時にスラッシュコマンドをDiscordに同期
        print("🔄 スラッシュコマンドを同期中...")
        await self.tree.sync()
        self.scheduled_task.start()

    async def on_ready(self):
        print(f"✅ ログイン成功: {self.user.name}")

    # --- 定期タスク (08:00天気 / 12:00挨拶) ---
    @tasks.loop(seconds=60)
    async def scheduled_task(self):
        jst = timezone(timedelta(hours=9), 'JST')
        now = datetime.now(jst)
        current_time = now.strftime('%H:%M')

        # 朝 08:00 天気通知
        if current_time == "08:00":
            ch = self.get_channel(CHANNELS["news"])
            if ch:
                msg = "🌅 **朝の全国天気予報**\n"
                for area, code in WEATHER_AREAS.items():
                    try:
                        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{code}.json"
                        res = requests.get(url).json()
                        w = res[0]['timeSeries'][0]['areas'][0]['weathers'][0]
                        msg += f"・{area}: {w}\n"
                    except: msg += f"・{area}: 取得失敗\n"
                await ch.send(msg)

        # 昼 12:00 挨拶
        if current_time == "12:00":
            ch = self.get_channel(CHANNELS["greeting"])
            if ch: await ch.send("🍱 12:00になりました。お昼休憩にしましょう！")

bot = MyBot()

# --- 4. イベント処理 ---

# 歓迎メッセージ
@bot.event
async def on_member_join(member):
    ch = bot.get_channel(CHANNELS["welcome"])
    if ch: await ch.send(f"🎊 {member.mention} さん、サーバーへようこそ！")

# VC入退室ログ
@bot.event
async def on_voice_state_update(member, before, after):
    ch = bot.get_channel(CHANNELS["log"])
    if not ch: return
    if before.channel is None and after.channel is not None:
        await ch.send(f"🎤 **{member.display_name}** が `{after.channel.name}` に参加")
    elif before.channel is not None and after.channel is None:
        await ch.send(f"👋 **{member.display_name}** が退出")

# 禁止用語監視
@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in BAD_WORDS):
        try:
            await message.delete()
            # 10分間ミュート（タイムアウト権限が必要）
            await message.author.timeout(timedelta(minutes=10), reason="禁止用語使用")
            log = bot.get_channel(CHANNELS["guard"])
            if log: await log.send(f"🛡️ {message.author.mention} を禁止用語使用で10分ミュートしました。")
        except Exception as e: print(f"Guard Error: {e}")
    
    # テキストコマンド (!syncなど) を有効にするために必要
    await bot.process_commands(message)

# --- 5. スラッシュコマンド ---

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
    if interaction.channel_id != CHANNELS["verify"]:
        return await interaction.response.send_message("専用の認証チャンネルで使ってください。", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Member") # ロール名
    if role:
        await interaction.user.add_roles(role)
        await interaction.response.send_message("✅ 認証完了！ロールを付与しました。", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 'Member'ロールが見つかりません。", ephemeral=True)

# 管理者用：強制コマンド同期
@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("✅ スラッシュコマンドを同期しました。")

# --- 6. 起動処理 ---
if __name__ == "__main__":
    # Webサーバーを別スレッドで起動
    t = threading.Thread(target=run_web, daemon=True)
    t.start()

    # Botをメインスレッドで起動
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ DISCORD_BOT_TOKEN が設定されていません。")
