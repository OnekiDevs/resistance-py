import utils
from utils.context import Context


class Country(utils.discord.ui.Select):
    def __init__(self, embed):
        countries = {
            "Venezuela", 
            "Colombia", 
            "Ecuador", 
            "Argentina", 
            "EE.UU", 
            "México", 
            "Chile", 
            "Trinidad y Tobago", 
            "Puerto Rico", 
            "Brasil", 
            "El Salvador", 
            "Paraguay", 
            "Uruguay", 
            "Nicaragua", 
            "Japon", 
            "España", 
            "República Domina", 
            "Guatemala", 
            "Peru", 
            "Bolivia", 
            "Panamá" 
        }
                
        options = []
        for country in countries:
            options.append(utils.discord.SelectOption(label=country, description=f"Actualmente resides en {country}"))

        super().__init__(placeholder='Elije tu País de residencia ...', min_values=1, max_values=1, options=options)
        self.embed: utils.discord.Embed = embed

    async def callback(self, interaction: utils.discord.Interaction):
        try: 
            self.embed.set_field_at(0, name="País de residencia:", value=f"```{self.values[0]}```", inline=True)
        except:
            self.embed.insert_field_at(0, name="País de residencia:", value=f"```{self.values[0]}```", inline=True)
        await interaction.response.edit_message(embed=self.embed)


class Question(utils.discord.ui.Select):
    def __init__(self, embed):
        options = [
            utils.discord.SelectOption(label="Diversion", emoji="🥳"),
            utils.discord.SelectOption(label="Por el nitro", emoji="🤑"),
            utils.discord.SelectOption(label="Ambas", emoji="👍")
        ]
        
        super().__init__(placeholder='¿Por que participas?', min_values=1, max_values=1, options=options)
        self.embed: utils.discord.Embed = embed
        
    async def callback(self, interaction: utils.discord.Interaction):
        try:
            self.embed.set_field_at(1, name="¿Por que participas?:", value=f"```{self.values[0]}```", inline=True)
        except:
            self.embed.insert_field_at(1, name="¿Por que participas?:", value=f"```{self.values[0]}```", inline=True)
        await interaction.response.edit_message(embed=self.embed)
        

class Form(utils.discord.ui.View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx: Context = ctx
        self.embed: utils.discord.Embed = utils.discord.Embed(title='Formulario', colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
        
        self.country = Country(self.embed)
        self.add_item(self.country)
        
        self.question = Question(self.embed)
        self.add_item(self.question)
        
    @utils.discord.ui.button(label='Enviar', style=utils.discord.ButtonStyle.red)
    async def send(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        document = utils.db.Document(collection="tournamentc", document="participants")

        if len(document.content) >= 32:
            await interaction.response.send_message("Ups!, ya se lleno el limite de inscripciones :(\nSe mas rapido la proxima vez!")
            return await self.ctx.message.add_reaction('❌')

        if utils.is_empty(self.country.values) or utils.is_empty(self.question.values):
            return await interaction.response.send_message('Creo que te falta contestar el formulario <:awita:852216204512329759>', ephemeral=True)

        document.update(str(self.ctx.author.id), {"name": f"{self.ctx.author.name}#{self.ctx.author.discriminator}", 
                                                  "pfp": self.ctx.author.avatar.url,
                                                  "country": self.country.values[0],
                                                  "question": self.question.values[0]})

        for role in self.ctx.guild.roles:
            if role.id == 912816678818172968:
                await self.ctx.author.add_roles(role)
        
        await interaction.response.send_message("Listo! , se envio tu inscripción correctamente :D\nAhora toca esperar las indicaciones de los admins :)", ephemeral=True)
        await self.ctx.message.add_reaction('✔')

        avatar = self.ctx.author.guild_avatar.url if self.ctx.author.guild_avatar is not None else self.ctx.author.avatar.url
        channel = self.ctx.bot.get_channel(911764720481107989)

        embed = utils.discord.Embed(title = "Nuevo Jugador Inscrito", description = f"{self.ctx.author.mention} ahora es un rival más", color = utils.discord.Colour.blue())
        embed.set_thumbnail(url=avatar)
        embed.set_image(url="https://cdn.discordapp.com/attachments/850419367573061653/913920854709129326/unknown.png")
        embed.set_author(name = f"{self.ctx.author.name}#{self.ctx.author.discriminator}", icon_url = self.ctx.author.avatar.url)
        await channel.send(embed = embed)

        self.stop()

    async def on_timeout(self):
        await self.ctx.author.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")


class Tournament_Chess(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @utils.commands.command(hidden=True)
    async def inscription(self, ctx: Context):
        if ctx.guild is None:
            return

        form = Form(ctx)
        await ctx.author.send("Pronto estará lista tu inscripción al torneo!, solo necesitamos que llenes este pequeño formulario:", embed=form.embed, view = form)

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def participants(self, ctx: Context):
        document = utils.db.Document(collection="tournamentc", document="participants")
        
        num = 1
        for user_id, data in document.content.items():
            embed: utils.discord.Embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name=data.get('name'), icon_url=data.get('pfp'))
            
            embed.add_field(name="ID:", value=f"`{user_id}`")
            embed.add_field(name="Country:", value=f"`{data.get('country')}`")
            embed.add_field(name="Question:", value=f"`{data.get('question')}`")
            
            await ctx.send(f"#{num}", embed=embed)
            num += 1
        

def setup(bot):
    bot.add_cog(Tournament_Chess(bot))
