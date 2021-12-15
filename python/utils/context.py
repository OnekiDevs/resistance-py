from discord.ext import commands
import discord
# import discord_slash

import datetime
import traceback


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

    @property
    def debug_channel(self) -> discord.TextChannel:
        # Debug channel
        return self.bot.get_channel(885674115615301651)

    async def log(self, message):
        message = f"log: \n`{message}`\ncommand: `{self.command}`\ntimestamp: `{datetime.datetime.utcnow()}`"
        print(message)

        await self.debug_channel.send(message)
