import utils
from utils import ui
from utils.context import Context

import os
from PIL import Image
from typing import Optional


def avatar_embed(ctx, member, translation):
    member = member or ctx.author
    avatar = member.guild_avatar.url if member.guild_avatar is not None else member.avatar.url
    
    embed = utils.discord.Embed(colour=member.color, timestamp=utils.utcnow())
    embed.set_author(name=translation.embed.author.format(member), url=avatar)
    embed.set_image(url=avatar)
    embed.set_footer(text=translation.embed.footer.format(ctx.author.name), icon_url=ctx.author.avatar.url)
    
    return embed


def info_embed(ctx, member, translation):
    roles = "".join([role.mention for role in member.roles])

    embed = utils.discord.Embed(
        title=translation.embed.title,
        description=roles,
        color=member.color,
        timestamp=utils.utcnow(), 
    )
    embed.set_author(name=f"{member}", url=member.avatar.url)
    embed.set_thumbnail(url=member.avatar.url)
    
    if member.activity is not None: 
        activity = member.activity if isinstance(member.activity, utils.discord.CustomActivity) else member.activity.name
        embed.add_field(name=translation.embed.fields[0], value=f"```{activity}```", inline=False)
    
    embed.add_field(name=translation.embed.fields[1], value=utils.discord.utils.format_dt(member.created_at, "F"))
    embed.add_field(name=translation.embed.fields[2], value=utils.discord.utils.format_dt(member.joined_at, "F"))
    embed.add_field(name=translation.embed.fields[3], value=f"```{member.color}```")
    embed.add_field(name=translation.embed.fields[4], value=f"```{member.id}```")
    embed.add_field(name=translation.embed.fields[5], value=f"```{member.raw_status}```")
    
    embed.set_footer(text=translation.embed.footer.format(ctx.author.name), icon_url=ctx.author.avatar.url)
    
    return embed


