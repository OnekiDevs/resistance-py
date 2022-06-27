import discord
import traceback
from . import View, decorators


class ReportBug(View):
    def __init__(self, context = None, **kwargs):
        super().__init__(context, **kwargs)
        self.error = None

    async def get_data(self, *, error: Exception):
        self.error = error
        
    async def get_content(self, *args) -> str:
        return f"{self.error.__class__.__name__}: {self.error}"

    @decorators.button(label="Report Bug", emoji="🪲", style=discord.ButtonStyle.red)
    @decorators.disable_when_pressed
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        await interaction.response.send_message("Reporting...", ephemeral=True)
        
        msg_error = "".join(traceback.format_exception(type(self.error), self.error, self.error.__traceback__))
        embed = discord.Embed(
            description=f"```py\n{msg_error}\n```",
            colour=discord.Colour.blue(), 
            timestamp=discord.utils.utcnow()
        ).set_author(name="Bug Reported", icon_url=interaction.user.avatar.url)
        
        await interaction.client.debug_channel.send(embed=embed)
        return {}


class CauseError(View):
    @decorators.button(label="Click to cause error", emoji="🪲", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        raise TypeError("an intentional error")
    