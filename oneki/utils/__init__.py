# Librerias importantes
import discord
from discord import app_commands
from discord.ext import commands

# Etc
import datetime
import asyncio 
import random
import re


# Funciones utiles
utcnow = datetime.datetime.utcnow
is_empty = lambda data_structure: False if data_structure else True

def check_links(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    return re.findall(regex, string)

color_hex = lambda _hex: int(hex(int(_hex.replace("#", ""), 16)), 0)

async def send_file_and_get_url(bot, file: discord.File):
    channel = await bot.fetch_channel(885674115946643456)
    message = await channel.send(file=file) 
    return message.attachments[0]

async def delete_collection(collection_ref):
    async for doc_ref in collection_ref.list_documents():
        async for subcollection_ref in doc_ref.collections():
            async for doc in subcollection_ref.list_documents():
                await doc.delete()

        await doc_ref.delete()