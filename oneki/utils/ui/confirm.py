import discord
from view import View
import decorators 
from typing import Coroutine, Any, Optional


class View(View):
    """
    example:
        async def confirmed(translation):
            ...
        
        async def cancelled(translation):
            ...
        
        view = confirm.View(confirmed=confirmed, cancelled=cancelled)
        view.NAME = ""
        view.start()
    """
    def __init__(self, context = None, *, confirmed: Optional[Coroutine[Any, Any, dict]] = None, cancelled: Optional[Coroutine[Any, Any, dict]] = None):
        super().__init__(context)
        self.value = None
        
        self.confirmed = confirmed
        self.cancelled = cancelled

    @decorators.button(label="Confirm", style=discord.ButtonStyle.red)
    @decorators.disable_when_pressed
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button, translation):
        await interaction.response.send_message("Confirming", ephemeral=True)
        self.value = True
        
        if self.confirmed is not None:
            return await self.confirmed(translation)
        
        return {}

    @decorators.button(label="Cancel", style=discord.ButtonStyle.grey)
    @decorators.disable_when_pressed
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button, translation):
        await interaction.response.send_message("Cancelling", ephemeral=True)
        self.value = False
        
        if self.cancelled is not None:
            return await self.cancelled(translation)
        
        return {}
