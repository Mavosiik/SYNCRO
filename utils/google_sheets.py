import gspread
from config import GOOGLE_SHEETS_CREDENTIALS
from datetime import datetime, timedelta
import pytz

gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS)
sheet = gc.open("SST3 Ref Sheet")

def update_sheet(discord_nickname, lobby_id):
    """Updates Google Sheets with the user’s scheduled lobby."""
    try:
        worksheet = sheet.worksheet("QSchedule")

        # Step 1: Try to find the old lobby the player is in (if there's one)
        old_lobby_cell = None  # Variable to store the old lobby cell if the user is found
        old_lobby_column = None  # Variable to store the column where the player is found
        for team_row_index, team_row in enumerate(worksheet.get_all_values(), start=1):  # Start from row 1 if data starts there
            for col in range(12, 17):  # Columns M (12) to Q (16)
                # Compare nickname with value in M-Q, removing extra spaces from both
                if discord_nickname.strip() == team_row[col - 1].strip():  # Strip any leading/trailing spaces
                    # Found the player's current cell in the old lobby, save it
                    print(f"Found {discord_nickname} in old lobby (row {team_row_index}, column {chr(col + 64)}).")
                    old_lobby_cell = f"{chr(col + 64)}{team_row_index}"  # Save the exact cell address (e.g., 'M5')
                    old_lobby_column = col  # Save the column for clearing
                    break  # Exit the loop once the player is found in the old lobby
            if old_lobby_cell:
                break  # Exit outer loop once the player is found

        # Step 2: Check if the lobby exists and retrieve necessary data
        cell = worksheet.find(lobby_id)
        if not cell:
            return False, "**Lobby not found.**"
        
        row = cell.row
        print(f"row {row}")
        date_cell = worksheet.cell(row, 9)
        time_cell = worksheet.cell(row, 10)
        current_datetime = datetime.now(pytz.UTC)

        try:
            # Parse date and time correctly
            date_value = datetime.strptime(date_cell.value, "%m/%d/%y").date()
            time_value = datetime.strptime(time_cell.value, "%H:%M").time()  # Parses 'HH:MM' format

            # Combine into a full datetime
            combined_datetime = datetime.combine(date_value, time_value).replace(tzinfo=pytz.UTC)

            # Compare to ensure it's not a past date/time
            if combined_datetime < current_datetime:
                return False, "**The scheduled time for this lobby is earlier than current time.**"

        except ValueError:
            return False, "**Invalid date or time format in the sheet.**"

        # Track if the user was added successfully to the new lobby
        added_to_new_lobby = False

        # Step 3: Try to find and update the new lobby
        team_cells = worksheet.range(f"M{row}:Q{row}")  # Ensure using the correct row value (row is dynamic)
        for cell in team_cells:
            if not cell.value:  # Find the first empty cell
                worksheet.update(cell.address, [[discord_nickname]])  # Update the cell with the user's nickname as a list
                added_to_new_lobby = True  # Set the flag to indicate the user was added
                break  # Exit the loop once added

        # Step 4: If the user was successfully added to the new lobby, now remove the player from the old lobby
        if added_to_new_lobby:
            # Step 5: Clear the old lobby cell if it exists
            if old_lobby_cell:
                # Clear the old lobby cell using batch_clear
                worksheet.batch_clear([old_lobby_cell])  # Clears the contents of the specified cell
                print(f"❌ Removed {discord_nickname} from old lobby: {old_lobby_cell}.")
            else:
                print(f"❌ No old lobby entry found for {discord_nickname}.")


            return True, None  # Return success after the update
        
        return False, "**Lobby not found or full.**"  # If the user wasn't added to the new lobby
        
    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return False, "An error occurred while updating the sheet."


