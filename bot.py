# bot.py
import discord
from discord.ext import commands
import os, json, asyncio
from dotenv import load_dotenv
from keep_alive import keep_alive


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
keep_alive()
DATA_FILE = "reaction_roles.json"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

def load_data():
    if not os.path.isfile(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@commands.has_permissions(manage_roles=True)
@bot.command(name="rr_create")
async def rr_create(ctx, channel: discord.TextChannel, *, message_text: str):
    msg = await channel.send(message_text)
    data = load_data()
    data[str(msg.id)] = {"channel_id": channel.id, "map": {}}
    save_data(data)
    await ctx.send(f"Đã tạo reaction-role message: `{msg.id}` ở {channel.mention}.\nThêm mapping: `!rr_add {msg.id} emoji @Role`")

@commands.has_permissions(manage_roles=True)
@bot.command(name="rr_add")
async def rr_add(ctx, message_id: int, emoji: str, role: discord.Role):
    data = load_data()
    sid = str(message_id)
    if sid not in data:
        await ctx.send("Message ID không tồn tại. Dùng `!rr_create` trước.")
        return
    channel = bot.get_channel(data[sid]["channel_id"])
    try:
        message = await channel.fetch_message(message_id)
    except Exception as e:
        await ctx.send(f"Không lấy được message: {e}")
        return

    data[sid]["map"][emoji] = role.id
    save_data(data)

    try:
        await message.add_reaction(emoji)
        await asyncio.sleep(0.4)
    except Exception as e:
        await ctx.send(f"Không thể thêm reaction `{emoji}` — lỗi: {e}")
        return
    await ctx.send(f"Đã map {emoji} → {role.mention} cho message `{message_id}`.")

@commands.has_permissions(manage_roles=True)
@bot.command(name="rr_remove")
async def rr_remove(ctx, message_id: int, emoji: str):
    data = load_data()
    sid = str(message_id)
    if sid not in data or emoji not in data[sid]["map"]:
        await ctx.send("Mapping không tồn tại.")
        return
    del data[sid]["map"][emoji]
    save_data(data)
    await ctx.send(f"Đã xóa mapping {emoji} cho message {message_id}.")

@commands.has_permissions(manage_roles=True)
@bot.command(name="rr_list")
async def rr_list(ctx):
    data = load_data()
    if not data:
        await ctx.send("Chưa có reaction-role nào.")
        return
    lines = []
    for mid, info in data.items():
        ch = bot.get_channel(info['channel_id'])
        pairs = ", ".join(f"{k} → <@&{v}>" for k, v in info['map'].items()) or "(chưa mapping)"
        lines.append(f"Message `{mid}` in {ch.mention if ch else info['channel_id']}: {pairs}")
    msg = "\n".join(lines)
    if len(msg) > 1900:
        await ctx.send("Danh sách quá dài.")
    else:
        await ctx.send(msg)

@bot.event
async def on_raw_reaction_add(payload):
    data = load_data()
    sid = str(payload.message_id)
    if sid not in data:
        return
    emoji_key = str(payload.emoji)
    mapping = data[sid]["map"]
    if emoji_key not in mapping:
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    role = guild.get_role(mapping[emoji_key])
    if role is None:
        return
    member = payload.member or await guild.fetch_member(payload.user_id)
    if member is None:
        return
    try:
        await member.add_roles(role, reason="Reaction role assigned")
    except Exception as e:
        print("Failed to add role:", e)

@bot.event
async def on_raw_reaction_remove(payload):
    data = load_data()
    sid = str(payload.message_id)
    if sid not in data:
        return
    emoji_key = str(payload.emoji)
    mapping = data[sid]["map"]
    if emoji_key not in mapping:
        return
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return
    role = guild.get_role(mapping[emoji_key])
    if role is None:
        return
    try:
        member = await guild.fetch_member(payload.user_id)
    except Exception:
        member = None
    if member is None:
        return
    try:
        await member.remove_roles(role, reason="Reaction role removed")
    except Exception as e:
        print("Failed to remove role:", e)

if __name__ == "__main__":
    if not TOKEN:
        print("Vui lòng đặt DISCORD_TOKEN trong .env")
    else:
        bot.run(os.getenv("DISCORD_TOKEN"))
