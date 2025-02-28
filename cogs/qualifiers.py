import discord
from discord import app_commands
from discord.ext import commands
from utils.google_sheets import update_sheet, create_lobby
from datetime import datetime
import pytz

class Qualifiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="qsched", description="Schedule a team for a qualifiers lobby.")
    async def schedule_qualifiers(self, interaction: discord.Interaction, team_name: str, lobby_id: str):
        """Slash command for scheduling a qualifiers lobby."""
        await interaction.response.defer()
        
        success, error_msg = update_sheet(team_name, lobby_id)
        
        if success:
            await interaction.followup.send(f"✅ {team_name} has been successfully scheduled for lobby {lobby_id}.")
        else:
            await interaction.followup.send(f"❌ Scheduling failed: {error_msg}. Please contact an admin if the issue persists.")
    
    @app_commands.command(name="qmake", description="Create custom qualifiers lobby.")
    async def make_qualifiers(self, interaction: discord.Interaction, date: str, time: str):
        """Slash command for creating a new qualifiers lobby."""
        await interaction.response.defer()
        
        new_lobby_id, error_msg = create_lobby(date, time)
        
        if new_lobby_id:
            # Convert the input date and time to a datetime object
            input_datetime_str = f"{date} {time}"
            
            try:
                input_datetime = datetime.strptime(input_datetime_str, "%m/%d/%y %H:%M")
            except ValueError:
                await interaction.followup.send(f"❌ Invalid date or date format. Please use mm/dd/yy HH:MM.")
                return

            # Check if the input time is already in UTC
            utc_time = input_datetime.replace(tzinfo=pytz.UTC)
            
            # Get the Unix timestamp for Discord
            timestamp = int(utc_time.timestamp())
            discord_timestamp = f"<t:{timestamp}:F>"  # Discord format for full date-time

            # Log the time for the console (use the same UTC time)
            print(f"✅ Created new lobby {new_lobby_id} on {utc_time.strftime('%m/%d/%y')} at {utc_time.strftime('%H:%M')}. Timestamp for Discord: {discord_timestamp}")

            # Send the success message with the Discord timestamp
            await interaction.followup.send(f"✅ New lobby {new_lobby_id} has been created for {utc_time.strftime('%m/%d/%y')} at {utc_time.strftime('%H:%M')}. {discord_timestamp}")
        else:
            # Provide more specific error message for failure to create a lobby
            await interaction.followup.send(f"❌ Lobby creation failed: {error_msg}. For urgent matters, please reach out to an admin.")

async def setup(bot):
    await bot.add_cog(Qualifiers(bot))
