import utils
from utils.context import Context


class User(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        

def setup(bot):
    bot.add_cog(User(bot))