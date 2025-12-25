import discord
from discord.ext import commands, tasks
import datetime
import asyncio
import os
import random
from flask import Flask
from threading import Thread

# --- [1. Render用 Webサーバー] ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Online!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- [2. 設定の読み込み] ---
TOKEN = os.getenv("DISCORD_TOKEN")

def get_ch_id(key):
    val = os.getenv(key)
    # 環境変数が設定されていない場合や空の場合は None を返す
    if not val or not val.isdigit():
        return None
    return int(val)

# --- [3. Botの基本設定] ---
intents = discord.Intents.all()
# コマンドの開始文字を「!」に設定
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ ログイン成功: {bot.user.name}')
    if not daily_schedule.is_running():
        daily_schedule.start()

# --- [4. コマンド機能] ---
# チャンネル制限を外し、どこでも実行できるようにしました

@bot.command(name="おみくじ")
async def omikuji(ctx):
    res = random.choice(["大吉", "中吉", "小吉", "吉", "凶"])
    await ctx.send(f"🔮 {ctx.author.mention} さんの運勢は **{res}** です！")

@bot.command(name="タイマー")
async def timer(ctx, sec: int):
    await ctx.send(f"⏰ {sec}秒のタイマーを開始します。")
    await asyncio.sleep(sec)
    await ctx.send(f"🔔 {ctx.author.mention} 時間になりました！")

@bot.command(name="認証")
async def verify(ctx):
    role_name = "認証済み" # サーバーで作ったロール名に合わせてください
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ {ctx.author.mention} にロール `{role_name}` を付与しました。")
    else:
        await ctx.send(f"⚠️ `{role_name}` という名前のロールが見つかりません。")

# --- [5. 定期通知系] ---
@tasks.loop(seconds=60)
async def daily_schedule():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%H:%M')
    
    # ニュース・天気
    if now == "08:00":
        ch_id = get_ch_id("CH_NEWS")
        if ch_id:
            ch = bot.get_channel(ch_id)
            if ch: await ch.send("📢 **朝の通知**\n☀️【全国天気】晴れ\n📰 ニュースを確認してください。")

    # 挨拶
    if now == "12:00":
        ch_id = get_ch_id("CH_GREETING")
        if ch_id:
            ch = bot.get_channel(ch_id)
            if ch: await ch.send("🍱 12:00です。お昼休み！")

# --- [6. メッセージ監視（NGワードなど）] ---
@bot.event
async def on_message(message):
    # Bot自身のメッセージは無視
    if message.author.bot:
        return

    # NGワードチェック
    NG_WORDS = ["禁止語1", "禁止語2"]
    if any(w in message.content for w in NG_WORDS):
        await message.delete()
        ch_id = get_ch_id("CH_GUARD")
        if ch_id:
            ch = bot.get_channel(ch_id)
            if ch: await ch.send(f"⚠️ {message.author.mention} 禁止用語検知。")
        return # NGワードの場合はコマンド処理をさせない

    # 重要：これを書かないとコマンド(!おみくじ等)が反応しません
    await bot.process_commands(message)

# --- [7. 起動] ---
keep_alive()
bot.run(TOKEN)
