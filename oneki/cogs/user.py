import utils
from utils.context import Context


class User(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @utils.commands.command()
    async def avatar(self, ctx: Context, member : utils.discord.Member=None):
        member = ctx.author if member == None else member
        avatar = member.guild_avatar.url if member.guild_avatar is not None else member.avatar.url
        
        embed = utils.discord.Embed(colour=member.color, timestamp=utils.datetime.datetime.utcnow())
        embed.set_author(name=ctx.translation["embed"]["author"].format(member), url=avatar)
        embed.set_image(url=avatar)
        embed.set_footer(text=ctx.translation["embed"]["footer"].format(ctx.author.name), icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(User(bot))