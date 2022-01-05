import utils
from utils.context import Context


class User(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @utils.commands.command()
    async def avatar(self, ctx: Context, member: utils.discord.Member=None):
        member = ctx.author if member == None else member
        avatar = member.guild_avatar.url if member.guild_avatar is not None else member.avatar.url
        
        embed = utils.discord.Embed(colour=member.color, timestamp=utils.datetime.datetime.utcnow())
        embed.set_author(name=ctx.translation["embed"]["author"].format(member), url=avatar)
        embed.set_image(url=avatar)
        embed.set_footer(text=ctx.translation["embed"]["footer"].format(ctx.author.name), icon_url=ctx.author.avatar.url)

        await ctx.send(embed=embed)

    @utils.commands.command()
    async def info(self, ctx: Context, member: utils.discord.Member=None):
        member = ctx.author if member == None else member
        try: roles = "".join([role.mention for role in member.roles])
        except: roles = ctx.translation['no_roles']
        
        embed = utils.discord.Embed(
            title=ctx.translation["embed"]["title"],
            description=roles,
            color=member.color,
            timestamp=utils.datetime.datetime.utcnow(), 
        )
        embed.set_author(name=f"{member}", url=member.avatar.url)
        embed.set_thumbnail(url=member.avatar.url)
        
        if member.activity is not None: 
            activity = member.activity if isinstance(member.activity, utils.discord.CustomActivity) else member.activity.name
            embed.add_field(name=ctx.translation["embed"]["fields"][0], value=f"```{activity}```", inline=False)
        
        embed.add_field(name=ctx.translation["embed"]["fields"][1], value=f"```{member.created_at}```")
        embed.add_field(name=ctx.translation["embed"]["fields"][2], value=f"```{member.joined_at}```")
        embed.add_field(name=ctx.translation["embed"]["fields"][3], value=f"```{member.color}```")
        embed.add_field(name=ctx.translation["embed"]["fields"][4], value=f"```{member.id}```")
        embed.add_field(name=ctx.translation["embed"]["fields"][5], value=f"```{member.raw_status}```")
        
        embed.set_footer(text=ctx.translation["embed"]["footer"].format(ctx.author.name), icon_url=ctx.author.avatar.url)

        await ctx.send(embed = embed)


def setup(bot):
    bot.add_cog(User(bot))