import aiohttp
import discord
import datetime
from typing import Optional, Union
from discord.ext import commands
from utils.db import AsyncClient


class BaseContext:
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
    

class Context(commands.Context, BaseContext):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

class Ctx(BaseContext):
    def __init__(self, author, channel, command, bot) -> None:
        self.author: Union[discord.User, discord.Member] = author
        self.guild: Optional[discord.Guild] = channel.guild
        self.channel: discord.abc.MessageableChannel = channel
        self.command = command
        self.bot = bot
        
    @classmethod
    def from_context(cls, ctx: Context):
        return cls(ctx.author, ctx.channel, ctx.command, ctx.bot)
        
    @classmethod
    def from_interaction(cls, interaction: discord.Interaction):
        return cls(interaction.user, interaction.channel, interaction.command,interaction.client)
    