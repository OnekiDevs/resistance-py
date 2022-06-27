import discord
from discord import app_commands
from discord.ext import commands

import datetime
import math
import asyncio 
import random
import re

from .cog import Cog


utcnow = discord.utils.utcnow
is_empty = lambda data_structure: False if data_structure else True

def check_links(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    return re.findall(regex, string)

color_hex = lambda _hex: int(hex(int(_hex.replace("#", ""), 16)), 0)

def filled_bar(current: int, *, len = 25) -> str:
    progress = math.floor((current / 100) * len)
    return "".join(["█" for _ in range(0, progress)]) + "".join([" " for _ in range(0, len - progress)])

async def send_file_and_get_url(bot, file: discord.File):
    channel = await bot.fetch_channel(885674115946643456)
    message = await channel.send(file=file) 
    return message.attachments[0]
    