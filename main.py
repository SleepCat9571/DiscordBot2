import discord
from discord.ext import commands, tasks
import datetime
import random
import asyncio
import os
from flask import Flask
from threading import Thread

# --- [1. 環境変数の読み込み] ---
# RenderのEnvironment Variablesから取得
TOKEN = os.getenv("DISCORD_TOKEN")

def get_ch(key):
    """環境変数からIDを読み込み、数値として返す"""
    value = os.getenv(key)
    return int(value) if value and value.isdigit() else None

# --- [2. Render用：スリープ防止サーバー] ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- [3. Bot基本設定] ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    daily_schedule.start()
    keep_alive()

# --- [4. 定期通知系 (ニュース/天気/挨拶)] ---
@tasks.loop(minutes=1)
async def daily_schedule():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%H:%M')
    
    # 08:00 ニュース＆天気
    if now == "08:00":
        ch_id = get_ch("CH_NEWS")
        ch = bot.get_channel(ch_id)
        if ch: await ch.send("📢 **朝の定期通知**\n☀️【全国天気】東京:晴 大阪:曇 福岡:雨\n📰【最新ニュース】本日注目のトピックをお届けします。")

    # 12:00 お昼休憩
    elif now == "12:00":
        ch_id = get_ch("CH_GREETING")
        ch = bot.get_channel(ch_id)
        if ch: await ch.send("🍱 12:00になりました。お昼休憩の時間です！")

# --- [5. イベント監視系] ---

# 管理ログ (VC入退室)
@bot.event
async def on_voice_state_update(member, before, after):
    ch_id = get_ch("CH_LOG")
    log_ch = bot.get_channel(ch_id)
    if not log_ch: return
    if before.channel is None and after.channel is not None:
        await log_ch.send(f"🔊 入室: {member.mention} が `{after.channel.name}` に入りました。")
    elif before.channel is not None and after.channel is None:
        await log_ch.send(f"🔇 退室: {member.mention} が `{before.channel.name}` から出ました。")

# 自動守護 (NGワード)
@bot.event
async def on_message(message):
    if message.author.bot: return
    NG_WORDS = ["禁止語1", "禁止語2"] # これも環境変数化可能
    if any(word in message.content for word in NG_WORDS):
        await message.delete()
        ch_id = get_ch("CH_GUARD")
        guard_ch = bot.get_channel(ch_id)
        if guard_ch: await guard_ch.send(f"⚠️ {message.author.mention} 禁止用語検知。10分ミュート。")
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        await message.author.timeout(until, reason="禁止用語使用")
    await bot.process_commands(message)

# 歓迎・離脱
@bot.event
async def on_member_join(member):
    ch_id = get_ch("CH_WELCOME")
    ch = bot.get_channel(ch_id)
    if ch: await ch.send(f"🎉 {member.mention} さん、いらっしゃいませ！")

# --- [6. コマンド系] ---

@bot.command()
async def おみくじ(ctx):
    if ctx.channel.id != get_ch("CH_ENTAME"): return
    res = random.choice(["大吉", "中吉", "小吉", "末吉", "凶"])
    await ctx.send(f"🔮 {ctx.author.mention} さんの運勢は **{res}** です！")

@bot.command()
async def タイマー(ctx, sec: int):
    if ctx.channel.id != get_ch("CH_TIMER"): return
    await ctx.send(f"⏰ {sec}秒のタイマーを開始。")
    await asyncio.sleep(sec)
    await ctx.send(f"🔔 {ctx.author.mention} 時間になりました！")

@bot.command()
async def 認証(ctx):
    if ctx.channel.id != get_ch("CH_VERIFY"): return
    role = discord.utils.get(ctx.guild.roles, name="認証済み")
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ {ctx.author.mention} 認証完了。")

@bot.command()
async def おすすめ動画(ctx):
    ch_id = get_ch("CH_YOUTUBE")
    ch = bot.get_channel(ch_id)
    if ch: await ch.send("🎥 本日のおすすめ： https://www.youtube.com/watch?v=dQw4w9WgXcQ")

bot.run(TOKEN)
