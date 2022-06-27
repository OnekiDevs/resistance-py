import aiohttp
import discord
import datetime
from discord.ext import commands
from utils.translations import Translation
from utils.db import AsyncClient
    

class Context(commands.Context):
    @property
    def db(self) -> AsyncClient:
        return self.bot.db
        
    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def lang(self):
        if self.interaction is not None:
            return self.interaction.locale.value.split("-")[0]
        
        return self.guild.preferred_locale.value.split("-")[0]

    @property
    def translation(self) -> Translation:
        return self.cog.translations.command(self.lang, self.command.name)

    @property
    def debug_channel(self) -> discord.TextChannel:
        # Debug channel
        return self.bot.debug_channel

    async def log(self, message):
        timestamp = datetime.datetime.utcnow()

        print(f"log: \n{message}\ncommand: {self.command}\ntimestamp: {timestamp}")
        await self.debug_channel.send(f"log: \n`{message}`\ncommand: `{self.command}`\ntimestamp: `{timestamp}`")
        
    