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
        self.healing_done = 0
        self.statuses_inflicted = 0
        self.betrayals = 0
        # Trick / Switcheroo nonsense
        self.switched_item_previous_owner = None
        # track if this is the pokemons first turn switching in
        # necessary for setting initial hp and tracking regenerator healing
        self.is_first_turn = True

    def __str__(self):
            return f'Species = {self.species} \n Nickname = {self.nickname} \n Kills {self.kills} \n Fainted {self.fainted} \n HP {self.hp} \
            \n Damage Done: {self.damage_done} \n Healing done: {self.healing_done} \n'
        
    def __repr__(self):
            return f'Species = {self.species} \n Nickname = {self.nickname} \n Kills {self.kills} \n Fainted {self.fainted} \n HP {self.hp} \
            \n Damage Done: {self.damage_done} \n Healing done: {self.healing_done} \n'

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
currentTerrainSetter = None
weatherMove = 0

# Flags to print things once if there's something to review
seenFirstWeather = False
seenReplace = False

# Track last damage by a leech seed mon to see who gets the heal
lastLeechSeeder = None

# Track last Lunar Dance User (luckily this can only be Cresselia, so doesnt have the same niche issue as healing wish)
lastLunarDancer = None

# Track last mon that used healing wish
# TODO: Find a better solution?
# this technically doesn't work if healing wish is clicked by multiple mons in the same turn, but what are the odds?
lastHealingWisher = None

# Track last revival blessing user, has same issue as healing wish
lastRevivalBlesser = None

# Turn counter, mostly for detailed results and debugging
turn = 0

# Provide the path to your HTML file -- TODO Run this on the entire folder not just one html file
# TODO: Need update replays for the first 6 tests that use external replay and not user-perspective based replays
file_path = 'Replays\Test 14 -- draining moves, lunar blessing and dance, pain split, regenerator, floral healing, revival blessing.html'

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
    if nickname_pokemon.is_first_turn:
        set_hp(line[4],nickname_pokemon)
        nickname_pokemon.is_first_turn = False    

def check_regenerator(line):
    player, nickname = get_player_and_nickname_from_line_segment(line[2])
    mon = get_Pokemon_by_player_and_nickname(player, nickname)
    
    logged_hp = int(line[4].split("\\/")[0])
    
    if mon.hp != logged_hp and not mon.is_first_turn: # type: ignore
        print("WEEE WOOO WEEE WOOO WE HAVE A CRINGE REGEN STALL MON")
        mon.healing_done += logged_hp - mon.hp # type: ignore
        mon.hp = logged_hp # type: ignore
    

# oof this is a big boy
# handles all the possible damage calculations in order to make damage tracking possible
def check_damage(line):
    global lastMoveUsed, lastMovePoke, lastLeechSeeder

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
            from_source = line[4]
            from_source = from_source.replace("[from] ", "")
            damaging_move = from_source
            
            # Recoil is attributed to the opposing poke. Yeah, I know.
            # If it's recoil, it's a self-kill, so drop down
            if len(line) > 5 and damaging_move != "recoil":
                # We have a "[of]" for attribution of the kill! Hooray!
                of_source = line[5]
                of_source = of_source.replace("[of] ", "")
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
                        side_start_result = sideStarted.get(player, {}).get(from_source, None)
                        
                        if side_start_result is not None:
                            attacking_pokemon = side_start_result
                        else:
                            # Check starts
                            start_result = target_pokemon.startBy.get(from_source, None) # type: ignore
                            
                            if start_result is not None:
                                attacking_pokemon = start_result
                                
                                if from_source == 'Leech Seed':
                                    lastLeechSeeder = attacking_pokemon
                            else:
                                attacking_pokemon = target_pokemon
        
        # If killer is not on same team, increment kill
        if not check_if_on_same_team(attacking_pokemon, player):
            killer_mon = attacking_pokemon
            killer_mon.kills += 1 # type: ignore
            #Calculate Damage Done -- case changes if they fainted cause you cannot divide by zero :)
            calculate_faint_damage(target_pokemon, killer_mon)
            
        # if the killer was on the same team its a betrayal
        else:
            attacking_pokemon.betrayals += 1 # type: ignore
    
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
                            
                            if from_source == 'Leech Seed':
                                lastLeechSeeder = damaging_mon
                        else:
                            damaging_mon = target_pokemon
                            hp_segment = line[3]
        # check first if the damage was not performed by self-infliction or teammate
        if not check_if_on_same_team(damaging_mon, player):
            calculate_damage(target_pokemon, damaging_mon, hp_segment)
        else:
            # need to still update health if it was friendly fire
            calculate_damage(target_pokemon, None, hp_segment)

