from bs4 import BeautifulSoup

class Trainer:
    def __init__(self, p="null", name="null"):
        self.name = name
        self.p = p
        self.win = 0


class Poke:
    def __init__(self, species="null"):
        self.species = species
        self.nickname = "null"
        # Used to maintain state in case of a toxic/burn kill
        self.statusBy = "null"
        # Used for other damaging debuffs
        self.startBy = []
        self.kills = 0
        self.fainted = 0

    
# List of trainers (equivalent to the array of trainers in PHP)
trainers = []
# Dictionary of Pokémon indexed by trainer (equivalent to $pokes in PHP)
pokes = {}

# Other variables associated with damaging moves
lastMoveUsed = ""
lastMovePoke = ""
sideStarted = []

# For weather
lastSwitchedPoke = ""
currentWeatherSetter = ""
weatherMove = 0

# Flags to print things once if there's something to review
seenFirstWeather = False
seenReplace = False

# Turn counter, mostly for detailed results and debugging
turn = 0


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

# Provide the path to your HTML file
file_path = 'Gen9NatDexDraft-2024-08-28-sarkev-icebender.html'

# Parse and print the headers
scripts = parse_html_script(file_path)
# Print script content
if scripts:
    print("\nScript content:")
    for script_content in scripts:
        print(f"  {script_content}")
