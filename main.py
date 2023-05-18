import os
import sys
import typing
import subprocess
import discord
import requests
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime, time, timedelta
import yaml

TOKEN = ''

SERVER_ID = ''

CHANNEL_IDS = [] # in integrale

USERNAME_FILE = 'non_votanti.json'

STAFFER_FILE = 'staffer.yaml'

REMINDER_TIME = time(hour=8, minute=16)

REMINDER_MESSAGE = "```Ecco gli staffers che non hanno votato:\n"

API_URL = f'https://minecraft-italia.net/lista/api/vote/server?serverId={SERVER_ID}'

intents = discord.Intents.default()

intents.message_content = True

client = commands.Bot(
    command_prefix=".",
    owner_id="777231224753750057",
    case_insensitive=True,
    intents=intents,
    help_command=None
)

try:
    with open(USERNAME_FILE, 'r') as f:
        non_votanti_dict = json.load(f)
except FileNotFoundError:
    non_votanti_dict = {}

USERNAMES_TO_CHECK = []

f = open(STAFFER_FILE, 'r+')
lines = f.readlines()
f.close()

for line in lines:
    if not line == '' or not line == ' ':
        if '\n' in line:
            line = line.replace('\n', '')
            line = line.replace('-', '')
            line = line.replace(' ', '')
            line = line.strip()

        USERNAMES_TO_CHECK.append(line)


async def controllo_auto():
    while True:
        now = datetime.now().time()
        if now >= REMINDER_TIME:
            response = requests.get(API_URL)

            if response.status_code == 200:
                data = response.json()
                message = REMINDER_MESSAGE
                voted_usernames = [vote['username'] for vote in data]

                tutti_hanno_votato = True  # Flag per verificare se tutti gli username hanno votato

                for username in USERNAMES_TO_CHECK:
                    if "[]" in username:
                        tutti_hanno_votato = False
                        for channel_id in CHANNEL_IDS:
                            channel = client.get_channel(channel_id)
                            message = await channel.send("Non ci sono ancora staffers registrati al controllo!!!")
                        break
                    if username not in voted_usernames:
                        tutti_hanno_votato = False
                        if username in non_votanti_dict:
                            non_votanti_dict[username] += 1
                        else:
                            non_votanti_dict[username] = 1
                        non_voti = non_votanti_dict[username]
                        message += f"- {username} non ha votato ({non_voti}).\n"

                if tutti_hanno_votato:
                    for channel_id in CHANNEL_IDS:
                        channel = client.get_channel(channel_id)
                        await channel.send("Tutti gli staffers registrati al controllo hanno votato!!!")
                else:
                    try:
                        for channel_id in CHANNEL_IDS:
                            channel = client.get_channel(channel_id)
                            await channel.send(message + "```")
                            with open(USERNAME_FILE, 'w') as f:
                                json.dump(non_votanti_dict, f)
                    except TypeError:
                        pass
            else:
                print(f"Errore nella richiesta. Status code: {response.status_code}")

            tomorrow = datetime.now().date() + timedelta(days=1)
            wait_seconds = (datetime.combine(tomorrow, REMINDER_TIME) - datetime.now()).total_seconds()
            await asyncio.sleep(wait_seconds)
        else:
            await asyncio.sleep(60)


@client.event
async def on_ready():
    print(f'{client.user} è online!')
    await client.change_presence(activity=discord.Game(name="akaserra/mcita-votebot"))
    while True:
        await controllo_auto()


@client.command()
@commands.has_any_role("Head Staff", "Owner")
async def addstaffer(ctx, *staffers):
    for staffer in staffers:
        if staffer in USERNAMES_TO_CHECK:
            await ctx.reply(f"**❌ • {staffer} è già presente nella lista degli staffer da sottoporrere al controllo!**")
        else:
            import yaml

            with open(STAFFER_FILE, 'r') as file:
                yaml_data = yaml.safe_load(file)

            yaml_data.append(staffer)

            with open(STAFFER_FILE, 'w') as file:
                yaml.safe_dump(yaml_data, file)

            USERNAMES_TO_CHECK.append(staffer)
            await ctx.reply(f"**✅ • D'ora in poi {staffer} verrà sottoposto al controllo dei Voti**")


@client.command()
@commands.has_any_role("Head Staff", "Owner")
async def rmvstaffer(ctx, *staffers):
    import yaml

    with open(STAFFER_FILE, 'r') as file:
        yaml_data = yaml.safe_load(file)

        for staffer in staffers:
            try:
                yaml_data.remove(staffer)

                with open(STAFFER_FILE, 'w') as file:
                    yaml.safe_dump(yaml_data, file)

                with open(USERNAME_FILE, 'r') as file:
                    data = json.load(file)

                if staffer in data:
                    del data[staffer]

                with open(USERNAME_FILE, 'w') as file:
                    json.dump(data, file)

                USERNAMES_TO_CHECK.remove(staffer)
                await ctx.reply(f"**❌ • D'ora in poi {staffer} non verrà più sottoposto al controllo dei Voti**")
            except ValueError:
                await ctx.reply(f"**❌ • {staffer} non è ancora stato registrato al controllo!**")


@client.command()
async def staffers(ctx):
    with open('staffer.yaml', 'r') as file:
        yaml_data = yaml.safe_load(file)

    staffers = ''
    for staffer in yaml_data:
        if "[]" in staffer:
            await ctx.send(f"No")
        else:
            staffers += f'- {staffer}\n'

            await ctx.send(f"Ecco tutti gli staffers registrati:```\n{staffers}```")


@client.command()
@commands.has_any_role("Head Staff", "Owner")
async def controllo(ctx):
    response = requests.get(API_URL)

    if response.status_code == 200:
        data = response.json()
        message = REMINDER_MESSAGE
        voted_usernames = [vote['username'] for vote in data]

        tutti_hanno_votato = True  # Flag per verificare se tutti gli username hanno votato

        for username in USERNAMES_TO_CHECK:
            if "[]" in username:
                tutti_hanno_votato = False
                message = await ctx.send("Non ci sono ancora staffer registrati al controllo!!!")
                break
            if username not in voted_usernames:
                tutti_hanno_votato = False
                non_voti = non_votanti_dict[username]
                message += f"- {username} non ha votato ({non_voti}).\n"

        if tutti_hanno_votato:
            message = await ctx.send("Tutti gli staffer registrati al controllo hanno votato!!!")

        for channel_id in CHANNEL_IDS:
            try:
                channel = client.get_channel(channel_id)
                await channel.send(message + "```")
            except TypeError:
                pass
    else:
        print(f"Errore nella richiesta. Status code: {response.status_code}")



client.run(TOKEN)
