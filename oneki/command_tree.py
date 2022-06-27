import traceback
import sys

import discord
from discord import app_commands
from utils.ui import ReportBug


class CommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        await super().on_error(interaction, error)
        if isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                view = ReportBug(error=original)
                await view.start(interaction)
        