class Profile(ui.ExitableView):
    NAME = "profile"
    DEFAULT_BANNER = "https://media.discordapp.net/attachments/885674115946643463/931022708030980126/Nuevo_proyecto.png"
    
    def __init__(self, context: Context, **kwargs):
        super().__init__(context, **kwargs)
        self.member = kwargs["member"]
    
    async def get_data(self, *, member: utils.discord.Member):
        return member
    
    async def get_embed(self, member: utils.discord.Member) -> utils.discord.Embed:
        if member.banner is None:
            path = f"resource/img/default_banner_{member.id}.png"
            default_banner = Image.new("RGB", (600, 240), member.colour.to_rgb())
            default_banner = default_banner.save(path)
            with open(path, "rb") as f:
                banner = await utils.send_file_and_get_url(self.ctx.bot, utils.discord.File(fp=f))
                
            os.remove(path)
        else:
            banner = member.banner.url
        
        embed = utils.discord.Embed(colour=member.color, timestamp=utils.utcnow())
        embed.set_author(name=self.translations.embed.author.format(member))
        embed.set_image(url=banner)
        embed.set_footer(text=self.translations.embed.footer.format(self.ctx.author.name), icon_url=self.ctx.author.avatar.url)
        
        return embed
    
    @ui.button(label="Avatar", style=utils.discord.ButtonStyle.secondary)
    @ui.change_color_when_used
    async def avatar(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        embed = avatar_embed(self.ctx, self.member, translation)
        await interaction.response.edit_message(embed=embed, view=self)
        
    @ui.button(label="Banner", emoji="🖼️", style=utils.discord.ButtonStyle.secondary)
    @ui.change_color_when_used
    async def banner(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        banner = self.member.banner.url if self.member.banner is not None else self.DEFAULT_BANNER
        
        embed = utils.discord.Embed(colour=self.member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation.embed.author.format(self.member), url=banner)
        embed.set_image(url=banner)
        embed.set_footer(text=translation.embed.footer.format(self.ctx.author.name), icon_url=self.ctx.author.avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)
        
    @ui.button(label="Information", emoji="📑", style=utils.discord.ButtonStyle.secondary)
    @ui.change_color_when_used
    async def information(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation):
        embed = info_embed(self.ctx, self.member, translation)
        await interaction.response.edit_message(embed=embed, view=self)
        
        
class User(utils.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.afks = {}
        
    async def cog_load(self):
        self.afks = await self._get_afks()
        
    async def _get_afks(self):
        # user_id: dict(reason, time)
        afks = {}

        doc = await self.bot.db.document("users/afks").get()
        if doc.exists:
            for key, value in doc.to_dict().items():
                afks[key] = value
        
        return afks
    
    @utils.commands.hybrid_command()
    async def profile(self, ctx: Context, member: Optional[utils.discord.Member] = None):
        member = member or ctx.author
        view = Profile(ctx, member=member)
        await view.start() 
        
    @utils.commands.hybrid_command()
    async def avatar(self, ctx: Context, member: Optional[utils.discord.Member] = None):
        member = member or ctx.author
        embed = avatar_embed(ctx, member, ctx.translation)

        await ctx.send(embed=embed)
       
    @utils.commands.hybrid_command()
    async def info(self, ctx: Context, member: Optional[utils.discord.Member] = None):
        member = member or ctx.author
        embed = info_embed(ctx, member, ctx.translation)
        
        await ctx.send(embed=embed)
        
    # afk

    async def add_to_afk(self, user_id, *, reason):
        data = {"reason": reason, "time": utils.utcnow()}
        self.afks[str(user_id)] = data
        
        doc_ref = self.bot.db.document("users/afks")
        doc = await doc_ref.get()
        if doc.exists:
            await doc_ref.update({str(user_id): data})
        else:
            await doc_ref.set(self.afks)

    async def remove_from_afk(self, user_id):
        self.afks.pop(str(user_id))
        
        doc_ref = self.bot.db.document("users/afks")
        await doc_ref.delete(str(user_id))

    @utils.commands.hybrid_command()
    async def afk(self, ctx: Context, *, reason=None):
        member = ctx.author
        if str(member.id) in self.afks:
            translation = self.bot.translations.event(ctx.lang, "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation.no_longer_afk.format(member.display_name), color=0xFCE64C)
            return await ctx.send(embed=embed)
            
        reason = reason or ctx.translation.no_reason
        if len(reason) > 50: 
            return await ctx.send(ctx.translation.too_long)
        
        if utils.check_links(reason): 
            return await ctx.send(ctx.translation.no_links)

        await self.add_to_afk(member.id, reason=reason)
        embed = utils.discord.Embed(title=ctx.translation.embed.title.format(member.display_name), color=0x383FFF)
        if len(member.display_name) >= 27: 
            ctx.send(ctx.translation.max_name_length.format(member.mention))
        else: 
            try:
                await member.edit(nick=f"[AFK] {member.display_name}")
            except utils.discord.errors.Forbidden:
                await ctx.send(ctx.translation.no_permissions)
                
        await ctx.send(embed=embed)
    
    @utils.Cog.listener()
    async def on_message(self, message: utils.discord.Message):
        # if the user is afk
        if str(message.author.id) in self.afks:
            ctx = await self.bot.get_context(message)
            if ctx.valid and ctx.command == self.bot.get_command("afk"): 
                return 
            
            member = message.author
            translation = self.bot.translations.event(self.bot.get_guild_lang(message.guild), "afk")

            await self.remove_from_afk(member.id)
            try:
                await member.edit(nick=member.display_name.replace("[AFK] ", ""))
            except: pass
            
            embed = utils.discord.Embed(title=translation.no_longer_afk.format(member.display_name), color=0xFCE64C)
            await message.channel.send(embed=embed, delete_after=10.0)

        # is there a mention of an afk user?
        if message.mentions:
            translation = self.bot.translations.event(self.bot.get_guild_lang(message.guild), "afk")
            for user in message.mentions:
                if str(user.id) in self.afks:
                    data = self.afks[str(user.id)]
                    embed = utils.discord.Embed(
                        title=translation.embed.title.format(user.display_name),
                        description=translation.embed.reason.format(data["reason"]),
                        timestamp=data["time"],
                        color=0xFCE64C
                    )
                    await message.channel.send(embed=embed, delete_after=15.0)
        
        
async def setup(bot):
    await bot.add_cog(User(bot))
        