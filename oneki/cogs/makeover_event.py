import utils
from utils import ui


class SuggestName(utils.discord.ui.Modal, title="Sugiere el nuevo nombre del servidor"):
    CHANNEL = 987158694427000882
    
    name = utils.discord.ui.TextInput(label="Nombre", placeholder="Nuevo nombre del servidor", min_length=4, max_length=32)
    reason = utils.discord.ui.TextInput(
        label="Razon del nuevo nombre", 
        placeholder="Una razon por la cual deberiamos poner este nombre",
        style=utils.discord.TextStyle.paragraph, 
        min_length=10, max_length=120
    )
    
    theme = utils.discord.ui.TextInput(
        label="Tematica", 
        placeholder="La nueva tematica que deberia tener el servidor",
        style=utils.discord.TextStyle.paragraph,
        required=False,
        min_length=4, max_length=120
    )
    
    async def on_submit(self, interaction: utils.discord.Interaction):
        channel = await interaction.client.fetch_channel(self.CHANNEL)
        embed = utils.discord.Embed(title=interaction.user)
        embed.add_field(name="Nombre sugerido", value=f"```{self.name.value}```")
        embed.add_field(name="Razon", value=f"```{self.reason.value}```")
        if self.theme.value is not None:
            embed.add_field(name="Tematica sugerida", value=f"```{self.theme.value}```", inline=False)
        
        await interaction.response.send_message("¡Gracias por participar!", ephemeral=True)
        await channel.send(embed=embed)


class Makeover(utils.commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot
        
    @utils.app_commands.command()
    async def suggest_name(self, interaction: utils.discord.Interaction): 
        await interaction.response.send_modal(SuggestName())
        

async def setup(bot):
    await bot.add_cog(Makeover(bot))