from discord.ext import commands


class Cog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        self.translations = bot.translations
    