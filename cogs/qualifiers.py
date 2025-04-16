import discord
from discord import app_commands, Embed
from discord.ext import commands, tasks
from utils.google_sheets import get_worksheet, update_sheet, create_lobby, get_lobbies, claim_referee, drop_referee, get_claimed_lobbies, fetch_pings
from datetime import datetime
import pytz
import io
import os
import csv

def get_team_from_csv(user_id):
    """Reads the CSV file and returns the team associated with the user_id."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the script
        parent_dir = os.path.dirname(current_dir)  # Go up one directory
        file_path = os.path.join(parent_dir, 'MBB7teams.csv')  # Path to the CSV file

        with open(file_path, mode='r') as file:
            # Manually specify the column names since there are no headers
            reader = csv.DictReader(file, fieldnames=['id', 'team'])

            for row in reader:
                print(f"Row data: {row}")  # Print each row to inspect the data
                if str(row['id']) == str(user_id):  # Ensure both IDs are treated as strings
                    return row['team']  # Return the corresponding team name

        return None  # Return None if the user ID is not found
    except Exception as e:
        print(f"⚠️ Error reading CSV file: {e}")
        return None
    
class Qualifiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_lobbies.start()

    @app_commands.command(name="qrules", description="Displays the qualifiers rules")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def qrules(self, interaction: discord.Interaction):
        embed = Embed(title="Qualifiers Rules", description="Please follow these rules to ensure a smooth run of the qualifiers stage", color=0x1ABC9C)
        embed.add_field(name="📝 Scheduling Rules", value="- Only **the captain** of the team can schedule their lobby *(for emergencies contact a member of the admin team)*\n- Each team can sign up for any existing lobby **before it's start time**\n- Custom lobbies **must** be scheduled **at least 6h before the lobby time** *(exceptions can be made if there's a referee able to take the lobby)*", inline=False)
        embed.add_field(name="⚔ Qualifiers Procedure", value="- Every team will be notified about their lobby **15 minutes prior to the lobby start time**\n- Every team will have **one try** to play the qualifiers\n- Qualifiers mappool will consist of **4xNM, 2xHD, 2xHR and 2xDT**, played in order **beginning with NM1 and ending with DT2**\n- If a player disconnects during a map **due to a technical issue**, they’re allowed to replay the map **once**\n- Teams that are **more than 5 minutes late** to their qualifier lobby **will be asked to reschedule**", inline=False)
        embed.add_field(name="📌 Useful Links", value="- [Main Sheet](https://docs.google.com/spreadsheets/d/1e-PgHx_fx-aqo_J1M17ekpshO72Ldnilr5QYZJ4X7RU)\n- [Full Rulebook](https://docs.google.com/document/d/1HSZA4_OCpGjgmlVCrxvNT70ANSWaaxup9FLUGoATqoQ)", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="qsched", description="Schedule your team for a qualifiers lobby.")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def schedule_qualifiers(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for scheduling a qualifiers lobby using the user's team from a CSV file."""

        # Get the user's team based on their user ID from the CSV file
        team = get_team_from_csv(interaction.user.id)

        if not team:
            await interaction.response.send_message("❌ Only captains can schedule qualifier lobbies. For urgent matters please reach out to an admin.", ephemeral=True)
            return

        await interaction.response.defer()

        success, error_msg = update_sheet(team, lobby_id)

        if success:
            # Create an embedded success message
            embed = Embed(
                title=f"✅ {team} Scheduled",
                description=f"Team {team} has successfully scheduled for lobby {lobby_id}.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)
        else:
            # Send an ephemeral error message and delete the deferred message
            await interaction.delete_original_response()  # Delete the deferred response
            await interaction.followup.send(f"❌ Scheduling failed: {error_msg} For urgent matters, please reach out to an admin.", ephemeral=True)

    @app_commands.command(name="qmake", description="Create custom qualifiers lobby.")
    @app_commands.describe(
        date="m/d/yy",
        time="hh:mm"
    )
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def make_qualifiers(self, interaction: discord.Interaction, date: str, time: str):
        """Slash command for creating a new qualifiers lobby."""

        # Define the role IDs you want to check
        role_ids = [1162844846478864544, 1164991967302783037]  # Allowed roles

        # Check if the user has any of the roles or is in the CSV file
        if not any(role.id in role_ids for role in interaction.user.roles):
            # Check if the user is in the CSV by trying to get their team
            team = get_team_from_csv(interaction.user.id)
            if not team:  # If no team is returned, the user is not in the CSV file
                await interaction.response.send_message("❌ Only captains, admins, referees, or users listed in the CSV can create qualifier lobbies. For urgent matters please reach out to an admin", ephemeral=True)
                return

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
            await interaction.followup.send(f"❌ Lobby creation failed: {error_msg} For urgent matters, please reach out to an admin.", ephemeral=True)

    @app_commands.command(name="lobbies", description="List upcoming qualifiers lobbies based on conditions.")
    @app_commands.describe(condition="referee=empty for lobbies without a referee | referee=needed for lobbies with at least 1 team without referee | free for lobbies with free team slot")
    @commands.cooldown(1, 1.0, commands.BucketType.default)
    async def list_lobbies(self, interaction: discord.Interaction, condition: str):
        """Lists upcoming qualifiers lobbies based on user input ('empty' or 'free')."""
        await interaction.response.defer()

        # Validate the condition input
        if condition not in ["referee=empty","referee=needed", "free"]:
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

        embed = discord.Embed(title=f"Upcoming Lobbies ({condition.capitalize()})", color=0x1ABC9C)
        embed.description = "Times are in **your local timezone**"

        for lobby_id, timestamp in displayed_lobbies:
            print(f"Lobby found: {lobby_id}")  # Logging for debugging
            embed.add_field(name=f"• {lobby_id}", value=f"{timestamp}", inline=False)

        if extra_count > 0:
            embed.set_footer(text=f"+ {extra_count} more lobbies match this condition")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="qclaim", description="Claim a qualifiers lobby as a referee.")
    @commands.has_role(1162844846478864544)
    @commands.cooldown(1, 1.0, commands.BucketType.default)
    async def claim_lobby(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for claiming a lobby as a referee."""

        if not any(role.id == 1162844846478864544 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return
        await interaction.defer()
        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username
        discord_id = interaction.user.id

        success, error_msg = claim_referee(lobby_id, discord_id)

        if success:
            embedmsg = Embed(
                title=f"✅ Lobby {lobby_id} Claimed",
                description=f"{discord_nickname} has successfully claimed lobby {lobby_id} as the referee.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embedmsg)
        else:
            await interaction.delete_original_response()
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)

    @app_commands.command(name="qdrop", description="Drop your claim as a referee for a qualifiers lobby.")
    @commands.has_role(1162844846478864544)  # Only users with the referee role can use this
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def drop_lobby(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for dropping a referee claim on a lobby."""

        # Check if the user has the correct role
        if not any(role.id == 1162844846478864544 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return
        await interaction.response.defer()
        
        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username
        discord_id = interaction.user.id

        success, error_msg = drop_referee(lobby_id, discord_id)

        if success:
            # Create an embedded success message for dropping the lobby
            embedmsg = Embed(
                title=f"✅ Lobby {lobby_id} Dropped",
                description=f"{discord_nickname} has successfully dropped their claim on lobby {lobby_id}.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embedmsg)
        else:
            await interaction.delete_original_response()
            await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)

    @app_commands.command(name="qclaimed", description="List the lobbies claimed by a referee.")
    @commands.has_role(1162844846478864544)  # Only users with the referee role can use this
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def claimed_lobbies(self, interaction: discord.Interaction):
        """Slash command for listing lobbies claimed by the referee."""
        
        # Check if the user has the correct role
        if not any(role.id == 1162844846478864544 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return
        
        await interaction.response.defer()

        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username
        discord_id = interaction.user.id

        # Get the list of claimed lobbies
        claimed_lobbies = get_claimed_lobbies(discord_id)

        if not claimed_lobbies:
            await interaction.followup.send(f"❌ No claimed lobbies found for {discord_nickname}.", ephemeral=True)
            return

        # Prepare the embed message
        embed = discord.Embed(title=f"Claimed Lobbies by {discord_nickname}", color=0x1ABC9C)
        embed.description = "These are the lobbies you have claimed that are still upcoming."

        for lobby_id, timestamp in claimed_lobbies:
            embed.add_field(name=f"• {lobby_id}", value=f"{timestamp}", inline=False)

        await interaction.followup.send(embed=embed)

    @tasks.loop(minutes=1)  # Runs every minute
    async def check_lobbies(self):
        print("checking")
        worksheet = get_worksheet()  # Get the Google Sheet
        rows = worksheet.get_all_values()[1:60]  # Fetch all rows from the sheet

        # Loop through each row and check if column 'S' has a number <= 15
        for row in rows:
            try:
                lobby_id = row[7]  # Column H is index 7 (starting from 0) for the lobby ID
                time_left = int(row[18])  # Column S is index 18 (starting from 0)
                pinged_status = int(row[19])  # Column T is index 19 (starting from 0)

                print(f"id:{lobby_id} in {time_left}")

                # Skip if time_left is -727
                if time_left < 0:
                    print("finished/empty lobby")
                    continue  # Skip if time left cell is -727

                # Check if the time left is <= 15 minutes and T column is 0 (not pinged yet)
                if time_left <= 15 and pinged_status == 0:
                    inviter_id, team_cap_ids = fetch_pings(lobby_id)  # Returns Discord user IDs

                    if not team_cap_ids:
                        continue

                    # Mention inviter directly
                    inviter_text = f"<@{inviter_id}>" if inviter_id else "No referee <@&1162844846478864544> please help"

                    # Mention each team captain directly
                    role_mentions = [f"<@{cap_id}>" for cap_id in team_cap_ids]

                    if not role_mentions:
                        continue

                    role_ping_text = " ".join(role_mentions)


                    message = f"{role_ping_text} Your qualifiers lobby: **{lobby_id}** starts soon, the referee for this lobby will be: {inviter_text}"

                    # Send the ping to the channel
                    channel = self.bot.get_channel(1160278434820411486)
                    if channel:
                        await channel.send(message, allowed_mentions=discord.AllowedMentions(roles=True, users=True))

                    # After sending the ping, increment the value in the T column
                    row_index = rows.index(row) + 2  # Calculate the correct row number
                    worksheet.update_cell(row_index, 20, 1)  # Column T is 20th, row_index is 1-based

            except Exception as e:
                print(f"Error checking lobby {lobby_id}: {e}")

    @check_lobbies.before_loop
    async def before_check_lobbies(self):
        # Wait until the bot is fully ready before starting the task
        await self.bot.wait_until_ready()



    @app_commands.command(name="get_users", description="Get all users in the guild and their IDs in a CSV format.")
    async def get_users(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not any(role.id == 1160286790498930759 for role in interaction.user.roles):
            await interaction.response.send_message("❌ You don't have permissions to use this command", ephemeral=True)
            return

        guild = interaction.guild
        await guild.chunk()

        print(f"Cached members: {len(guild.members)}")

        # Prepare CSV data
        csv_data = io.StringIO()
        csv_writer = csv.writer(csv_data)

        # Write header
        csv_writer.writerow(["Username", "ID"])

        # Write each member's username and ID
        for member in guild.members:
            csv_writer.writerow([f"{member.name}#{member.discriminator}", member.id])

        # Prepare the CSV file to send
        csv_data.seek(0)  # Reset pointer to the beginning of the StringIO buffer
        output_file = discord.File(fp=csv_data, filename="users.csv")

        # Send the CSV file as a response
        await interaction.followup.send(content="Here's the CSV file with all users and their IDs:", file=output_file)


async def setup(bot):
    await bot.add_cog(Qualifiers(bot))
