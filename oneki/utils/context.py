import aiohttp
import discord
import datetime
from discord.ext import commands
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
        return self.bot.get_guild_lang(str(self.guild.id))

    @property
    def translation(self) -> dict:
        return self.bot.translations.command(self.lang, self.command.name)

    @property
    def debug_channel(self) -> discord.TextChannel:
        # Debug channel
        return self.bot.get_channel(885674115615301651)

    async def log(self, message):
        timestamp = datetime.datetime.utcnow()

        print(f"log: \n{message}\ncommand: {self.command}\ntimestamp: {timestamp}")
        await self.debug_channel.send(f"log: \n`{message}`\ncommand: `{self.command}`\ntimestamp: `{timestamp}`")
        
    