import argparse
import re
import logging
import asyncio
import subprocess
import random

import yaml
import discord

from util import ValueRetainingRegexMatcher
from persist import DatabaseManager

# https://discord.com/api/oauth2/authorize?client_id=812816570556088331&permissions=67648&scope=bot
# Parse the command line arguments
parser = argparse.ArgumentParser(description='Run the Whitehack dice bot.')
parser.add_argument('--config', type=str, required=True, help='The path to the configuration yaml file.')
args = parser.parse_args()


# Load the configuration file
config = {}
with open(args.config, 'r') as f:
    config = yaml.safe_load(f)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config['logging_path'] if 'logging_path' in config else 'bot.log'),
        logging.StreamHandler()
    ]
)

logging.info("Loading configuration...")
BOT_TOKEN = config['bot_token']
DB_FILE_PATH = config['sqlite3_database_path']


HELP_TEXT = '''\
 BOT UTILITY FUNCTIONS
-----------------------
!ping                           Checks if bot is alive
!help                           Displays this message
!version [history]

    DICE FUNCTIONS
-----------------------
!roll                           Roll some dice
'''


# Command regex
PING_REGEX = re.compile(r'!ping')
HELP_REGEX = re.compile(r'!help')
VERSION_REGEX = re.compile(r'!version(?: (.+))?')
ROLL_REGEX = re.compile(r'^\!roll (?:(\d+)?\s?[dD]\s?(\d{1,4})|(str|dex|wis|cha|int|con))\s?([+-]\s?\d{1,2})?\s?(\+{1,2}|-{1,2})?\s?(<=?\s?\d{1,4})?\s?(>=?\s?\d{1,4})?$')
STAT_REGEX = re.compile(r'\!stat (str|dex|con|int|wis|cha|av|ac) (\d{1,2})')
MACRO_REGEX = re.compile(r'\!macro ([a-zA-Z0-9]+)\s?(.+)?')

STAT_NAMES = {
    'str': 'strength',
    'dex': 'dexterity',
    'con': 'constitution',
    'int': 'intelligence',
    'wis': 'wisdom',
    'cha': 'charisma',
    'av': 'av',
    'ac': 'ac',
    'hp': 'hp'
}


