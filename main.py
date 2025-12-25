import discord
from discord.ext import commands, tasks
import datetime
import random
import asyncio
import requests
from flask import Flask
from threading import Thread

# --- [設定エリア] ---
TOKEN = "YOUR_BOT_TOKEN_HERE" # Discordのトークン
NEWS_CHANNEL_ID = 123456789   # ニュース・天気用
LOG_CHANNEL_ID = 123456789    # 管理ログ用
VERIFY_CHANNEL_ID = 123456789 # 認証用
NG_WORDS = ["禁止用語1", "禁止用語2"]

# --- [Render用のWebサーバー設定] ---
app = Flask('')
@app.route('/')
def home(): return "Bot is running!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- [Bot本体の設定] ---
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- [機能実装] ---

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    daily_tasks.start()
    keep_alive() # Webサーバー起動

# 1, 2, 4. 定期実行 (ニュース・天気・挨拶)
@tasks.loop(minutes=1)
async def daily_tasks():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%H:%M')
    channel = bot.get_channel(NEWS_CHANNEL_ID)
    if not channel: return

    if now == "08:00":
        # 本来はAPIを叩きますが、ここでは簡易化
        await channel.send("☀️ 8:00です！【全国天気】東京:☀️ 大阪:☁️ 福岡:☔... \n📰 【ニュース】最新のヘッドラインをお届けします。")
    elif now == "12:00":
        await channel.send("🍱 12:00になりました。お昼休憩の時間です！")

# 5. VC入退室ログ
@bot.event
async def on_voice_state_update(member, before, after):
    log_ch = bot.get_channel(LOG_CHANNEL_ID)
    if before.channel is None and after.channel is not None:
        await log_ch.send(f"🔊 {member.name} が {after.channel.name} に参加しました。")
    elif before.channel is not None and after.channel is None:
        await log_ch.send(f"🔇 {member.name} が退出しました。")

# 6. 自動守護 (NGワード削除 & ミュート)
@bot.event
async def on_message(message):
    if message.author.bot: return
    if any(word in message.content for word in NG_WORDS):
        await message.delete()
        await message.channel.send(f"{message.author.mention} 不適切な言葉を検知しました。", delete_after=5)
        # 簡易ミュート（権限が必要）
        timeout_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
        await message.author.timeout(timeout_until, reason="NGワード使用")
    await bot.process_commands(message)

# 7, 9, 10. エンタメ・ツール系コマンド
@bot.command()
async def おみくじ(ctx):
    results = ["大吉", "中吉", "小吉", "吉", "凶"]
    await ctx.send(f"🔮 結果は... **{random.choice(results)}** です！")

@bot.command()
async def タイマー(ctx, seconds: int):
    await ctx.send(f"⏰ {seconds}秒後に通知します。")
    await asyncio.sleep(seconds)
    await ctx.send(f"🔔 {ctx.author.mention} 時間になりました！")

# 8. 歓迎・離脱
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel: await channel.send(f"👋 {member.name}さん、いらっしゃいませ！")

# 13. 自動認証 (ボタン等でも作れますが簡易版)
@bot.command()
async def 認証(ctx):
    role = discord.utils.get(ctx.guild.roles, name="Member")
    await ctx.author.add_roles(role)
    await ctx.send("✅ 認証が完了し、ロールを付与しました。")

bot.run(TOKEN)
