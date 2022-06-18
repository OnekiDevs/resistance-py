import discord
from . import View, decorators
from typing import Coroutine, Any, Optional


class Confirm(View):
    """
    example:
        async def confirmed(interaction):
            ...
        
        async def cancelled(interaction):
            ...
        
        view = confirm.View(confirmed=confirmed, cancelled=cancelled)
        view.start()
    """
    def __init__(self, context = None, *, confirmed: Optional[Coroutine[Any, Any, dict]] = None, cancelled: Optional[Coroutine[Any, Any, dict]] = None):
        super().__init__(context)
        self.value = None
        
        self.confirmed = confirmed
        self.cancelled = cancelled

    async def start(self, interaction: Optional[discord.Interaction] = None, *, ephemeral=False):
        await super().start(interaction, ephemeral=ephemeral)
        return await self.wait()

    @decorators.button(label="Confirm", style=discord.ButtonStyle.red)
    @decorators.disable_when_pressed
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        await interaction.response.send_message("Confirming", ephemeral=True)
        self.value = True
        
        if self.confirmed is not None:
            await self.confirmed(interaction)
        
        return {}

    @decorators.button(label="Cancel", style=discord.ButtonStyle.grey)
    @decorators.disable_when_pressed
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button, _):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False
        
        if self.cancelled is not None:
            await self.cancelled(interaction)
        
        return {}
