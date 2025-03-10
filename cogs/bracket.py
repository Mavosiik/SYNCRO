import discord
from discord import app_commands, Embed
from discord.ext import commands
# from utils.google_sheets import
from datetime import datetime
import pytz

class Bracket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #@app_commands.command(name="resched",description="Reschedule on of your matches")
    #@commands.cooldown(1, 1.0, commands.BucketType.default)
    #async def reschedule_match(self, interaction: discord.Interaction, lobby_id: str, date: str, time: str):
        #"""Slash command for rescheduling a match."""
        #await interaction.response.defer()  

    @app_commands.command(name="test", description="multi-module test")
    @commands.cooldown(1, 1.0,commands.BucketType.default)
    async def multitest(self, interaction: discord.Interaction):
        """Slash command to test if multi-module setup works correctly"""
        await interaction.response.send_message("Sup!")
        return
    
async def setup(bot):
    await bot.add_cog(Bracket(bot))