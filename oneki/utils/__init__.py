# Librerias importantes
import discord
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