from discord.ext import commands
# import discord_slash
# import discord

import json
import datetime


class Context(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    @property
    def session(self):
        return self.bot.session

    @property
    def lang(self):
        return self.bot.get_raw_guild_lang(str(self.guild.id))

    @property
    def translation(self) -> dict:
        return self.bot.translations.command(self.lang, self.command)

    async def log(self, message, *, embed=None):
        # Debug channel
        channel = self.bot.get_channel(885674115615301651)

        if embed is not None:
            message = f"log: \n{message}\ncommand: {self.command}\ntimestamp: {datetime.datetime.utcnow()}"
            print(message)

        await channel.send(message, embed=embed)
  
