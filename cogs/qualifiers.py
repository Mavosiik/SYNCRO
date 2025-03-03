import discord
from discord import app_commands
from discord.ext import commands
from utils.google_sheets import update_sheet, create_lobby
from datetime import datetime
import pytz

class Qualifiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="qsched", description="Schedule yourself for a qualifiers lobby.")
    async def schedule_qualifiers(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for scheduling a qualifiers lobby using the user's nickname."""
        await interaction.response.defer()

        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username

        success, error_msg = update_sheet(discord_nickname, lobby_id)

        if success:
            # Send an ephemeral follow-up message (visible only to the user)
            await interaction.followup.send(f"✅ {discord_nickname} has been successfully scheduled for lobby {lobby_id}.")
        else:
            # Send an ephemeral error message and delete the deferred message
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send(f"❌ Scheduling failed: {error_msg}. Please contact an admin for urgent scheduling assistance or if the issue persists.", ephemeral=True)

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
                await interaction.followup.send(f"❌ Invalid date or date format. Please use mm/dd/yy HH:MM.", ephemeral=True)
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
            # Send an ephemeral error message and delete the deferred response
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send(f"❌ Lobby creation failed: {error_msg}. For urgent matters, please reach out to an admin.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Qualifiers(bot))
