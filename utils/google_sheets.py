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

        team_cells = worksheet.range("M2:Q")

        cell = worksheet.find(lobby_id)
        if cell:
            row = cell.row
            date_cell = worksheet.cell(row, 9)
            time_cell = worksheet.cell(row, 10)
            current_datetime = datetime.now(pytz.UTC)

            try:
                # Parse date and time correctly
                date_value = datetime.strptime(date_cell.value, "%m/%d/%y").date()
                time_value = datetime.strptime(time_cell.value, "%H:%M").time()  # Parses 'HH:MM' format

                # Combine into a full datetime
                combined_datetime = datetime.combine(date_value, time_value).replace(tzinfo=pytz.UTC)

                # Compare
                if combined_datetime < current_datetime:
                    print("The stored date and time is earlier than now.")
                    return None, f"The scheduled time for this lobby is earlier than current time."

            except ValueError:
                print("Invalid date or time format in the sheet.")
        
        for cell in team_cells:
            if cell.value == discord_nickname:
                worksheet.batch_clear([cell.address])
                print(f"❌ Removed existing {discord_nickname} from {cell.address}.")
        
        cell = worksheet.find(lobby_id)
        if cell:
            row = cell.row
            team_cells = worksheet.range(f"M{row}:Q{row}")
            
            for cell in team_cells:
                if not cell.value:
                    worksheet.update(cell.address, [[discord_nickname]])
                    print(f"✅ Updated {discord_nickname} in lobby {lobby_id} at {cell.address}.")
                    return True, None
        
        return False, "Lobby not found or full."
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
            return None, "Invalid date or date format. Please use mm/dd/yy HH:MM."
        
        input_datetime_utc = pytz.utc.localize(input_datetime)
        current_datetime = datetime.now(pytz.UTC)

        if input_datetime_utc < current_datetime + timedelta(hours=6):
            return None, "The date must be at least 6 hours from the current time."
        
        start_date = datetime(2025, 2, 27, 21, 0, tzinfo=pytz.UTC)
        end_date = datetime(2025, 3, 3, 23, 0, tzinfo=pytz.UTC)
        
        if not (start_date <= input_datetime_utc <= end_date):
            return None, f"The date must be between {start_date.strftime('%m/%d/%y %H:%M')} and {end_date.strftime('%m/%d/%y %H:%M')}."
        
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
                        return None, f"Lobby at this time already exists: {lobby_id}"
        
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
        
        return None, "No available space for a new lobby."
    except Exception as e:
        print(f"⚠️ Google Sheets Error: {e}")
        return None, "An error occurred while creating the lobby."