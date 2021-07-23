import json
import urllib.request, requests
import os, re
import discord
import random

from dotenv import load_dotenv

def write_arena_cards():
    with urllib.request.urlopen("https://api.scryfall.com/bulk-data") as url:
        data = json.loads(url.read().decode())
    oracle_ids_uri=data["data"][3]["download_uri"]
    response = requests.get(oracle_ids_uri, allow_redirects=True)
    cards=response.json()
    retdict={}
    for card in cards:
        if "arena_id" in card:
            retdict[str(card['arena_id'])] = card['name']
    # need to manually fix cards like claim // fame, etc
    with open(os.path.join(os.environ['USERPROFILE'], r"Documents\script\arena-cards.json"), "w") as outfile: 
        json.dump(retdict, outfile)    

def load_json_from_file():
    with open(os.path.join(os.environ['USERPROFILE'], r"Documents\script\arena-cards.json"), 'r', encoding='utf-8') as f:
        cards = json.load(f)
    return cards

def load_dict_from_user(dbjson, playerDict):
    userdict={}
    for playeritem, value in playerDict.items():
        if playeritem in dbjson: #some 5 digit codes are not valid scryfall arena_id values eg: 73145 . idk why, cosmetics maybe?
            if str(dbjson[playeritem]) not in userdict:
                userdict[dbjson[playeritem]] = value
            else:
                userdict[dbjson[playeritem]] += value
    return userdict
    
def get_library_from_player_logstring(librarystring):
    lastLibraryLine=""
    
    for line in librarystring.splitlines():
        if re.search(r"%s\b" % re.escape("PlayerInventory.GetPlayerCardsV3"), line):
            lastLibraryLine=line
    catalog=json.loads(lastLibraryLine.replace("[UnityCrossThreadLogger]<== PlayerInventory.GetPlayerCardsV3 ",""))
    return catalog["payload"]



def get_jumpstart_packs():
    with open(os.path.join(os.environ['USERPROFILE'], r"Documents\script\all_jumps.txt"), 'r', encoding='utf-8') as f:
        file_content = f.readlines()
    file_content = [x.strip() for x in file_content] 

    decks_dict={}
    subdict={}

    for line in file_content:
        if len(line)>0:#ignore blank lines
            if line[0].isnumeric():
                quantity=line.split(' ', 1)[0]
                card=line.split(' ', 1)[1]
                subdict[card]=quantity
                #this means it's a line item

            else:
                decks_dict[line]=subdict
                subdict={}
                pass
                #this means it's a deck name
    return decks_dict

def get_available_jumpstart_packs(user_catalog):
    retlist=[]
    packs=get_jumpstart_packs()
    for pack,packlist in packs.items():
        missingcards=[]
        cards_are_available=True
        for card,quantity in packlist.items():
            if card not in user_catalog:
                missingcards.append(card)
                print("1 " + card)
                cards_are_available=False
                break
        if cards_are_available:
            retlist.append(pack)
    return retlist

arena_ids=load_json_from_file()

jumpstart_packs=get_jumpstart_packs()


random_pack_options=[]

picked_packs=[]

with open(os.path.join(os.environ['USERPROFILE'], r"Documents\script\user_collections.json"), 'r', encoding='utf-8') as f:
        collection_dict = json.load(f)

load_dotenv()
client = discord.Client()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

@client.event
async def on_message(message):
    channel = message.channel
    if message.author == client.user:
        return        
    if message.content.lower().startswith("heybot pick packs"):
        username=message.content.lower().replace("heybot pick packs ","")
        random_pack_options=[]
        picked_packs=[]
        while len(picked_packs)<2:
            random_pack_options=[]
            while len(random_pack_options)<3:
                rand_num=random.randint(0, len(collection_dict[username])-1)
                if rand_num not in random_pack_options and rand_num not in picked_packs:
                    random_pack_options.append(rand_num)
            response_str="0: " + collection_dict[username][random_pack_options[0]].split('_', 1)[0] + ". 1: " + collection_dict[username][random_pack_options[1]].split('_', 1)[0] + ". 2: " + collection_dict[username][random_pack_options[2]].split('_', 1)[0] + ". q: quit"
            await message.channel.send(response_str)
            
            def check(m):
                return m.content in ['0','1','2','q'] and m.channel == channel

            msg = await client.wait_for('message', check=check)
            if msg.content=='q':
                await message.channel.send("gotcha. bye")
                break
            else:
                picked_packs.append(int(random_pack_options[int(msg.content)]))
        
        if len(picked_packs)==2:
            decklist="Deck\n"
            for i in range(len(picked_packs)):
                for key, value in jumpstart_packs[collection_dict[username][picked_packs[0]]].items():
                    decklist = decklist + str(value) + " " + key + "\n"
            await channel.send(decklist)
    elif message.content.lower().startswith("heybot load collection"):
        if message.attachments:
            username=message.content.lower().replace("heybot load collection ","")
            output = await message.attachments[0].read()
            user_ids=get_library_from_player_logstring(output.decode("utf-8"))
            user_catalog=load_dict_from_user(arena_ids,user_ids)

            available__jumpstart_packs=get_available_jumpstart_packs(user_catalog)
            collection_dict[username]=available__jumpstart_packs
            with open(os.path.join(os.environ['USERPROFILE'], r"Documents\script\user_collections.json"), "w") as outfile: 
                json.dump(collection_dict, outfile)    

            
            
        else:
            await channel.send("attachment not found")

    elif message.content.lower().startswith("heybot print available"):
        username=message.content.lower().replace("heybot print available ","")
        await channel.send(collection_dict[username])

client.run(DISCORD_TOKEN)
