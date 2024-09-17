from bs4 import BeautifulSoup

class Player:
    def __init__(self, position="null", name="null", win="null"):
        self.name = name
        self.position = position
        self.win = False


class Pokemon:
    def __init__(self, species="null"):
        self.species = species
        self.hp = 0
        self.max_hp = -1
        self.nickname = "null"
        # Used to maintain state in case of a toxic/burn kill
        self.statusBy = None
        # Used for other damaging debuffs
        self.startBy = {}
        self.kills = 0
        self.fainted = False
        self.damage_done = 0
        self.statuses_inflicted = 0
        # Trick / Switcheroo nonsense
        self.switched_item_previous_owner = None

    def __str__(self):
            return f'Species = {self.species} \n Nickname = {self.nickname} \n Kills {self.kills} \n Fainted {self.fainted} \n HP {self.hp} \
            \n Damage Done: {self.damage_done} \n Volatile Statuses: {self.startBy} \n'
        
    def __repr__(self):
            return f'Species = {self.species} \n Nickname = {self.nickname} \n Kills {self.kills} \n Fainted {self.fainted} \n HP {self.hp} \
            \n Damage Done: {self.damage_done} \n Volatile Statuses: {self.startBy} \n'

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
# Pokemon Object
lastMovePoke = None
sideStarted = {}

# For weather
lastSwitchedPoke = ""
# Pokemon Object
currentWeatherSetter = None
weatherMove = 0

# Flags to print things once if there's something to review
seenFirstWeather = False
seenReplace = False

# Turn counter, mostly for detailed results and debugging
turn = 0

# Provide the path to your HTML file -- TODO Run this on the entire folder not just one html file
# TODO: Need update replays for the first 6 tests that use external replay and not user-perspective based replays
file_path = 'Replays\Test 2 -- indirect damage kills.html'

# Get the battle log from the html file
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

# Gets the nickname of each mon and assigns it to them in the pokes dict
def grab_nickname(line):

    player_nickname = get_player_and_nickname_from_line_segment(line[2])

    player, nickname  = player_nickname

    species = line[3].split(",")[0]

    #Assign the Nickname to the right pokemon Pokemon
    nickname_pokemon = pokes[player][species]
    nickname_pokemon.nickname = nickname

    #Assign initial hp value
    set_hp(line[4],nickname_pokemon)

