import discord
from discord import app_commands, Embed
from discord.ext import commands
# from utils.google_sheets import
from datetime import datetime
import pytz

class Bracket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="brules", description="Displays the bracket stage rules")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def qrules(self, interaction: discord.Interaction):
        embed = Embed(title="Bracket Stage Rules", description="Please follow these rules to ensure a smooth run of the bracket stage", color=0x1ABC9C)
        embed.add_field(name="📝 Scheduling Rules", value="- Only **the captain** of the team can reschedule their match *(for emergencies contact a member of the admin team)*\n- To reschedule a match use the **/reschedule command in the scheduling channel**\n- Reschedules for time **earlier than 6h before the desired time** may not be accepted", inline=False)
        embed.add_field(name="⚔ Match Procedure", value="- Every team will be notified about their match **15 minutes prior to the match start time**\n ", inline=False)
        embed.add_field(name="📌 Useful Links", value="- [Main Sheet](add_later)\n- [Full Rulebook](https://docs.google.com/document/d/1svb55MENQu1lbJIagna5RaCaAn_e2pkZBIHcgPQ9G5A)", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resschedule", description="Reschedule one of your matches.")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    @app_commands.describe(
        date="m/d/yy",
        time="hh:mm"
    )
    async def schedule_qualifiers(self, interaction: discord.Interaction, match_id: str, date: str, time: str):
        """Slash command for rescheduling a match limited to captain+team role."""

        # Check if the user has the correct role
        if not any(role.id == 1344467503245557770 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only captains can reschedule matches. For urgent matters please reach out to an admin", ephemeral=True)
            return
        
        await interaction.response.defer()

    
async def setup(bot):
    await bot.add_cog(Bracket(bot))