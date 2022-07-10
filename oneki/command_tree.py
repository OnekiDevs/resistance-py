import traceback
import sys

import discord
from discord import app_commands
from utils.ui import ReportBug


class CommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        err = getattr(error, "original", error)
        if isinstance(err, app_commands.CommandNotFound): 
            return
        elif not isinstance(err, (discord.HTTPException, app_commands.CheckFailure)): 
            view = ReportBug(error=err)
            await view.start(interaction)
        else:
            await interaction.response.send_message(f"{err.__class__.__name__}: {err}")

        print(f"In {interaction.command.qualified_name}:", file=sys.stderr)
        traceback.print_tb(err.__traceback__)
        print(f"{err.__class__.__name__}: {err}", file=sys.stderr)
        
