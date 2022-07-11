import discord
from discord import ui 
from ..context import Context
from ..translations import Translation
from typing import Optional, Union

import sys
import traceback


def _can_be_disabled(item):
    return hasattr(item, "disabled")


class View(ui.View):
    TIMEOUT = 320
    user_check = True
    name: Optional[str] = None
    
    def __init__(self, context: Optional[Context] = None, *, timeout: Optional[float] = TIMEOUT, **kwargs):
        super().__init__(timeout=timeout)
        
        self.ctx = context
        self.author: Optional[discord.Member] = None
        self.msg: Optional[Union[discord.Message, discord.InteractionMessage]] = None
        self.embed: Optional[discord.Embed] = None
        
        self.translations: Optional[Translation] = None
        self._disabled = False
        
        self.kwargs = kwargs
        
    async def get_data(self, **kwargs): 
        return None
        
    async def get_content(self, *args) -> Optional[str]:
        return None
        
    async def get_embed(self, *args) -> Optional[discord.Embed]:
        return None
        
    async def update_components(self, *args):
        pass # nothing is returned in this function
        
    async def process_data(self):
        data = await discord.utils.maybe_coroutine(self.get_data, **self.kwargs)
        if not isinstance(data, tuple):
            data = (data,)

        content = await discord.utils.maybe_coroutine(self.get_content, *data)
        self.embed = await discord.utils.maybe_coroutine(self.get_embed, *data)
        await discord.utils.maybe_coroutine(self.update_components, *data)
         
        return {"content": content, "embed": self.embed, "view": self}
        
    def _get_translations(self, interaction: Optional[discord.Interaction] = None) -> Translation:
        if self.name is not None:
            if interaction is not None:
                return interaction.client.translations.view(interaction.locale.value, self.name)
                
            return self.ctx.bot.translations.view(self.ctx.lang, self.name)
        
    def _get_author(self, interaction: Optional[discord.Interaction] = None):
        return interaction.user if interaction is not None else self.ctx.author
        
    async def _send_view(self, interaction: Optional[discord.Interaction] = None, **kwargs) -> discord.Message:
        if interaction is not None:
            await interaction.response.send_message(**kwargs)
            return await interaction.original_message()
            
        return await self.ctx.send(**kwargs)
        
    async def start(self, interaction: Optional[discord.Interaction] = None, *, ephemeral = False):
        self.translations = self._get_translations(interaction)
        self.author = self._get_author(interaction)
        
        kwargs = await self.process_data()
        kwargs["ephemeral"] = ephemeral

        self.msg = await self._send_view(interaction, **kwargs)
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author is None:
            raise RuntimeError("can't user check can be done with unbooted view")
        
        if self.user_check:
            check = interaction.user == self.author
            if not check:
                translation = interaction.client.translations.view(interaction.locale.value, "generic")
                await interaction.response.send_message(translation.user_check.format(interaction.client.bot_emojis["enojao"]), ephemeral=True) 

            return check
        
        return True
        
    async def update(self, interaction: Optional[discord.Interaction] = None) -> Union[discord.Message, discord.InteractionMessage]:
        kwargs = await self.process_data()
        
        if self.msg is None:
            raise RuntimeError("can't update view without start")
        
        if interaction is not None:
            await interaction.response.edit_message(**kwargs) 
            return await interaction.original_message()

        return await self.msg.edit(**kwargs)
         
    def _disable_children(self):
        for item in self.children:
            if _can_be_disabled(item):
                item.disabled = True
        
    async def disable(self, **kwargs) -> Union[discord.Message, discord.InteractionMessage]:
        if self._disabled:
            return
        
        self.stop()
        self._disabled = True
        self._disable_children()
        
        if self.msg is None:
            raise RuntimeError("can't disable view without start")

        return await self.msg.edit(view=self, **kwargs)
        
    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        from .report_bug import ReportBug
        view = ReportBug(error=error)
        await view.start(interaction)
        
        print(f"In view {self} for item {item}:", file=sys.stderr)
        traceback.print_tb(error.__traceback__)
        print(f"{error.__class__.__name__}: {error}", file=sys.stderr)
        
    async def on_timeout(self) -> None:
        await self.disable()
        
        
class _StopButton(discord.ui.Button):
    async def callback(self, interaction):
        view: View = self.view
        if view is None:
            raise RuntimeError("Missing view to disable.")

        view.stop()
        view._disable_children()

        if view.msg is not None:
            await interaction.response.edit_message(view=view)
            

class ExitableView(View):
    def __init__(self, context: Optional[Context] = None, **kwargs):
        super().__init__(context=context, **kwargs)
        self.add_item(_StopButton(label="Exit", style=discord.ButtonStyle.red))


class CancellableView(View):
    def __init__(self, context: Optional[Context] = None, **kwargs):
        super().__init__(context=context, **kwargs)
        self.add_item(_StopButton(label="Cancel", style=discord.ButtonStyle.red))
    
