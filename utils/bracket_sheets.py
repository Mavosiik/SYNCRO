import gspread
from config import GOOGLE_SHEETS_CREDENTIALS
from datetime import datetime, timedelta
import pytz

gc = gspread.service_account(filename=GOOGLE_SHEETS_CREDENTIALS)
sheet = gc.open("SST3 Ref Sheet")

def get_worksheet():
    return sheet.worksheet("BSchedule")