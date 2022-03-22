import discord


class View(discord.ui.View):
    def __init__(self, timeout) -> None:
        super().__init__(timeout=timeout)
        
        self.using_button = None
        
    def change_color(self, button):
        if self.using_button is not None:
            self.using_button.style = discord.ButtonStyle.secondary
                        
        self.using_button = button
        button.style = discord.ButtonStyle.success