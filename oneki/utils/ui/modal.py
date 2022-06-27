import discord
from discord import ui 
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..translations import Translation


class Modal(ui.Modal):
    modal_name: Optional[str] = None
    
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.translations: Optional[Translation] = None
    
    def get_items(self) -> dict[str, ui.Item]:
        raise NotImplementedError
    
    def add_items(self, **kwargs) -> None:
        for name, item in kwargs.items():
            translation = getattr(self.translations, name)
            if translation is not None:
                item.label = translation.label
                
                if item.placeholder is not None:
                    item.placeholder = translation.placeholder
                    
            setattr(self, name, item)
            self.add_item(item)
            
    async def start(self, interaction: discord.Interaction): 
        if self.modal_name is not None:
            self.translations: Translation = interaction.client.translations.view(interaction.locale.value, self.modal_name)
            self.title = self.translations.title
        
        items = self.get_items()
        self.add_items(**items)
        
        await interaction.response.send_modal(self)
        
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await super().on_error(interaction, error)
        
        from .report_bug import ReportBug
        view = ReportBug(error=error)
        await view.start(interaction)
