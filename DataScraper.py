from bs4 import BeautifulSoup

class Trainer:
    def __init__(self, p="null", name="null", win="null"):
        self.name = name
        self.p = p
        self.win = win


class Poke:
    def __init__(self, species="null"):
        self.species = species
        self.nickname = "null"
        # Used to maintain state in case of a toxic/burn kill
        self.statusBy = "null"
        # Used for other damaging debuffs
        self.kills = 0
        self.fainted = 0

# Function to open and parse the HTML file
def parse_html_script(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        # Read the HTML content
        content = file.read()

        # Parse the HTML content using the built-in html.parser
        soup = BeautifulSoup(content, 'html.parser')

        # Extract all <script> tags content
        scripts = [script.string for script in soup.find_all('script') if script.string]

        return scripts

    
# List of trainers
trainers = []
# Dictionary of Pokémon indexed by trainer
pokes = {}

# Other variables associated with damaging moves
lastMoveUsed = ""
lastMovePoke = ""
sideStarted = []

# For weather
lastSwitchedPoke = ""
currentWeatherSetter = ""
weatherMove = 0

# Turn counter, mostly for detailed results and debugging
turn = 0

# Provide the path to your HTML file -- TODO Run this on the entire folder not just one html file
file_path = 'Replays/Test 1 -- OpenSheet -- Game 2.html'

# Get the Battlelog from the html file
battle_log = parse_html_script(file_path)[0]

def split_battle_log(battle_log):
    split_log = battle_log.splitlines()
    logs = []
    for log in split_log:
        log = log.split("|")
        logs.append(log)
    return logs

# Print script content
if battle_log:
    logs = split_battle_log(battle_log)
    for log in logs:
        print(f'{log}')
    