import os.path
import gspread

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1F40BYNNeUnYXjvWSb4ptXQlWuHae9pQosdxH3TyFn4A"
SAMPLE_RANGE_NAME = "Stats!C2:C"

def updateSheet(pokemon):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("shh_secrets/token.json"):
        creds = Credentials.from_authorized_user_file("./shh_secrets/token.json", SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "shh_secrets/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=3000, access_type='offline', prompt='consent')
        # Save the credentials for the next run
        with open("./shh_secrets/token.json", "w") as token:
            token.write(creds.to_json())
    
    try:
        # Set up the client
        client = gspread.auth.authorize(creds)
        
        # Open the Google Sheet
        sheet = client.open("Calyrex_OPmon_draft").worksheet("Stats")
        
        # Find the row with the matching species
        cell = sheet.find(pokemon.species, in_column=3)
        
        if cell:
            row = cell.row
            
            # Update the respective columns
            
            # increment sets active by 1
            new_value = int(sheet.cell(row, 4).value) + 1
            sheet.update_cell(row, 4, new_value)
                
            if pokemon.damage_done > 0:
                new_value = int(sheet.cell(row, 5).value) + pokemon.damage_done
                sheet.update_cell(row, 5, new_value)
            
            if pokemon.damage_tanked > 0:
                new_value = int(sheet.cell(row, 6).value) + pokemon.damage_tanked
                sheet.update_cell(row, 6, new_value)
                
            if pokemon.healing_done > 0:
                new_value = int(sheet.cell(row, 7).value) + pokemon.healing_done
                sheet.update_cell(row, 7, new_value)
            
            if pokemon.statuses_inflicted > 0:
                new_value = int(sheet.cell(row, 8).value) + pokemon.statuses_inflicted
                sheet.update_cell(row, 8, new_value)
                
            if pokemon.blocks_for > 0:
                new_value = int(sheet.cell(row, 9).value) + pokemon.blocks_for
                sheet.update_cell(row, 9, new_value)
                
            if pokemon.blocks_against > 0:
                new_value = int(sheet.cell(row, 10).value) + pokemon.blocks_against
                sheet.update_cell(row, 10, new_value)
            
            if pokemon.kills > 0:
                new_value = int(sheet.cell(row, 11).value) + pokemon.statuses_inflicted
                sheet.update_cell(row, 11, new_value)      

            if pokemon.fainted:
                new_value = int(sheet.cell(row, 12).value) + 1
                sheet.update_cell(row, 12, new_value)
                
            if pokemon.betrayals > 0:
                new_value = int(sheet.cell(row, 13).value) + pokemon.betrayals
                sheet.update_cell(row, 13, new_value)
            
    except Exception as e:
        print("we goofed")
        # Handle any other exceptions
        print(f"An unexpected error occurred: {e}")

# Gonna delete once I fully figure out this API
# def main():
#     creds = None
#     # The file token.json stores the user's access and refresh tokens, and is
#     # created automatically when the authorization flow completes for the first
#     # time.
#     if os.path.exists("./shh_secrets/token.json"):
#         creds = Credentials.from_authorized_user_file("./shh_secrets/token.json", SCOPES)

#     # If there are no (valid) credentials available, let the user log in.
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 "./shh_secrets/credentials.json", SCOPES
#             )
#             creds = flow.run_local_server(port=3000)
#         # Save the credentials for the next run
#         with open("./shh_secrets/token.json", "w") as token:
#             token.write(creds.to_json())

#     try:
#         service = build("sheets", "v4", credentials=creds)

#         # Call the Sheets API
#         sheet = service.spreadsheets()
#         result = (
#             sheet.values()
#             .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
#             .execute()
#         )
        
#         values = result.get("values", [])

#         if not values:
#             print("No data found.")
#             return

#         print("Pokemon:")
#         for row in values:
#             print(f"{row[0]}")
            
#     except HttpError as err:
#         print(err)


# if __name__ == "__main__":
#     main()
#     # updateSheet(None)