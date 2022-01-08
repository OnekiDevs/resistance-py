from discord.ext import tasks
import utils
from utils.context import Context


class User(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.afks = self._get_afks()
        
    def _get_afks(self):
        # user_id: dict(reason, time)
        afks = {}

        doc_ref = self.bot.db.document("users/afks")
        async def coro(): 
            doc = await doc_ref.get()
            if doc.exists:
                for key, value in doc.to_dict().items():
                    afks[key] = value
        
        self.bot.loop.run_until_complete(coro())
        return afks
        
    @utils.commands.command()
    async def avatar(self, ctx: Context, member: utils.discord.Member=None):
        member = ctx.author if member == None else member
        avatar = member.guild_avatar.url if member.guild_avatar is not None else member.avatar.url
        
        embed = utils.discord.Embed(colour=member.color, timestamp=utils.utcnow())
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
            timestamp=utils.utcnow(), 
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

    async def add_to_afk(self, user_id, *, reason):
        data = {"reason": reason, "time": utils.utcnow()}
        self.afks[str(user_id)] = data
        
        doc_ref = self.bot.db.document("users/afks")
        doc = await doc_ref.get()
        print(doc.exists)
        if doc.exists:
            await doc_ref.update({str(user_id): data})
        else:
            await doc_ref.set(self.afks)

    async def remove_from_afk(self, user_id):
        self.afks.pop(str(user_id))
        
        doc_ref = self.bot.db.document("users/afks")
        await doc_ref.delete(str(user_id))

    @utils.commands.command()
    async def afk(self, ctx: Context, *, reason=None):
        member = ctx.author
        if str(member.id) in self.afks:
            translation = self.bot.translations.event(ctx.lang, "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation["no_longer_afk"].format(member.display_name), color=0xFCE64C)
            return await ctx.send(embed=embed)
            
        reason = reason or ctx.translation["no_reason"]
        if len(reason) > 50: 
            return await ctx.send(ctx.translation["too_long"])
        
        if utils.check_links(reason): 
            return await ctx.send(ctx.translation["no_links"])

        await self.add_to_afk(member.id, reason=reason)
        embed = utils.discord.Embed(title=ctx.translation["embed"]["title"].format(member.display_name), color=0x383FFF)
        if len(member.display_name) >= 27: 
            ctx.send(ctx.translation["max_name_length"].format(member.mention))
        else: 
            try:
                await member.edit(nick=f"[AFK] {member.display_name}")
            except utils.discord.errors.Forbidden:
                await ctx.send(ctx.translation["no_permissions"])
                
        await ctx.send(embed=embed)
    
    @utils.commands.Cog.listener()
    async def on_message(self, message: utils.discord.Message):
        # if the user is afk
        if str(message.author.id) in self.afks:
            ctx = await self.bot.get_context(message)
            if ctx.valid and ctx.command == self.bot.get_command("afk"): 
                return 
            
            member = message.author
            translation = self.bot.translations.event(self.bot.get_guild_lang(message.guild.id), "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation["no_longer_afk"].format(member.display_name), color=0xFCE64C)
            await message.channel.send(embed=embed, delete_after=10.0)

        # is there a mention of an afk user?
        if message.mentions:
            translation = self.bot.translations.event(self.bot.get_guild_lang(message.guild.id), "afk")
            for user in message.mentions:
                if str(user.id) in self.afks:
                    data = self.afks[str(user.id)]
                    embed = utils.discord.Embed(
                        title=translation["embed"]["title"].format(user.display_name),
                        description=translation["embed"]["reason"].format(data["reason"]),
                        timestamp=data["time"],
                        color=0xFCE64C
                    )
                    await message.channel.send(embed=embed, delete_after=15.0)
        

def setup(bot):
    bot.add_cog(User(bot))