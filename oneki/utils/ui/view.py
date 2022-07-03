import discord
from discord import ui 
from ..context import Context
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..translations import Translation


def _can_be_disabled(item):
    return hasattr(item, "disabled")


class View(ui.View):
    TIMEOUT = 320
    name: Optional[str] = None
    
    def __init__(self, context: Optional[Context] = None, *, timeout: Optional[float] = TIMEOUT, **kwargs):
        super().__init__(timeout=timeout)
        
        self.ctx = context
        self.msg: Optional[discord.Message] = None
        self.embed: Optional[discord.Embed] = None
        
        self.translations: Optional[Translation] = None
        self._disabled = False
        
        self.kwargs = kwargs
        
    async def get_data(self, **kwargs): 
        return None
        
    async def get_content(self, *args) -> Optional[str]:
        return None
        
    async def get_embed(self, *args) -> Optional[discord.Embed]:
        return None # this is optional to implement
        
    async def update_components(self, *args):
        pass # this implementation is also optional
        
    async def process_data(self):
        data = await discord.utils.maybe_coroutine(self.get_data, **self.kwargs)
        if not isinstance(data, tuple):
            data = (data,)

        content = await discord.utils.maybe_coroutine(self.get_content, *data)
        self.embed = await discord.utils.maybe_coroutine(self.get_embed, *data)
        await discord.utils.maybe_coroutine(self.update_components, *data)
         
        return {"content": content, "embed": self.embed, "view": self}
        
    async def start(self, interaction: Optional[discord.Interaction] = None, *, ephemeral = False):
        if self.name is not None:
            self.translations: Translation = interaction.client.translations.view(interaction.locale.value, self.name) if interaction is not None else self.ctx.cog.translations.view(self.ctx.lang, self.name)
        
        kwargs = await self.process_data()
        kwargs["ephemeral"] = ephemeral
        
        if interaction is not None:
            await interaction.response.send_message(**kwargs)
            self.msg = await interaction.original_message()
        else:
            self.msg = await self.ctx.send(**kwargs)
        
    async def update(self):
        kwargs = await self.process_data()
        
        if self.msg is None:
            raise RuntimeError("can't update view without start")
        
        await self.msg.edit(**kwargs)
            
    def _disable_children(self):
        for item in self.children:
            if _can_be_disabled(item):
                item.disabled = True
        
    async def disable(self, **kwargs):
        if self._disabled:
            return
        
        self.stop()
        self._disabled = True
        self._disable_children()
        
        if self.msg is None:
            raise RuntimeError("can't disable view without start")

        await self.msg.edit(view=self, **kwargs)
        
    async def on_error(self, interaction: discord.Interaction, error: Exception, item) -> None:
        await super().on_error(interaction, error, item)
        
        from .report_bug import ReportBug
        view = ReportBug(error=error)
        await view.start(interaction)
        
    async def on_timeout(self) -> None:
        await self.disable()
        
        
class _StopButton(discord.ui.Button):
    async def callback(self, interaction):
        view = self.view
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
    