import discord
from discord.ext import commands
import asyncio
from config import TOKEN

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

async def load_cogs():
    await bot.load_extension("cogs.qualifiers")  # Make sure "cogs" is a folder

@bot.event
async def on_ready():
    await bot.tree.sync()  # This syncs the slash commands
    print(f"Logged in as {bot.user}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

asyncio.run(main())
