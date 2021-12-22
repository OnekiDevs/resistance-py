from discord.ext import tasks

import utils
# from utils.context import Context


class Gift(utils.discord.ui.View):
    def __init__(self):
        super().__init__()
        self.rewards = [
            lambda interaction: (await interaction.response.send_message("Toma 🍪, una galleta :D", ephemeral=True) for _ in "_").__anext__(),
        ]
        self.punishments = [
            lambda interaction: (await interaction.response.send_message("\*le pega*", ephemeral=True) for _ in "_").__anext__()
        ]
    
    @utils.discord.ui.button(label='Abrir', style=utils.discord.ButtonStyle.red)
    async def to_open(self, button: utils.discord.ui.Button, interaction: utils.discord.Interaction):
        reward_or_punishment = utils.random.sample(utils.random.choice([self.rewards, self.punishments]), k=1)[0]

        await reward_or_punishment(interaction)
        self.stop()


class Christmas(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.allowed_channels = [
            850338969135611926, # General 
            850471820493979648, # Comandos
            850373152943898644, # Memes 
            862907238673809430, # Sugerencias emojis
            871894089904295976, # Spam
            853131733918941205, # Arte
            850374620321808416, # Programación 
            884185193324355594, # Juegos 
            897305507180711946, # Anime 
            856576340115062785, # Biblioteca
            853126432305053716, # Cafeteria
            850460895053479936 # Taquilla
        ]
        
        self.gifts.start()
    
    @tasks.loop(minutes=5.0)
    async def gifts(self):
        # Extend time 
        time_sleep = utils.random.randint(0, 600)
        await utils.asyncio.sleep(time_sleep)
        
        # Select channel
        self.guild: utils.discord.Guild = await self.bot.fetch_guild(850338969135611924)
        channel = await self.guild.fetch_channel(utils.random.choice(self.allowed_channels))
        await channel.send(file=utils.discord.File(fp="resource/img/Gift-Box.jpg"), view=Gift())
    
    
def setup(bot):
    bot.add_cog(Christmas(bot))