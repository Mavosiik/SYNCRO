import discord
from discord import app_commands, Embed
from discord.ext import commands, tasks
from utils.google_sheets import get_worksheet, update_sheet, create_lobby, get_lobbies, claim_referee, drop_referee, get_claimed_lobbies, fetch_pings
from datetime import datetime
import pytz

class Qualifiers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_lobbies.start()

    @app_commands.command(name="qrules", description="Displays the qualifiers rules")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def qrules(self, interaction: discord.Interaction):
        embed = Embed(title="Qualifiers Rules", description="Please follow these rules to ensure a smooth run of the qualifiers stage", color=0x1ABC9C)
        embed.add_field(name="📝 Scheduling Rules", value="- Only **the captain** of the team can schedule their lobby *(for emergencies contact a member of the admin team)*\n- Each team can sign up for any existing lobby **before it's start time**\n- Custom lobbies **must** be scheduled **at least 6h before the lobby time** *(exceptions can be made if there's a referee able to take the lobby)*", inline=False)
        embed.add_field(name="⚔ Qualifiers Procedure", value="- Every team will be notified about their lobby 15 minutes prior to the lobby start time\n- Every team will have **one try** to play the qualifiers\n- Qualifiers mappool will consist of **4xNM, 2xHD, 2xHR, 2xDT and 1xEZ**, played in order **beginning with NM1 and ending with EZ1**\n- If a player disconnects during a map **due to a technical issue**, they’re allowed to replay the map **once**\n- Teams that are **more than 5 minutes late** to their qualifier lobby **will be asked to reschedule**", inline=False)
        embed.add_field(name="📌 Useful Links", value="- [Main Sheet](add_later)\n- [Full Rulebook](https://docs.google.com/document/d/1svb55MENQu1lbJIagna5RaCaAn_e2pkZBIHcgPQ9G5A)", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="qsched", description="Schedule your team for a qualifiers lobby.")
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def schedule_qualifiers(self, interaction: discord.Interaction, lobby_id: str):
        """Slash command for scheduling a qualifiers lobby using the user's lowest role (excluding @everyone)."""

        # Check if the user has the correct role
        if not any(role.id == 1344467503245557770 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only captains can schedule qualifier lobbies. For urgent matters please reach out to an admin.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get all roles excluding @everyone and find the lowest one
        roles = [role for role in interaction.user.roles if role.name != "@everyone"]
        if not roles:
            await interaction.followup.send("❌ You don't have any assignable roles.", ephemeral=True)
            return
        
        lowest_role = min(roles, key=lambda r: r.position)  # Get the lowest role by position
        role_name = lowest_role.name

        success, error_msg = update_sheet(role_name, lobby_id)

        if success:
            # Create an embedded success message
            embed = Embed(
                title=f"✅ {role_name} Scheduled",
                description=f"{role_name} has been successfully scheduled for lobby {lobby_id}.",
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
        role_ids = [1344467503245557770, 1114173406628298872, 1234974134744907989]  # Allowed roles

        # Check if the user has any of the roles
        if not any(role.id in role_ids for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only captains, admins and referees can create qualifier lobbies. For urgent matters please reach out to an admin", ephemeral=True)
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

        embed = discord.Embed(title=f"Upcoming Lobbies ({condition.capitalize()})", color=0x1ABC9C)
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

        # Check if the user has the correct role
        if not any(role.id == 1114173406628298872 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return

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

        # Check if the user has the correct role
        if not any(role.id == 1114173406628298872 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return
        
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

    @app_commands.command(name="qclaimed", description="List the lobbies claimed by a referee.")
    @commands.has_role(1114173406628298872)  # Only users with the referee role can use this
    @commands.cooldown(1, 1.0, commands.BucketType.default)  # Limit command activation to 1 time per second globally
    async def claimed_lobbies(self, interaction: discord.Interaction):
        """Slash command for listing lobbies claimed by the referee."""
        
        # Check if the user has the correct role
        if not any(role.id == 1114173406628298872 for role in interaction.user.roles):
            await interaction.response.send_message("❌ Only referees can claim qualifier lobbies", ephemeral=True)
            return
        
        await interaction.response.defer()

        discord_nickname = interaction.user.nick or interaction.user.name  # Use nickname if set, otherwise fallback to username

        # Get the list of claimed lobbies
        claimed_lobbies = get_claimed_lobbies(discord_nickname)

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
                    inviter_nickname, team_roles = fetch_pings(lobby_id)  # Use your existing fetch_pings function

                    if not team_roles:
                        continue

                    inviter = discord.utils.get(self.bot.guilds[0].members, display_name=inviter_nickname)

                    role_mentions = []
                    for role_name in team_roles:
                        role = discord.utils.get(self.bot.guilds[0].roles, name=role_name)
                        if role:
                            role_mentions.append(role.mention)

                    if not role_mentions:
                        continue

                    role_ping_text = " ".join(role_mentions)
                    inviter_text = inviter.mention if inviter else inviter_nickname

                    message = f"{role_ping_text} Your qualifiers lobby: **{lobby_id}** starts soon, the referee for this lobby will be {inviter_text}"

                    # Send the ping to the channel
                    channel = discord.utils.get(self.bot.guilds[0].text_channels, name="bot-testing")  # Change this to your target channel
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

async def setup(bot):
    await bot.add_cog(Qualifiers(bot))