from bs4 import BeautifulSoup

class Player:
    def __init__(self, position="null", name="null", win="null"):
        self.name = name
        self.position = position
        self.win = win


class Pokemon:
    def __init__(self, species="null", hp=0):
        self.species = species
        self.hp = hp
        self.nickname = "null"
        # Used to maintain state in case of a toxic/burn kill
        self.statusBy = "null"
        # Used for other damaging debuffs
        self.startBy = {}
        self.kills = 0
        self.fainted = False
        self.damage_done = 0

    def __str__(self):
            return f'Species = {self.species} -- Nickname = {self.nickname} -- Kills {self.kills} -- Fainted {self.fainted}'
        
    def __repr__(self):
            return f'Species = {self.species} -- Nickname = {self.nickname} -- Kills {self.kills} -- Fainted {self.fainted}'

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
sideStarted = {}

# For weather
lastSwitchedPoke = ""
currentWeatherSetter = ""
weatherMove = 0

# Turn counter, mostly for detailed results and debugging
turn = 0

# Provide the path to your HTML file -- TODO Run this on the entire folder not just one html file
file_path = 'Replays\Test 1 -- OpenSheet -- Game 2.html'

# Get the Battlelog from the html file
battle_log = parse_html_script(file_path)[0]

# ------------- Called Methods in Main --------------------

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
        pokes[owned_by][species] = nxt_poke
    else:
        pokes[owned_by] = {species: nxt_poke}

#Gets the nickname of each mon and assigns it to them in the pokes dict
def grab_nickname(line):

    player_nickname = get_player_and_nickname_from_line(line[2])

    player, nickname  = player_nickname

    species = line[3].split(",")[0]

    #Assign the Nickname to the right pokemon Pokemon
    pokes[player][species].nickname = nickname

# REMINDER: DO NOT INCREMENT MURDER COUNTER IF TEAMMATE WAS KILLED (or add a betrayal count)
def check_damage(line):
    global lastMoveUsed, lastMovePoke
    #Check if damage fainted the opponent
    if(line[3] == '0 fnt'):
        # Get the current pokemon from the player and the mons nickname
        player, nickname = get_player_and_nickname_from_line(line[2])
        curr_pokemon = get_Pokemon_by_player_and_nickname(player, nickname)
        
        # Record that the mon fainted
        curr_pokemon.fainted = True
        
        # Figure out how mon died, first assume it was from the last move
        killing_move = lastMoveUsed
        killer = lastMovePoke
        
        if (len(line) > 4):
            # a kill from indirect damage
            fromSource = line[4]
            fromSource = fromSource.replace("[from] ", "")
            killing_move = fromSource
            
            # Recoil is attributed to the opposing poke. Yeah, I know.
            # If it's recoil, it's a self-kill, so drop down
            if len(line) > 5 and killing_move != "recoil":
                # We have a "[of]" for attribution of the kill! Hooray!
                ofSource = line[5]
                ofSource = ofSource.replace("[of] ", "")
                killer_player, killer_nickname = get_player_and_nickname_from_line(ofSource)
                killer = get_Pokemon_by_player_and_nickname(killer_player, killer_nickname)
            else:
                # No "[of]", requires variable state to determine
                # Otherwise, it's probably a self-death
                
                # Check status and weather
                match killing_move:
                    case "brn" | "psn":
                        killer = curr_pokemon.statusBy
                    case "sandstorm" | "hail":
                        killer = currentWeatherSetter
                    case _:
                        # Not status nor weather...
                        # Check side starts
                        side_start_result = sideStarted.get(player, {}).get(fromSource, None)
                        
                        if side_start_result is not None:
                            killer = side_start_result
                        else:
                            # Check starts
                            start_result = curr_pokemon.startBy.get(fromSource, None)
                            
                            if start_result is not None:
                                killer = start_result
                            else:
                                killer = curr_pokemon
        
        # If killer is not on same team, increment kill
        if not check_if_killer_on_same_team(killer, player):
            get_Pokemon_by_player_and_nickname(get_other_player(player),killer).kills += 1

def check_move(line):
    global lastMovePoke, lastMoveUsed
    # get the mons nickname
    _, a_nickname = get_player_and_nickname_from_line(line[2])

    #Store move info as a global to track damage and other stats with
    lastMovePoke = a_nickname
    lastMoveUsed = line[3]

    print(lastMovePoke, lastMoveUsed)

# -------------- Helper Methods ----------------

# Splits the player and nickname segement into their individual components
# Example: ['', 'switch', 'p1a: Nuke', 'Calyrex-Shadow, L50', '100\\/100']
#Pass segment 'p1a: Nuke'
# Returns tuple(str,str)
def get_player_and_nickname_from_line(segment):

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
    
    split_list_fixed = split_list[0:2]
    return split_list_fixed[0], split_list_fixed[1]


def get_Pokemon_by_player_and_nickname(player, nickname):
    for species in pokes[player]:
        if pokes[player][species].nickname == nickname:
            return pokes[player][species]
        
    # if this happens, something bad happened
    return None

def check_if_killer_on_same_team(killer, fainted_team):
    for species in pokes[fainted_team]:
        if pokes[fainted_team][species].nickname == killer:
            return True
        
    return False

# Coding Excellence
def get_other_player(player):
    if player == 'p1':
        return 'p2'
    else:
        return 'p1'

# Main Script runs here
if battle_log:
    logs = split_battle_log(battle_log) 

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
                # This hasn't been changed in 8 years????

                # Switching in is voluntary (switch, u-turn)
                # Drag is roar and whirlwind
                # Replace is literally just for Zoroark
                case 'switch' | 'drag' | 'replace':
                    grab_nickname(line)

                #Detect Damage -- if a pokemon does damage, record it
                case '-damage':
                    check_damage(line)

                #Detect Move -- see which pokemon did the move and save it as a global
                case 'move':
                    check_move(line)

    print(pokes)
