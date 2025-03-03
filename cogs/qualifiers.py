import discord
from discord import app_commands, Embed
from discord.ext import commands
from utils.google_sheets import update_sheet, create_lobby, get_lobbies, claim_referee, drop_referee
from datetime import datetime
import pytz

class Qualifiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="qsched", description="Schedule yourself for a qualifiers lobby.")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def schedule_qualifiers(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for scheduling a qualifiers lobby using the user's nickname."""
        await interaction.response.defer()

        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username

        success, error_msg = update_sheet(discord_nickname, lobby_id)

        if success:
            # Create an embedded success message
            embed = Embed(
                title=f"✅ {discord_nickname} Scheduled",
                description=f"{discord_nickname} has been successfully scheduled for lobby {lobby_id}.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            # Send an ephemeral error message and delete the deferred message
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send(f"❌ Scheduling failed: {error_msg}. For urgent matters, please reach out to an admin.", ephemeral=True)

    @app_commands.command(name="qmake", description="Create custom qualifiers lobby.")
    @app_commands.describe(
        date="m/d/yy",
        time="hh:mm"
    )
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
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

            # Create an embedded success message
            embed = Embed(
                title=f"✅ New Lobby {new_lobby_id} Created",
                description=f"A new lobby {new_lobby_id} has been created for {utc_time.strftime('%m/%d/%y')} at {utc_time.strftime('%H:%M')}. {discord_timestamp}",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            # Send an ephemeral error message and delete the deferred response
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send(f"❌ Lobby creation failed: {error_msg}. For urgent matters, please reach out to an admin.", ephemeral=True)

    @app_commands.command(name="lobbies", description="List upcoming qualifiers lobbies based on conditions.")
    @app_commands.describe(condition="referee=empty for lobbies without a referee | free for lobbies with free team slot")
    @commands.cooldown(1, 1.0, commands.BucketType.default)
    async def list_lobbies(self, interaction: discord.Interaction, condition: str):
        """Lists upcoming qualifiers lobbies based on user input ('empty' or 'free')."""
        await interaction.response.defer()

        # Validate the condition input
        if condition not in ["referee=empty", "free"]:
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send("❌ Invalid condition. Please use 'referee=empty' for no referee or 'free' for at least one empty team slot.", ephemeral=True)
            return

        lobbies = get_lobbies(condition)

        if not lobbies:
            await interaction.followup.send(f"❌ No upcoming lobbies found where the condition '{condition}' is met.")
            return

        max_display = 8
        displayed_lobbies = lobbies[:max_display]
        extra_count = len(lobbies) - max_display

        embed = discord.Embed(title=f"Upcoming Lobbies ({condition.capitalize()})", color=discord.Color.blue())
        embed.description = "Times are in **your local timezone**"

        for lobby_id, timestamp in displayed_lobbies:
            print(f"Lobby found: {lobby_id}")  # Logging for debugging
            embed.add_field(name=f"• {lobby_id}", value=f"{timestamp}", inline=False)

        if extra_count > 0:
            embed.set_footer(text=f"+ {extra_count} more lobbies match this condition")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="qclaim", description="Claim a qualifiers lobby as a referee.")
    @commands.has_role(1114173406628298872)  # Only users with the referee role can use this
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def claim_lobby(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for claiming a lobby as a referee."""
        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username

        success, error_msg = claim_referee(lobby_id, discord_nickname)

        if success:
            # Create an embedded success message for claiming the lobby
            embed = Embed(
                title=f"✅ Lobby {lobby_id} Claimed",
                description=f"{discord_nickname} has successfully claimed lobby {lobby_id} as the referee.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)

    @app_commands.command(name="qdrop", description="Drop your claim as a referee for a qualifiers lobby.")
    @commands.has_role(1114173406628298872)  # Only users with the referee role can use this
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def drop_lobby(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for dropping a referee claim on a lobby."""
        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username

        success, error_msg = drop_referee(lobby_id, discord_nickname)

        if success:
            # Create an embedded success message for dropping the lobby
            embed = Embed(
                title=f"✅ Lobby {lobby_id} Dropped",
                description=f"{discord_nickname} has successfully dropped their claim on lobby {lobby_id}.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Qualifiers(bot))
