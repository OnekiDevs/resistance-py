from discord.ext import commands
import aiohttp
import discord
import datetime


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    @property
    def session(self) -> aiohttp.ClientSession:
        return self.bot.session

    @property
    def lang(self):
        return self.bot.get_guild_lang(str(self.guild.id))

    @property
    def translation(self) -> dict:
        return self.bot.translations.command(self.lang, self.command)

    @property
    def debug_channel(self) -> discord.TextChannel:
        # Debug channel
        return self.bot.get_channel(885674115615301651)

    async def log(self, message):
        timestamp = datetime.datetime.utcnow()

        print(f"log: \n{message}\ncommand: {self.command}\ntimestamp: {timestamp}")
        await self.debug_channel.send(f"log: \n`{message}`\ncommand: `{self.command}`\ntimestamp: `{timestamp}`")
