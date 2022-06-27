from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bot import OnekiBot
    from .translations import Translations


class Cog(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: OnekiBot = bot
        self.translations: Translations = bot.translations
        