# REMINDER: DO NOT INCREMENT MURDER COUNTER IF TEAMMATE WAS KILLED (or add a betrayal count)
def check_damage(line):
    global lastMoveUsed, lastMovePoke

    # Get the attacked/dead pokemon from the player and the mons nickname
    player, nickname = get_player_and_nickname_from_line_segment(line[2])
    target_pokemon = get_Pokemon_by_player_and_nickname(player, nickname)

    # Figure out how mon died/took damage, first assume it was from the last move
    damaging_move = lastMoveUsed
    attacking_pokemon = lastMovePoke

    # Check if damage fainted the opponent
    if(line[3] == '0 fnt'):
        
        # Record that the mon fainted
        target_pokemon.fainted = True # type: ignore
        
        if (len(line) > 4):
            # a kill from indirect damage
            fromSource = line[4]
            fromSource = fromSource.replace("[from] ", "")
            damaging_move = fromSource
            
            # Recoil is attributed to the opposing poke. Yeah, I know.
            # If it's recoil, it's a self-kill, so drop down
            if len(line) > 5 and damaging_move != "recoil":
                # We have a "[of]" for attribution of the kill! Hooray!
                ofSource = line[5]
                ofSource = ofSource.replace("[of] ", "")
                # killer_player, killer_nickname = get_player_and_nickname_from_line_segment(ofSource)
                # attacking_pokemon = get_Pokemon_by_player_and_nickname(killer_player, killer_nickname)
            else:
                # No "[of]", requires variable state to determine
                # Otherwise, it's probably a self-death
                
                # Check status and weather
                match damaging_move:
                    case "brn" | "psn":
                        attacking_pokemon = target_pokemon.statusBy # type: ignore
                    case "sandstorm" | "hail" | "Sandstorm" | "Hail":
                        attacking_pokemon = currentWeatherSetter
                    case _:
                        # Not status nor weather...
                        # Check side starts
                        side_start_result = sideStarted.get(player, {}).get(fromSource, None)
                        
                        if side_start_result is not None:
                            attacking_pokemon = side_start_result
                        else:
                            # Check starts
                            start_result = target_pokemon.startBy.get(fromSource, None) # type: ignore
                            
                            if start_result is not None:
                                attacking_pokemon = start_result
                            else:
                                attacking_pokemon = target_pokemon
        
        # If killer is not on same team, increment kill
        if not check_if_on_same_team(attacking_pokemon, player):
            killer_mon = attacking_pokemon
            killer_mon.kills += 1 # type: ignore
            #Calculate Damage Done -- case changes if they fainted cause you cannot divide by zero :)
            calculate_faint_damage(target_pokemon, killer_mon)
    
    # Check Damage if the Mon didn't faint TODO: Edge Cases, dear god the edge cases
    else:
        damaging_mon = None
        hp_segment = None
        # base case: a damaging move caused the damage
        if len(line) == 4:
            damaging_mon = attacking_pokemon
            hp_segment = line[3]
        # time to find what caused damage
        else:
            from_source = line[4]
            from_source = (from_source.replace("[from] ", ""))
            
            match from_source:
                case "brn" | "psn":
                    damaging_mon = target_pokemon.statusBy # type: ignore
                    hp_segment = line[3]
                case "sandstorm" | "hail" | "Sandstorm" | "Hail":
                    damaging_mon = currentWeatherSetter
                    hp_segment = line[3]
                case _:
                    # Not status nor weather...
                    # Check side starts
                    side_start_result = sideStarted.get(player, {}).get(from_source, None)
                        
                    if side_start_result is not None:
                        damaging_mon = side_start_result
                        hp_segment = line[3]
                    else:
                        # Check starts
                        start_result = target_pokemon.startBy.get(from_source, None) # type: ignore
                        
                        if start_result is not None:
                            damaging_mon = start_result
                            hp_segment = line[3]
                        else:
                            damaging_mon = target_pokemon
        # check first if the damage was not performed by self-infliction or teammate
        if not check_if_on_same_team(damaging_mon, player):
            calculate_damage(target_pokemon, damaging_mon, hp_segment)
        else:
            # need to still update health if it was friendly fire
            calculate_damage(target_pokemon, None, hp_segment)

def check_move(line):
    global lastMovePoke, lastMoveUsed
    # get the mons player and nickname
    a_player, a_nickname = get_player_and_nickname_from_line_segment(line[2])

    #Store move info as a global to track damage and other stats with
    lastMovePoke = get_Pokemon_by_player_and_nickname(a_player, a_nickname)
    lastMoveUsed = line[3]

    print(lastMovePoke.nickname, lastMoveUsed) # type: ignore

# stores the mon that set the weather manually, like sunny day or rain dance
# the weather header will directly follow the move being used, so we just store teh last move poke
def check_manual_weather_setter():
    global currentWeatherSetter
    currentWeatherSetter = lastMovePoke

# stores the mon that set the weather via an ability on entry, like drought or drizzle
def check_ability_weather_setter(line):
    global currentWeatherSetter
    
    of_source = line[4]
    of_source = of_source.replace("[of] ", "")
    split_of_source = of_source.split(": ")
    
    if len(split_of_source) > 2:
        # WHO NICKNAMES MONS WITH :
        nickname = ''
        for i in range(1, len(split_of_source)):
            nickname += split_of_source[i]
            if i != len(split_of_source) - 1:
                nickname += ':'
        split_of_source[1] = nickname
        
    currentWeatherSetter = get_Pokemon_by_player_and_nickname(split_of_source[0][:2], split_of_source[1])