def create_lobby(date, time):
    """Creates a new qualifiers lobby with the next available identifier."""
    try:
        input_datetime_str = f"{date} {time}"
        try:
            input_datetime = datetime.strptime(input_datetime_str, "%m/%d/%y %H:%M")
        except ValueError:
            return None, "**Invalid date or date format.** Please use mm/dd/yy HH:MM."
        
        input_datetime_utc = pytz.utc.localize(input_datetime)
        current_datetime = datetime.now(pytz.UTC)

        if input_datetime_utc < current_datetime + timedelta(hours=6):
            return None, "**The date must be at least 6 hours from the current time.**"
        
        start_date = datetime(2025, 3, 3, 12, 0, tzinfo=pytz.UTC)
        end_date = datetime(2025, 3, 12, 23, 0, tzinfo=pytz.UTC)
        
        if not (start_date <= input_datetime_utc <= end_date):
            return None, f"The date must be between** {start_date.strftime('%m/%d/%y %H:%M')} and {end_date.strftime('%m/%d/%y %H:%M')}.**"
        
        worksheet = sheet.worksheet("QSchedule")
        date_cells = worksheet.range("I2:I")  
        time_cells = worksheet.range("J2:J")  
        
        for date_cell, time_cell in zip(date_cells, time_cells):
            if date_cell.value == input_datetime.strftime("%m/%d/%y") and time_cell.value == time:
                row = date_cell.row
                team_cells = worksheet.range(f"M{row}:Q{row}")
                
                for team_cell in team_cells:
                    if not team_cell.value:
                        lobby_id = worksheet.cell(row, 8).value  
                        return None, f"**Lobby at this time already exists: {lobby_id}**"
        
        lobby_cells = worksheet.range("H2:H")
        last_lobby_number = 0
        for cell in lobby_cells:
            if cell.value and cell.value.startswith("X"):
                try:
                    lobby_num = int(cell.value[1:])
                    if lobby_num > last_lobby_number:
                        last_lobby_number = lobby_num
                except ValueError:
                    continue
        
        new_lobby_id = f"X{last_lobby_number + 1}"
        
        for cell in lobby_cells:
            if not cell.value:
                row = cell.row
                formatted_date_str = input_datetime_utc.strftime("%m/%d/%y")
                
                worksheet.update(f"H{row}", [[new_lobby_id]])
                worksheet.update(f"I{row}", [[formatted_date_str]])
                worksheet.update(f"J{row}", [[time]])
                
                timestamp = int(input_datetime_utc.timestamp())
                discord_timestamp = f"<t:{timestamp}:F>"
                
                print(f"✅ Created new lobby {new_lobby_id} on {formatted_date_str} at {time}. Timestamp for Discord: {discord_timestamp}")
                return new_lobby_id, None
        
        return None, "**No available space for a new lobby.**"
    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return None, "An error occurred while creating the lobby."
    
def get_lobbies(condition):
    """Fetches upcoming lobbies based on the given condition: 'empty' for no referee, 'free' for at least one empty team slot."""
    try:
        worksheet = sheet.worksheet("QSchedule")
        lobby_cells = worksheet.range("H2:H")
        date_cells = worksheet.range("I2:I")
        time_cells = worksheet.range("J2:J")
        referee_cells = worksheet.range("K2:K")
        team_cells = worksheet.range("M2:Q")  # Range of cells for the team slots

        upcoming_lobbies = []
        current_time = datetime.now(pytz.UTC)

        # Iterate over the lobbies
        for i, (lobby_cell, date_cell, time_cell, referee_cell) in enumerate(zip(lobby_cells, date_cells, time_cells, referee_cells)):
            # Determine which slice of team_cells corresponds to this row
            row_start = i * 5  # 5 team cells per row
            team_cell_range = team_cells[row_start:row_start + 5]  # Get 5 consecutive cells for each lobby

            if not lobby_cell.value or not date_cell.value or not time_cell.value:
                continue

            try:
                lobby_datetime = datetime.strptime(f"{date_cell.value} {time_cell.value}", "%m/%d/%y %H:%M").replace(tzinfo=pytz.UTC)
                if lobby_datetime < current_time:
                    continue  # Skip past lobbies
            except ValueError:
                continue

            # Handle the 'referee=empty' condition (no referee assigned)
            if condition == "referee=empty" and not referee_cell.value:
                discord_timestamp = f"<t:{int(lobby_datetime.timestamp())}:F>"
                upcoming_lobbies.append((lobby_cell.value, discord_timestamp))
                print(f"Lobby found: {lobby_cell.value}")  # Debugging log

            # Handle the 'free' condition (at least one empty team slot)
            elif condition == "free" and any(not cell.value for cell in team_cell_range):
                discord_timestamp = f"<t:{int(lobby_datetime.timestamp())}:F>"
                upcoming_lobbies.append((lobby_cell.value, discord_timestamp))
                print(f"Lobby found: {lobby_cell.value}")  # Debugging log

        return upcoming_lobbies

    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return []

