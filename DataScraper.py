from bs4 import BeautifulSoup

class Player:
    def __init__(self, position="null", name="null", win="null"):
        self.name = name
        self.position = position
        self.win = win


class Pokemon:
    def __init__(self, species="null"):
        self.species = species
        self.nickname = "null"
        # Used to maintain state in case of a toxic/burn kill
        self.statusBy = "null"
        # Used for other damaging debuffs
        self.kills = 0
        self.fainted = 0
        self.damage_done = 0

    def __str__(self):
            return f'Species = {self.species} -- Nickname = {self.nickname}'
        
    def __repr__(self):
            return f'Species = {self.species} -- Nickname = {self.nickname}'

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
players = []
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

def assign_pokemon(pokemon_line):

    # Grab the Player
    owned_by = pokemon_line[2]
    species = pokemon_line[3].split(",")[0]

    #Assign the pokemon to each player
    nxt_poke = Pokemon(species=species)
    if owned_by in pokes:
        pokes[owned_by].append(nxt_poke)
    else:
        pokes[owned_by] = [nxt_poke]

#Gets the nickname of each mon and assigns it to them in the pokes dict
def grab_nickname(line):

    player_nickname = get_player_and_nickname(line[2])

    player = player_nickname[0]
    nickname = player_nickname[1]

    species = line[3].split(",")[0]

    #Assign the Nickname to the right pokemon Pokemon -- TODO properly
    for pokemon in pokes[player]:
        if pokemon.species == species:
            pokemon.nickname = nickname
            break
    
    print(pokes)

# Splits the player and nickname segement into their individual components
# Example: ['', 'switch', 'p1a: Nuke', 'Calyrex-Shadow, L50', '100\\/100']
#Pass segement 'p1a: Nuke'
# Returns []
def get_player_and_nickname(segment):

    split_list = segment.split(':')

    if len(split_list) > 2:
        # WHO NICKNAMES MONS WITH :
        nickname = ''
        for part in split_list[1:]:
            nickname += part
            nickname += ':'
        split_list[1] = nickname

    #Nicknames have leading space for some reason -- remove it
    split_list[1] = split_list[1].lstrip()

    if "p1" in split_list[0]:
        split_list[0] = 'p1'
    elif "p2" in split_list[0]:
        split_list[0] = 'p2'
    
    return split_list[0:2]

def check_damage(line):



# Main Script runs here
if battle_log:
    logs = split_battle_log(battle_log)  #ALEX DUMBASS UPGRADE TO 3.10.* ISH OR ELSE THIS WONT WORK

    for line in logs:
        if len(line) > 1:

            match line[1]:
                # Adds the players to the list of trainers
                case 'player':
                    players.append(Player(name=line[3], position=line[2]))

                # Assigns each pokemon to their respective player dict
                case 'poke':
                    assign_pokemon(line)

                # Need to find the nickname cause for SOME reason, the moves are performed by the nicknames of the mons not the species???
                # This hasent been changed in 8 years????

                # Switcing in is voluntary (switch, u-turn)
                # Drag is roar and whirlwind
                # Replace is literaly just for Zoroark
                case 'switch' | 'drag' | 'replace':
                    grab_nickname(line)

                #Detect Damage -- if a pokemon does damage, record it
                case '-damage':
                    check_damage(line)
                


    