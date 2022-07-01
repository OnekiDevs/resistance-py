import traceback
import sys

import discord
from discord import app_commands
from utils.ui import ReportBug


class CommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        error = getattr(error, "original", error)
        if not isinstance(error, discord.HTTPException):                
            view = ReportBug(error=error)
            await view.start(interaction)
        else:
            await interaction.response.send_message(f"{error.__class__.__name__}: {error}")

        print(f"In {interaction.command.qualified_name}:", file=sys.stderr)
        traceback.print_tb(error.__traceback__)
        print(f"{error.__class__.__name__}: {error}", file=sys.stderr)
        