# Status Case
# Example Line: |-status|p1a: Nuke|tox --> Nuke has been Toxiced, check lastMoveMon to credit the mon who inflicted them
def check_status(line):
    affected_player, affected_player_nickname = get_player_and_nickname_from_line_segment(line[2])
    affected_player_pokemon = get_Pokemon_by_player_and_nickname(affected_player,affected_player_nickname)
    
    # This is the case that a status was inflicted by an item
    if(len(line) > 4):
        # check if the item was tricked onto the pokemon of not
        # if this attribute (switched_item_previous_owner) is null, that means item was from the affected pokemon
        if affected_player_pokemon.switched_item_previous_owner is None: # type: ignore
            affected_player_pokemon.statusBy = affected_player_pokemon # type: ignore
        # if the attribute was not none, that means the item was tricked onto the affected pokemon
        else:
            affected_player_pokemon.statusBy = affected_player_pokemon.switched_item_previous_owner # type: ignore
    else:
        #On the affected mon --> set status by as the lastMovePoke
        affected_player_pokemon.statusBy = lastMovePoke # type: ignore
        
        # Check that the mon that used the status move is not the affected mon (think REST)
        if lastMovePoke != affected_player_pokemon:
            #On the applying mon --> increase status_applied counter by one
            lastMovePoke.statuses_inflicted += 1 # type: ignore

# Ability Procs and Switcheroo/Trick shenanigans
def check_activate(line):
    activate_source = line[3].split(": ")
    # check for trick or switcheroo first
    # TODO: test if this actually works when tricking a flame or toxic orb
    # TODO: think of tricking sticky barb
    if activate_source[0] == 'move':
        if activate_source[1] == 'Trick' or activate_source[1] == 'Switcheroo':
            # TODO: consider nicknames with ": "
            split_trick_user_components = line[2].split(": ")
            trick_user_player = split_trick_user_components[0][:2]
            trick_user_pokemon_nickname = split_trick_user_components[1]
            
            trick_target_pokemon_nickname = line[4].split(": ")[1]
            trick_target_player = get_other_player(trick_user_player)
            
            trick_target_pokemon = get_Pokemon_by_player_and_nickname(trick_target_player, trick_target_pokemon_nickname)
            trick_target_pokemon.switched_item_previous_owner = get_Pokemon_by_player_and_nickname(trick_user_player, trick_user_pokemon_nickname) # type: ignore

# Used to track which mon set a volatile status on another mon           
def check_start(line):
    affected_player, affected_player_nickname = get_player_and_nickname_from_line_segment(line[2])
    affected_player_pokemon = get_Pokemon_by_player_and_nickname(affected_player,affected_player_nickname)
    started = line[3]
    
    if ("move: " in started):
        started = started.split("move: ")[1]
    
    # mark who started what on this pokemon
    affected_player_pokemon.startBy[started] = lastMovePoke # type: ignore

# Used to track which mon set a side condition (i.e. hazards) on a affected players side  
def check_side_start(line):
    global sideStarted
    
    player = get_player_from_side_start(line[2])
    effect = get_effect_from_side_start(line[3])
    
    if player not in sideStarted:
        sideStarted[player] = {}
        
    sideStarted[player][effect] = lastMovePoke

# Assign Winner based on line
# |win|Sixteen Gremlins
def assign_winner(line):

    winner = line[2]
    for player in players:
        if player.name == winner:
            player.win = True


# -------------- Helper Methods ----------------

# Calculate the Damage of a Mon
# Example Line: '[11\/176]'
# Variable Types -- dead_mon : Pokemon(Object), killer_mon : Pokemon(Object), damage_seg : str
def calculate_damage(target_mon,attacking_mon,damage_seg):

    #Get the New HP
    new_hp = int(damage_seg.split("\\/")[0])
    
    if attacking_mon is not None:
        damage = target_mon.hp - new_hp
        attacking_mon.damage_done += damage

    # For Serious
    target_mon.hp = new_hp

# Calculate the Damage of a Mon that Fainted
# Example Line: '0 fnt'
# Variable Types -- dead_mon : Pokemon(Object), killer_mon : Pokemon(Object)
def calculate_faint_damage(dead_mon,killer_mon):    
    killer_mon.damage_done += dead_mon.hp
    
    # For fun
    dead_mon.hp = 0


