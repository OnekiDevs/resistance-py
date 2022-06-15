import discord
from view import View
import decorators 
from typing import Coroutine, Any


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
    def __init__(self, context = None, *, confirmed: Coroutine[Any, Any, dict], cancelled: Coroutine[Any, Any, dict]):
        super().__init__(context)
        self.value = None
        
        self.confirmed = confirmed
        self.cancelled = cancelled

    @decorators.button(label="Confirm", style=discord.ButtonStyle.red)
    @decorators.disable_when_pressed
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button, translation):
        self.value = True
        return await self.confirmed(translation)

    @decorators.button(label="Cancel", style=discord.ButtonStyle.grey)
    @decorators.disable_when_pressed
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button, translation):
        self.value = False
        return await self.cancelled(translation)
