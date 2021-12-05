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
        
    @utils.discord.ui.button(label='Mandar', style=utils.discord.ButtonStyle.red)
    async def send(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        document = utils.db.Document(collection="tournamentc", document="participants")
        if len(document.content) >= 32:
            return await interaction.response.send_message("Ups!, ya se lleno el limite de inscripciones :(\nSe mas rapido la proxima vez!", ephemeral=True)
        
        document.update(str(self.ctx.author.id), {"name": f"{self.ctx.author.name}#{self.ctx.author.discriminator}", 
                                                  "pfp": self.ctx.author.avatar.url,
                                                  "country": self.country.values[0], 
                                                  "question": self.question.values[0]})
        for role in self.ctx.guild.roles:
            if role.id == 912816678818172968:
                await self.ctx.author.add_roles(role)
        
        await interaction.response.send_message("Listo! , se envio tu inscripción correctamente :D\nAhora toca esperar las indicaciones de los admins :)", ephemeral=True)
        # await self.ctx.message.add_reaction()
        self.stop()


class Tournament_Chess(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @utils.commands.command(hidden=True)
    async def inscription(self, ctx: Context):
        form = Form(ctx)
        
        await ctx.author.send("Pronto estará lista tu inscripción al torneo!, solo necesitamos que llenes este pequeño formulario:", embed=form.embed, view = form)
    
    
    # @utils.cog_ext.cog_slash(name="ping", description="un slash command de prueba")
    # async def _ping(self, ctx: SlashContext):
    #     await ctx.send("pong!")
        
    # @utils.cog_ext.cog_slash(name="test", description="xd")
    # async def _test(self, ctx: SlashContext):
    #     embed = utils.discord.Embed(title="Embed Test", description=f"Aiohttp Client Session: {ctx.session}")
    #     await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Tournament_Chess(bot))
    