# Sets the current HP of the Pokemon Object
# Variable Types -- health : str, Pokemon : Pokemon(Object)
# Health Example: '100\\/100'
def set_hp(health,pokemon):

    hp_value = health.split("\\/")
    pokemon.hp = int(hp_value[0])
    
    #On first set hp call, set the Max Hp of the Pokemon and never return here agiiiin
    if pokemon.max_hp == -1:
        pokemon.max_hp = int(hp_value[1])

# Splits the player and nickname segment into their individual components
# Example: 'p1a: Nuke'
# Pass segment 'p1a: Nuke'
# Returns tuple(str,str)
def get_player_and_nickname_from_line_segment(segment):

    split_list = segment.split(': ')

    if len(split_list) > 2:
        # WHO NICKNAMES MONS WITH :
        nickname = ''
        for i in range(1, len(split_list)):
            nickname += split_list[i]
            if i != len(split_list) - 1:
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

# Method to check if the mon that got a kill was a teammate of the fainted mon
# Takes as parameters - Killer (Pokemon Object) and Fainted Team (Str ex: 'p1')
def check_if_on_same_team(killer, fainted_team):
    for species in pokes[fainted_team]:
        if pokes[fainted_team][species].nickname == killer.nickname:
            return True
        
    return False

# Coding Excellence
def get_other_player(player):
    if player == 'p1':
        return 'p2'
    else:
        return 'p1'

# get the player which set the side start effect (like hazards)    
def get_player_from_side_start(segment):
    return segment.split(": ")[0]

# get the effect of the sidestart (such as Stealth Rock, Spikes, Tailwind, etc.)
def get_effect_from_side_start(segment):
    return segment.split(": ")[1]

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

                # Winner is declared on this line
                # |win|Sixteen Gremlins
                case 'win':
                    assign_winner(line)

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
                    
                # Detect megas -- update the mon to its mega form (TODO: IN FUTURE IF THERE IS A MEGA)
                case '-formechange':
                    print("How did a mega get into Gen 9 VGC?")
                
                # Keep track of what mon set the weather
                # Important for sandstorm damage / kills and older generation hail damage / kills    
                case '-weather':
                    # If line is 4 parts long, than its just upkeep
                    
                    # |-weather|SunnyDay --> weather set manually
                    # If it 3 parts long and line 2 is not "none", this means weather was just set manually
                    if(len(line) == 3 and line[2] != "none"):
                        # record who set the weather on which team
                        check_manual_weather_setter()
                    
                    #|-weather|Sandstorm|[from] ability: Sand Stream|[of] p1a: Ty:Get:Mogged --> weather set by Sand Stream on entry
                    # If it is 5 parts long, then weather was set by an ability
                    if(len(line) == 5):
                        check_ability_weather_setter(line)
                    
                    print("The mon that last set the weather was: " + currentWeatherSetter.nickname) # type: ignore
                
                # Keeps track of status conditions
                # Burn and poison are relevant for damage calculations
                # Others like sleep and burn are tracked in the Pokemon object statuses
                case '-status':
                    
                    # |-status|p1a: Nuke|tox --> Pokemon just gained status condition, check who applied it
                    check_status(line)
                
                case '-activate':
                    
                    # the only case we know so far of this header is for trick/switcheroo
                    # which is relevant when Kevin inevitably Klutz Switcheroo's a flame orb
                    check_activate(line)
                    
                # start relates to any volatile status, such as confusion, perish song, substitute, leech seed, etc.
                # all volatile statuses can be found at https://bulbapedia.bulbagarden.net/wiki/Status_condition#Volatile_status
                case '-start':
                    check_start(line)
                
                # sidestart relates to all effects that affect one side of the field (tailwind, hazards, screens)
                # TODO: -swapsideconditions is a header that swaps side conditions between sides, used for court change 
                case '-sidestart':
                    check_side_start(line)

    print(pokes)