class WhiteDiceBot(discord.Client):
    def __init__(self, **kwargs):
        self.db = DatabaseManager(DB_FILE_PATH)
        super().__init__(**kwargs)


    async def on_ready(self):
        logging.info("WhiteDice initializing...")
        await self.db.initialize()


    async def on_reaction_add(self, reaction, user):
        # If the reaction was from this bot, ignore it
        if user == self.user:
            return

        pass


    async def on_message(self, message):
        # Bot ignores itself. This is how you avoid the singularity.
        if message.author == self.user:
            return

        # Ignore anything that doesn't start with the magic token
        if not message.content.startswith('!'):
            return

        # Match against the right command, grab args, and go
        m = ValueRetainingRegexMatcher(message.content)

        # Process a command
        if m.match(PING_REGEX):
            await message.channel.send(f'{message.author.mention} pong!')
        elif m.match(VERSION_REGEX):
            num_commits = 5 if m.group(1) else 1
            version_content = subprocess.check_output(['git', 'log', '--use-mailmap', f'-n{num_commits}'])
            await message.channel.send("Latest commits..." + 
                "\n```" + str(version_content, 'utf-8') + "```")
        elif m.match(HELP_REGEX):
            await message.channel.send(f"```{HELP_TEXT}```")
        elif m.match(ROLL_REGEX):
            await self.roll(message, m)
        elif m.match(STAT_REGEX):
            stat = m.group(1)
            value = int(m.group(2).strip())
            await self.register_stat(message, stat.lower(), value)
        elif m.match(MACRO_REGEX):
            macro = m.group(1)
            value = m.group(2).strip() if m.group(2) else None
            if value:
                await self.register_macro(message, macro, value)
            else:
                new_cmd = self.db.get_macro(self.author, macro)
                m = m = ValueRetainingRegexMatcher(new_cmd)
                await self.roll(message, m)
            

    async def register_stat(self, message, stat, value):
        if stat not in STAT_NAMES:
            return
        await self.db.upsert_stat(message.author, STAT_NAMES[stat], value)
        await message.channel.send(f'{message.author.mention} - **{stat}** set to `{value}`')


    async def register_macro(self, message, macro, value):
        await self.db.upsert_macro(message.author, macro, value)
        await message.channel.send(f'{message.author.mention} - Macro **{macro}** set to `{value}`')


    async def roll(self, message, m):
        ''' Rolls the dice, right now everything is extracted via regex, and sanitized.
        Here are some examples of input...

        !roll d6
        !roll 1d6
        !roll 1 d 6
        !roll 1d20
        !roll 1d20+2
        !roll 1d20 + 2
        !roll 1d20 +2 --
        !roll str
        !roll dex+1
        !roll wis +1
        !roll con +2+
        !roll int+1++
        !roll cha+1 ++
        !roll d6++
        !roll int+1-- <5
        !roll int+1++ <=13
        !roll int+1++ < 1 >= 2
        '''
        num_dice = int(m.group(1)) if m.group(1) else 1
        size_die = int(m.group(2)) if m.group(2) else None
        stat = m.group(3) if m.group(3) else None
        
        if not stat and not size_die:
            return await message.channel.send('You must roll with a stat or a die of some size.')
        elif stat and size_die:
            return await message.channel.send('You can either roll a stat, or a die of a certain size, but not both.')
        elif not stat and not size_die:
            return await message.channel.send('You must roll either a die or a stat.')

        if stat:
            size_die = 20

        modifier = m.group(4) if m.group(4) else None
        advantage = m.group(5) if m.group(5) else None

        if advantage and num_dice > 1:
            return await message.channel.send('Advantage only applies to single die rolls.')

        less_than = m.group(6) if m.group(6) else None
        greater_than = m.group(7) if m.group(7) else None
        
        # TODO: Fetch it
        stat_val = None
        if stat:
            stats = await self.db.get_stats(message.author)
            if not stats:
                return await message.channel.send(f'You must set {stat} first (`!stat {stat} <value>`).')
            stat_val = stats[STAT_NAMES[stat]]


        raw_dice = [random.randint(1, size_die) for die in range(num_dice)]
        base_value = sum(raw_dice)

        modifier = modifier.strip().replace(' ', '') if modifier else ''
        post_mod = base_value
        if modifier:
            # For stat checks, mods affect the upper bound
            if stat:
                stat_val = stat_val + int(modifier[1:]) if modifier[0] == '+' else base_value - int(modifier[1:])
            else:
                post_mod = post_mod + int(modifier[1:]) if modifier[0] == '+' else base_value - int(modifier[1:])


        if not less_than and stat:
            less_than = f'<={stat_val}'

        was_crit = False
        if stat and post_mod == stat_val:
            was_crit = True

        less_than_result = True
        greater_than_result = True
        compare_str = f'[{post_mod}]'
        
        if less_than:
            less_than = less_than.replace(' ', '')
            compare_str += less_than
        if greater_than:
            greater_than = greater_than.replace(' ', '')

        if less_than and less_than[0:2] == '<=':
            less_than_result = post_mod <= int(less_than[2:])
        elif less_than and less_than[0] == '<':
            less_than_result = post_mod < int(less_than[1:])

        if greater_than and greater_than[0:2] == '>=':
            greater_than_result = post_mod >= int(greater_than[2:])
            compare_str = f'{greater_than[2:]}<=' + compare_str 
        elif greater_than and greater_than[0] == '>':
            greater_than_result = post_mod > int(greater_than[1:])
            compare_str = f'{greater_than[1:]}<' + compare_str

        was_compared = bool(less_than or greater_than)
        compared_result = less_than_result and greater_than_result

        die_str = f'{num_dice}d{size_die}'
        mod_str = f' {modifier} ' if modifier and not stat else ' '
        raw_str = f'`{" ".join(["[" + str(_) + "]" for _ in raw_dice])}`'
        comp_str = f'Within bounds `{compare_str}` --> {"PASS" if compared_result else "FAIL"}!' if was_compared else ''
        crit_str = f' **CRITICAL!!**' if was_crit else ''

        await message.channel.send(f'Rolling {die_str}{mod_str}...\n{raw_str}\nTOTAL: **{post_mod}**!\n{comp_str}{crit_str}')


def main():
    intents = discord.Intents.default()
    client = WhiteDiceBot(intents=intents)
    client.run(BOT_TOKEN)


if __name__ == "__main__":
    main()
