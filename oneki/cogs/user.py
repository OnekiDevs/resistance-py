import utils
from PIL import Image
from io import BytesIO
from utils.context import Context
from utils.views import color


class BaseCommands:
    def __init__(self, bot) -> None:
        self.bot = bot
        
    async def profile(self, t1, t2, member: utils.discord.Member, author):
        view = ProfileView(t2, self, member, author)
        
        if member.banner is None:
            default_banner = Image.new("RGB", (600, 240), member.colour.value)
            banner = await utils.send_file_and_get_url(self.bot, utils.discord.File(
                fp=BytesIO(default_banner.tobytes()),
                filename=f"default_banner_{member.id}.png"
            ))
        else:
            banner = member.banner.url

        embed = utils.discord.Embed(colour=member.color, timestamp=utils.utcnow())
        embed.set_author(name=t1["embed"]["author"].format(member))
        embed.set_image(url=banner)
        embed.set_footer(text=t1["embed"]["footer"].format(author.name), icon_url=author.avatar.url)

        return embed, view
        
    async def avatar(self, translation, member: utils.discord.Member, author):
        avatar = member.guild_avatar.url if member.guild_avatar is not None else member.avatar.url
        
        embed = utils.discord.Embed(colour=member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation["embed"]["author"].format(member), url=avatar)
        embed.set_image(url=avatar)
        embed.set_footer(text=translation["embed"]["footer"].format(author.name), icon_url=author.avatar.url)

        return embed

    async def info(self, translation, member: utils.discord.Member, author):
        try: 
            roles = "".join([role.mention for role in member.roles])
        except: 
            roles = translation['no_roles']
        
        embed = utils.discord.Embed(
            title=translation["embed"]["title"],
            description=roles,
            color=member.color,
            timestamp=utils.utcnow(), 
        )
        embed.set_author(name=f"{member}", url=member.avatar.url)
        embed.set_thumbnail(url=member.avatar.url)
        
        if member.activity is not None: 
            activity = member.activity if isinstance(member.activity, utils.discord.CustomActivity) else member.activity.name
            embed.add_field(name=translation["embed"]["fields"][0], value=f"```{activity}```", inline=False)
        
        embed.add_field(name=translation["embed"]["fields"][1], value=f"```{member.created_at}```")
        embed.add_field(name=translation["embed"]["fields"][2], value=f"```{member.joined_at}```")
        embed.add_field(name=translation["embed"]["fields"][3], value=f"```{member.color}```")
        embed.add_field(name=translation["embed"]["fields"][4], value=f"```{member.id}```")
        embed.add_field(name=translation["embed"]["fields"][5], value=f"```{member.raw_status}```")
        
        embed.set_footer(text=translation["embed"]["footer"].format(author.name), icon_url=author.avatar.url)

        return embed


class ProfileView(color.View): 
    def __init__(self, translation, bc: BaseCommands, member: utils.discord.Member, author):
        super().__init__(timeout=180)
        self.bc = bc
        self.member = member
        self.author = author
        self.translation = translation
        
    @utils.discord.ui.button(label="Avatar", style=utils.discord.ButtonStyle.secondary)
    async def avatar(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        self.change_color(button)
        embed = await self.bc.avatar(self.translation["avatar"], self.member, self.author)
        await interaction.response.edit_message(embed=embed, view=self)
        
    @utils.discord.ui.button(label="Banner", emoji="🖼️", style=utils.discord.ButtonStyle.secondary)
    async def banner(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        self.change_color(button)
        translation = self.translation["banner"]
        banner = self.member.banner.url if self.member.banner is not None else "https://media.discordapp.net/attachments/885674115946643463/931022708030980126/Nuevo_proyecto.png"
        
        embed = utils.discord.Embed(colour=self.member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation["embed"]["author"].format(self.member), url=banner)
        embed.set_image(url=banner)
        embed.set_footer(text=translation["embed"]["footer"].format(self.author.name), icon_url=self.author.avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)
        
    @utils.discord.ui.button(label="Information", emoji="📑", style=utils.discord.ButtonStyle.secondary)
    async def information(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        self.change_color(button)
        embed = await self.bc.info(self.translation["info"], self.member, self.author)
        await interaction.response.edit_message(embed=embed, view=self)


class User(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bc = BaseCommands(bot)
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
    
    # traditional commands
    
    @utils.commands.command(name="profile")
    async def c_profile(self, ctx: Context, member: utils.discord.Member = None):
        member = member or ctx.author
        i_translation = self.bot.translations.interaction(ctx.lang, "profile")
        embed, view = await self.bc.profile(ctx.translation, i_translation, member, ctx.author)

        await ctx.send(embed=embed, view=view)

    @utils.commands.command(name="avatar")
    async def c_avatar(self, ctx: Context, member: utils.discord.Member = None):
        member = member or ctx.author
        embed = await self.bc.avatar(ctx.translation, member, ctx.author)

        await ctx.send(embed=embed)

    @utils.commands.command(name="info")
    async def c_info(self, ctx: Context, member: utils.discord.Member = None):
        member = member or ctx.author
        embed = await self.bc.info(ctx.translation, member, ctx.author)

        await ctx.send(embed=embed)

    # slash commands 

    @utils.app_commands.command(name="profile")
    async def s_profile(self, interaction: utils.discord.Interaction, member: utils.discord.Member = None):
        member = member or interaction.message.author
        t1 = self.bot.translations.command(self.bot.get_guild_lang(str(interaction.guild_id)), "profile")
        t2 = self.bot.translations.interaction(self.bot.get_guild_lang(str(interaction.guild_id)), "profile")
        embed, view = await self.bc.profile(t1, t2, member, interaction.message.author)

        await interaction.channel.send(embed=embed, view=view)

    @utils.app_commands.command(name="avatar")
    async def s_avatar(self, interaction: utils.discord.Interaction, member: utils.discord.Member = None):
        member = member or interaction.message.author
        translation = self.bot.translations.command(self.bot.get_guild_lang(str(interaction.guild_id)), "avatar")
        embed = await self.bc.avatar(translation, member, interaction.message.author)

        await interaction.channel.send(embed=embed)
        
    @utils.app_commands.command(name="info")
    async def s_info(self, interaction: utils.discord.Interaction, member: utils.discord.Member = None):
        member = member or interaction.message.author
        translation = self.bot.translations.command(self.bot.get_guild_lang(str(interaction.guild_id)), "info")
        embed = await self.bc.info(translation, member, interaction.message.author)

        await interaction.channel.send(embed=embed)

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
        

async def setup(bot):
    await bot.add_cog(User(bot))
    