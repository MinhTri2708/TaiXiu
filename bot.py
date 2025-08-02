from keep_alive import keep_alive
keep_alive()
import discord
from discord.ext import commands
import json
import random
import asyncio
import os

# ==== Cấu hình ====
TOKEN = "MTQwMTEyNzA3OTgxMDE3NTA2OQ.GHMk_R.Vqmx5VLspDDE-F2aDJh54gUm7C_AYyI_AMlZL4"  # Thay bằng token bot của bạn
COIN_NAME = "VNĐ"                 # Tên tiền tệ
DEFAULT_BALANCE = 1000            # Số tiền mặc định khi người chơi mới
DATA_FILE = "players.json"        # File lưu dữ liệu
OWNER_ID = 1027094491598958612     # ID Discord của bạn
GAME_CHANNEL_ID = 1400656680282357900  # ID kênh chơi game
BET_TIME = 30                     # Thời gian cược mặc định (giây)
# ===================

# ==== Load/Lưu dữ liệu ====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_data()

def ensure_user(user_id):
    if str(user_id) not in users:
        users[str(user_id)] = DEFAULT_BALANCE
        save_data()

# ==== Khởi tạo bot ====
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

bets = {}
history = []
game_running = False

# ==== Vòng lặp game tự động ====
async def game_loop():
    global bets, game_running, BET_TIME
    await bot.wait_until_ready()
    channel = bot.get_channel(GAME_CHANNEL_ID)
    if channel is None:
        print("❌ Không tìm thấy kênh game! Kiểm tra GAME_CHANNEL_ID.")
        return
    while not bot.is_closed():
        bets = {}
        game_running = True
        await channel.send(embed=discord.Embed(
            title="🎲 Phiên Tài Xỉu bắt đầu!",
            description=f"Bạn có {BET_TIME} giây để đặt cược!\nDùng lệnh: `!dat tài|xỉu số_tiền`",
            color=0x00ff00
        ))
        await asyncio.sleep(BET_TIME - 10)
        await channel.send("⏳ Còn **10 giây** để đặt cược!")
        await asyncio.sleep(10)

        if not bets:
            await channel.send("❌ Không có ai đặt cược! Bắt đầu lại sau 3 giây...")
            game_running = False
            await asyncio.sleep(3)
            continue

        # Quay xúc xắc
        dice = [random.randint(1, 6) for _ in range(3)]
        total = sum(dice)
        result = "tài" if total >= 11 else "xỉu"
        history.append((dice, total, result))
        winners = []
        for user_id, (choice, amount) in bets.items():
            if choice == result:
                users[str(user_id)] += amount * 2
                winners.append(f"<@{user_id}> (+{amount} {COIN_NAME})")
        save_data()

        embed = discord.Embed(
            title="🎲 Kết quả phiên Tài Xỉu",
            description=f"**Xúc xắc:** {dice[0]} 🎲 {dice[1]} 🎲 {dice[2]}\n"
                        f"**Tổng:** {total} → **{result.upper()}**",
            color=0xffcc00
        )
        if winners:
            embed.add_field(name="🏆 Người thắng", value="\n".join(winners), inline=False)
        else:
            embed.add_field(name="💀 Không ai thắng", value="Không ai đoán đúng.", inline=False)
        await channel.send(embed=embed)

        game_running = False
        await asyncio.sleep(3)  # nghỉ trước khi mở phiên mới

# ==== Lệnh đặt cược ====
@bot.command()
async def dat(ctx, choice: str, amount: int):
    global bets, game_running
    ensure_user(ctx.author.id)
    choice = choice.lower()
    if not game_running:
        return await ctx.send("Hiện chưa có phiên cược nào!")
    if choice not in ["tài", "xỉu"]:
        return await ctx.send("Chọn `tài` hoặc `xỉu`!")
    if amount <= 0:
        return await ctx.send("Số tiền phải > 0!")
    if users[str(ctx.author.id)] < amount:
        return await ctx.send("Không đủ tiền!")
    users[str(ctx.author.id)] -= amount
    bets[ctx.author.id] = (choice, amount)
    save_data()
    await ctx.send(f"{ctx.author.mention} đã đặt {amount} {COIN_NAME} vào **{choice}**")

# ==== Lệnh xem số dư ====
@bot.command()
async def balance(ctx):
    ensure_user(ctx.author.id)
    await ctx.send(f"{ctx.author.mention} bạn có {users[str(ctx.author.id)]} {COIN_NAME}")

# ==== Lệnh chuyển tiền ====
@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    ensure_user(ctx.author.id)
    ensure_user(member.id)
    if amount <= 0:
        return await ctx.send("Số tiền phải > 0!")
    if users[str(ctx.author.id)] < amount:
        return await ctx.send("Không đủ tiền!")
    users[str(ctx.author.id)] -= amount
    users[str(member.id)] += amount
    save_data()
    await ctx.send(f"{ctx.author.mention} đã gửi {amount} {COIN_NAME} cho {member.mention}")

# ==== Lệnh cộng tiền (chỉ OWNER) ====
@bot.command()
async def addcoin(ctx, member: discord.Member, amount: int):
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Bạn không có quyền dùng lệnh này!")
    ensure_user(member.id)
    if amount <= 0:
        return await ctx.send("Số tiền phải > 0!")
    users[str(member.id)] += amount
    save_data()
    await ctx.send(f"Đã cộng {amount} {COIN_NAME} cho {member.mention}")

# ==== Lệnh top ====
@bot.command()
async def top(ctx):
    sorted_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
    top10 = sorted_users[:10]
    embed = discord.Embed(title=f"🏆 TOP Tỉ Phú {COIN_NAME}", color=0x00ffff)
    for i, (uid, coins) in enumerate(top10, 1):
        embed.add_field(name=f"{i}.", value=f"<@{uid}> - {coins} {COIN_NAME}", inline=False)
    await ctx.send(embed=embed)

# ==== Lệnh đặt lại thời gian cược (chỉ OWNER) ====
@bot.command()
async def settime(ctx, seconds: int):
    global BET_TIME
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Bạn không có quyền dùng lệnh này!")
    if seconds < 5:
        return await ctx.send("Thời gian phải >= 5 giây!")
    BET_TIME = seconds
    await ctx.send(f"⏳ Thời gian cược đã đặt thành {BET_TIME} giây.")

# ==== Lệnh xem lịch sử ====
@bot.command()
async def history_cmd(ctx):
    if not history:
        return await ctx.send("Chưa có lịch sử!")
    embed = discord.Embed(title="📜 Lịch sử Tài Xỉu", color=0xaaaaaa)
    for i, (dice, total, result) in enumerate(history[-5:], 1):
        embed.add_field(name=f"Phiên {i}", value=f"🎲 {dice} → {total} ({result.upper()})", inline=False)
    await ctx.send(embed=embed)

# ==== Chạy bot ====
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã sẵn sàng!")
    bot.loop.create_task(game_loop())

bot.run(TOKEN)