def check_move(line):
    global lastMovePoke, lastMoveUsed, lastHealingWisher, lastLunarDancer, lastRevivalBlesser
    # get the mons player and nickname
    a_player, a_nickname = get_player_and_nickname_from_line_segment(line[2])

    #Store move info as a global to track damage and other stats with
    lastMovePoke = get_Pokemon_by_player_and_nickname(a_player, a_nickname)
    lastMoveUsed = line[3]
    
    # check if the move used was healing wish (needed for tracking healing)
    if lastMoveUsed == "Healing Wish":
        lastHealingWisher = lastMovePoke
    
    # check if the move used was lunar dance (needed for tracking healing)
    if lastMoveUsed == "Lunar Dance":
        lastLunarDancer = lastMovePoke
    
    # check if the move used was revival blessing (needed for tracking healing)    
    if lastMoveUsed == "Revival Blessing":
        lastRevivalBlesser = lastMovePoke

    print(lastMovePoke.nickname, lastMoveUsed) # type: ignore

# stores the mon that set the weather manually, like sunny day or rain dance
# the weather header will directly follow the move being used, so we just store the last move poke
def check_manual_weather_setter():
    global currentWeatherSetter
    currentWeatherSetter = lastMovePoke

# stores the mon that set the terrain manually, like the move misty terrain
# the field start header will directly follow the move being used, so we just store teh last move poke    
def check_manual_terrain_setter():
    global currentTerrainSetter
    currentTerrainSetter = lastMovePoke

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

# stores the mon that set the terrain via an ability on entry, like grassy surge    
def check_ability_terrain_setter(line):
    global currentTerrainSetter
    
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
        
    currentTerrainSetter = get_Pokemon_by_player_and_nickname(split_of_source[0][:2], split_of_source[1])

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

# Used to keep track of a pokemons hp after they have been healed    
# TODO: only tested pollen puff, rest, life dew, heal pulse, berry, aqua ring, wish,
# leftovers, shell bell, aqua ring, grassy terrain, healing wish (known bug when multiple mons use at same time),
# floral healing, draining moves, lunar dance, revival blessing, ingrain and jungle healing
# FOR REGENERATOR: Is a switch case, check switch in main script and check_regenerator method
# FOR PAIN SPLI: Pain split is a sethp case, check sethp in main script and check_set_hp method
# Need to test present if we're really crazy)
def check_heal(line):
    global lastLeechSeeder, lastHealingWisher, lastLunarDancer, lastRevivalBlesser
    
    healed_player, healed_player_nickname = get_player_and_nickname_from_line_segment(line[2])
    healed_pokemon = get_Pokemon_by_player_and_nickname(healed_player, healed_player_nickname)
    healer_pokemon = None
    
    line_length = len(line)
    # This is the general case when healing was done by a unique move (think leech seed, berry, rest)
    if line_length == 5:
        # check first is the heal was from healing wish, since healing wish does not store the wish passer for some reason
        if line[4] == '[from] move: Healing Wish':
            healer_pokemon = lastHealingWisher
            lastHealingWisher = None
        # similarly check for lunar dance
        elif line[4] == '[from] move: Lunar Dance':
            healer_pokemon = lastLunarDancer
            lastLunarDancer = None
        # similarly check for revival blessing
        elif line[4] == '[from] move: Revival Blessing':
            healed_pokemon.fainted = False # type: ignore
            healer_pokemon = lastRevivalBlesser
            lastRevivalBlesser = None
        # check next if heal is from grassy terrain
        elif line[4] == '[from] Grassy Terrain':
            healer_pokemon = currentWeatherSetter
        # Leech seed has a weird property, so we store the last recorded leech seeder
        elif lastLeechSeeder is not None:
            healer_pokemon = lastLeechSeeder
            lastLeechSeeder = None
        # If not, berry/rest/aqua ring/lefties works like this
        else:
            healer_pokemon = healed_pokemon
    # so far this is the case for wish passing, drain moves, and shell bell for some reason, 
    elif line_length == 6:
        if "[wisher]" in line[5]:
            # the last index stores the mon that passed the wish (yippee)
            wisher_nickname = line[5].split("[wisher] ")[1]
            # we get the healer from its nickname and the player of the healed pokemon
            # (I dont think there is any way to wish pass to an opponent)
            healer_pokemon = get_Pokemon_by_player_and_nickname(healed_player, wisher_nickname)
            
        # So far only for shell bell and drain moves, the fifth index says which mon you damage which is irrelevant
        # only drain moves tested were giga drain and drain punch
        else:
            healer_pokemon = healed_pokemon
    else:
        # if that was not the case, then the last move is what healed the pokemon
        healer_pokemon = lastMovePoke
    
    calculate_heal(healed_pokemon, healer_pokemon, line[3])