def claim_referee(lobby_id, discord_nickname):
    """Claims a lobby by adding a referee's name to the referee cell."""
    try:
        worksheet = sheet.worksheet("QSchedule")
        cell = worksheet.find(lobby_id)

        if cell:
            row = cell.row
            referee_cell = worksheet.cell(row, 11)  # Referee cell is in column K (11th column)

            if referee_cell.value:
                return False, "**Lobby is already claimed.**"

            # Update the referee cell with the Discord user's nickname
            worksheet.update(referee_cell.address, [[discord_nickname]])  # Correct format for single cell update
            print(f"✅ {discord_nickname} claimed lobby {lobby_id} successfully.")
            return True, None
        else:
            return False, "**Lobby not found.**"

    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return False, "An error occurred while claiming the lobby."

def drop_referee(lobby_id, discord_nickname):
    """Drops a referee's claim on a lobby."""
    try:
        worksheet = sheet.worksheet("QSchedule")
        cell = worksheet.find(lobby_id)

        if cell:
            row = cell.row
            referee_cell = worksheet.cell(row, 11)  # Referee cell is in column K (11th column)

            if referee_cell.value != discord_nickname:
                # If the current referee is not the same as the user, return an error
                return False, "**This lobby is claimed by another referee. You cannot drop this claim.**"

            # Clear the referee cell if it matches
            worksheet.update(referee_cell.address, [['']])  # Clear the referee cell
            print(f"✅ {discord_nickname} dropped from lobby {lobby_id}.")
            return True, None
        else:
            return False, "**Lobby not found.**"

    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return False, "An error occurred while dropping the lobby."

def get_claimed_lobbies(discord_nickname):
    """Fetches the lobbies claimed by the referee, ensuring that the lobby times are not earlier than the current time by more than 1 hour."""
    try:
        worksheet = sheet.worksheet("QSchedule")
        lobby_cells = worksheet.range("H2:H")
        date_cells = worksheet.range("I2:I")
        time_cells = worksheet.range("J2:J")
        referee_cells = worksheet.range("K2:K")
        
        claimed_lobbies = []
        current_time = datetime.now(pytz.UTC)
        one_hour_earlier = current_time - timedelta(hours=1)

        # Iterate over the lobbies to find the ones claimed by the referee
        for i, (lobby_cell, date_cell, time_cell, referee_cell) in enumerate(zip(lobby_cells, date_cells, time_cells, referee_cells)):
            if referee_cell.value != discord_nickname:  # Only look for lobbies claimed by this referee
                continue

            try:
                lobby_datetime = datetime.strptime(f"{date_cell.value} {time_cell.value}", "%m/%d/%y %H:%M").replace(tzinfo=pytz.UTC)
                if lobby_datetime < one_hour_earlier:
                    continue  # Skip lobbies claimed more than 1 hour earlier
            except ValueError:
                continue  # Skip invalid date/time formats

            # Add the valid lobby to the list
            discord_timestamp = f"<t:{int(lobby_datetime.timestamp())}:F>"
            claimed_lobbies.append((lobby_cell.value, discord_timestamp))

        return claimed_lobbies

    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return []
