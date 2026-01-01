import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # חשוב אם את רוצה לגשת למשתמשים

bot = commands.Bot(command_prefix="!", intents=intents)

load_dotenv()

GUILD_ID_STR = os.getenv("DISCORD_GUILD_ID")
GUILD_ID = int(GUILD_ID_STR) if GUILD_ID_STR else None  # Handle missing env var
DISCORD_URL = os.getenv("DISCORD_URL")

@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    print(f"Connected to guilds: {[g.name for g in bot.guilds]}")

def check_in_guild(discord_username):
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        raise ValueError("Bot is not in the guild or guild ID is wrong!")
    return discord.utils.get(guild.members, name=discord_username)

async def create_private_channel(discord_username_1, discord_username_2):
    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        raise ValueError("Bot is not in the guild or guild ID is wrong!")

    member1 = check_in_guild(discord_username_1)
    member2 = check_in_guild(discord_username_2)

    if member1 and member2:

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member1: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            member2: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel_name = f"{discord_username_1}-{discord_username_2}"
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        link = f"{DISCORD_URL}/channels/{guild.id}/{channel.id}"
        print(link)
        return link
    description = ""
    if not member1:
        description += f"{discord_username_1} not found in guild.\n"
    if not member2:
        description += f"{discord_username_2} not found in guild.\n"
    description += f"{discord_username_1} and {discord_username_2}, please go to {DISCORD_URL} and search for each other"
    return description


async def create_discord_event(title, description, meeting_link, start_time, end_time):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        raise ValueError("Bot not connected to guild or wrong guild ID")

    # צור אירוע חיצוני (external)
    event = await guild.create_scheduled_event(
        name=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        entity_type=discord.EntityType.external,
        location=meeting_link,  # לינק חיצוני לאתר שלך
        privacy_level=discord.PrivacyLevel.guild_only
    )

    print(f"Created event: {event.name} ({event.url})")
    return event.url