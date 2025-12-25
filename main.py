import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import random
from flask import Flask
from threading import Thread

# --- [1. Render用 Webサーバー] ---
# Renderは外部からのアクセス（ポート8080）がないとスリープするため必須です
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Renderのポート指定に対応
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- [2. 設定の読み込み] ---
TOKEN = os.getenv("DISCORD_TOKEN")

def get_ch_id(key):
    val = os.getenv(key)
    return int(val) if val and val.isdigit() else None

# --- [3. Botの基本設定] ---
intents = discord.Intents.all()
# コマンドの開始文字を「!」に設定
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ ログインしました: {bot.user.name}')
    # 定期実行タスクの開始
    if not daily_schedule.is_running():
        daily_schedule.start()

# --- [4. 定期通知 (ニュース・挨拶)] ---
@tasks.loop(seconds=60)
async def daily_schedule():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%H:%M')
    
    if now == "08:00":
        ch = bot.get_channel(get_ch_id("CH_NEWS"))
        if ch: await ch.send("📢 **朝の通知**\n☀️【全国天気】晴れのち曇り\n📰【ニュース】最新情報をチェックしましょう！")

    if now == "12:00":
        ch = bot.get_channel(get_ch_id("CH_GREETING"))
        if ch: await ch.send("🍱 12:00です。お昼休みですよ！")

# --- [5. コマンド機能] ---

@bot.command(name="おみくじ")
async def omikuji(ctx):
    # 環境変数で指定したチャンネルのみで反応
    if ctx.channel.id == get_ch_id("CH_ENTAME"):
        res = random.choice(["大吉", "中吉", "小吉", "吉", "凶"])
        await ctx.send(f"🔮 {ctx.author.mention} さんの運勢は **{res}** です！")

@bot.command(name="タイマー")
async def timer(ctx, sec: int):
    if ctx.channel.id == get_ch_id("CH_TIMER"):
        await ctx.send(f"⏰ {sec}秒のタイマーを開始します。")
        await asyncio.sleep(sec)
        await ctx.send(f"🔔 {ctx.author.mention} 時間になりました！")

@bot.command(name="認証")
async def verify(ctx):
    if ctx.channel.id == get_ch_id("CH_VERIFY"):
        role = discord.utils.get(ctx.guild.roles, name="認証済み")
        if role:
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ {ctx.author.mention} 認証が完了し、ロールを付与しました。")
        else:
            await ctx.send("⚠️ 「認証済み」という名前のロールが見つかりません。サーバー設定で作ってください。")

@bot.command(name="おすすめ動画")
async def youtube_notify(ctx):
    ch = bot.get_channel(get_ch_id("CH_YOUTUBE"))
    if ch:
        await ch.send("🎥 本日のおすすめ動画はこちら！\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ")

# --- [6. イベント監視] ---

@bot.event
async def on_voice_state_update(member, before, after):
    log_ch = bot.get_channel(get_ch_id("CH_LOG"))
    if not log_ch: return
    if before.channel is None and after.channel is not None:
        await log_ch.send(f"🔊 {member.name} が `{after.channel.name}` に入室。")
    elif before.channel is not None and after.channel is None:
        await log_ch.send(f"🔇 {member.name} が退出。")

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # NGワード削除
    NG_WORDS = ["禁止語1", "禁止語2"]
    if any(w in message.content for w in NG_WORDS):
        await message.delete()
        ch = bot.get_channel(get_ch_id("CH_GUARD"))
        if ch: await ch.send(f"⚠️ {message.author.mention} が禁止用語を使用。10分ミュート。")
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        await message.author.timeout(until)

    # これがないとコマンド(!おみくじ等)が動かなくなる
    await bot.process_commands(message)

# --- [7. 起動] ---
keep_alive() # Webサーバーを先に起動
try:
    bot.run(TOKEN)
except Exception as e:
    print(f"❌ エラーが発生しました: {e}")