# Used to set mons to faint during moves that auto-faint, like healing wish
def check_faint(line):
    fainted_player, fainted_player_nickname = get_player_and_nickname_from_line_segment(line[2])
    fainted_pokemon = get_Pokemon_by_player_and_nickname(fainted_player, fainted_player_nickname)
    fainted_pokemon.fainted = True # type: ignore
    fainted_pokemon.hp = 0 # type: ignore
    

# Method that handles -sethp headers
def check_set_hp(line):
    if '[from]' in line[4]:
        from_source = line[4].split("[from] ")[1]
        
        #so far only known case of this header is pain split
        if from_source == 'move: Pain Split':
            # when the line has length six, it refers to the mon targeted by pain split
            if len(line) == 6:
                targeted_player, targeted_nickname = get_player_and_nickname_from_line_segment(line[2])
                targeted_mon = get_Pokemon_by_player_and_nickname(targeted_player, targeted_nickname)
                # the mon that used pain split will be the last move mon
                attacking_mon = lastMovePoke
                
                # check the hp stat of the targeted mon
                new_hp = int(line[3].split("\\/")[0])
                # check if the targeted_mon's hp went down, if it did, credit the attacking mon with damage
                if new_hp < targeted_mon.hp: # type: ignore
                    calculate_damage(targeted_mon, attacking_mon, line[3])
                # else, just update the targeted_mon's hp
                else:
                    targeted_mon.hp = new_hp # type: ignore
            # This is the mon using pain split
            else:
                # the mon that used pain split will be the last move mon
                pain_split_user = lastMovePoke
                
                # check the hp stat of the targeted mon
                new_hp = int(line[3].split("\\/")[0])
                # check if the pain split users's hp went up, if it did, credit the mon with healing
                if new_hp > pain_split_user.hp: # type: ignore
                    calculate_heal(pain_split_user, pain_split_user, line[3])
                # else, just update the targeted_mon's hp
                else:
                    pain_split_user.hp = new_hp # type: ignore

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

# Calculate the hp that was healed and set the healed mon to their new hp stat
def calculate_heal(healed_pokemon, healer_pokemon, health_segment):
    #Get the New HP
    new_hp = int(health_segment.split("\\/")[0])
    amount_healed = new_hp - healed_pokemon.hp
    
    healer_pokemon_team = 'p1'
    if healer_pokemon.nickname not in pokes[healer_pokemon_team]:
        healer_pokemon_team = 'p2'
    
    # check to that the healer and healed mon are on the same team, healing should only be credited
    # if self-inflicted or by a teammate
    if(check_if_on_same_team(healed_pokemon, healer_pokemon_team)):
        healer_pokemon.healing_done += amount_healed

    # For Serious
    healed_pokemon.hp = new_hp

# TODO: remove set hp because it will always default to 100 now
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
                    
                    # REGENERATOR IS NOT A HEAL (WHY??????)
                    # IT HAPPENS ON SWITCH, SO EVERY SWITCH NEED TO CHECK IF HP CHANGED (BLACK PILLED)
                    check_regenerator(line)

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
                
                # case related to all healing moves and items (drain moves, recover variants, leech seed, leftovers, berries, etc)    
                case '-heal':
                    check_heal(line)
                
                # case related to when a pokemon faints after using a move (so far have only seen Healing Wish)
                # TODO: test destiny bond and perish song
                case 'faint':
                    check_faint(line)
                
                # case related to setting a terrain    
                case '-fieldstart':
                    
                    # |-fieldstart|move: Misty Terrain --> terrain set manually
                    # If it 3 parts long, this means terrain was just set manually
                    if len(line) == 3:
                        # record who set the weather on which team
                        check_manual_terrain_setter()
                    
                    #|-fieldstart|move: Grassy Terrain|[from] ability: Grassy Surge|[of] p2a: Rillaboom --> terrain set by ability on entry
                    # If it is 5 parts long, then weather was set by an ability
                    else:
                        check_ability_terrain_setter(line)
                # This is seen in cases where hp is directly set, like in pain split
                # Example: mon targeted by pains plit --> |-sethp|p1a: Pawmot|100\/100|[from] move: Pain Split|[silent]
                # Example: mon using pain split --> |-sethp|p2b: Calyrex|73\/100|[from] move: Pain Split
                case '-sethp':
                    check_set_hp(line)
                # just a turn counter lol, could be useful for debugging
                case 'turn':
                    turn += 1
    print(pokes)
