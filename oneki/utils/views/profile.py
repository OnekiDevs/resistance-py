import utils
from utils.context import Context


class View(utils.discord.ui.View): 
    def __init__(self, ctx, member: utils.discord.Member, timeout: float = 180):
        super().__init__(timeout=timeout)
        self.ctx: Context = ctx
        self.member = member
        
        self.translation = self.ctx.bot.translations.interaction(self.ctx.lang, "profile")

    @utils.discord.ui.button(label="Avatar", style=utils.discord.ButtonStyle.secondary)
    async def avatar(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        button.style = utils.discord.ButtonStyle.success
        avatar = self.member.guild_avatar.url if self.member.guild_avatar is not None else self.member.avatar.url
        translation = self.translation["avatar"]
        
        embed = utils.discord.Embed(colour=self.member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation["embed"]["author"].format(self.member), url=avatar)
        embed.set_image(url=avatar)
        embed.set_footer(text=translation["embed"]["footer"].format(self.ctx.author.name), icon_url=self.ctx.author.avatar.url)

        await interaction.response.edit_message(embed=embed)
        
    @utils.discord.ui.button(label="Banner", emoji="🖼️", style=utils.discord.ButtonStyle.secondary)
    async def banner(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        button.style = utils.discord.ButtonStyle.success
        translation = self.translation["banner"]
        banner = self.member.banner.url if self.member.banner is not None else "https://media.discordapp.net/attachments/885674115946643463/931022708030980126/Nuevo_proyecto.png"
        
        embed = utils.discord.Embed(colour=self.member.color, timestamp=utils.utcnow())
        embed.set_author(name=translation["embed"]["author"].format(self.member), url=banner)
        embed.set_image(url=banner)
        embed.set_footer(text=translation["embed"]["footer"].format(self.ctx.author.name), icon_url=self.ctx.author.avatar.url)

        await interaction.response.edit_message(embed=embed)
        
    @utils.discord.ui.button(label="Information", emoji="📑", style=utils.discord.ButtonStyle.secondary)
    async def information(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        button.style = utils.discord.ButtonStyle.success
        translation = self.translation["info"]
        try: roles = "".join([role.mention for role in self.member.roles])
        except: roles = translation['no_roles']
        
        embed = utils.discord.Embed(
            title=translation["embed"]["title"],
            description=roles,
            color=self.member.color,
            timestamp=utils.utcnow(), 
        )
        embed.set_author(name=f"{self.member}", url=self.member.avatar.url)
        embed.set_thumbnail(url=self.member.avatar.url)
        
        if self.member.activity is not None: 
            activity = self.member.activity if isinstance(self.member.activity, utils.discord.CustomActivity) else self.member.activity.name
            embed.add_field(name=translation["embed"]["fields"][0], value=f"```{activity}```", inline=False)
        
        embed.add_field(name=translation["embed"]["fields"][1], value=f"```{self.member.created_at}```")
        embed.add_field(name=translation["embed"]["fields"][2], value=f"```{self.member.joined_at}```")
        embed.add_field(name=translation["embed"]["fields"][3], value=f"```{self.member.color}```")
        embed.add_field(name=translation["embed"]["fields"][4], value=f"```{self.member.id}```")
        embed.add_field(name=translation["embed"]["fields"][5], value=f"```{self.member.raw_status}```")
        
        embed.set_footer(text=translation["embed"]["footer"].format(self.ctx.author.name), icon_url=self.ctx.author.avatar.url)
        
        await interaction.response.edit_message(embed=embed)