import traceback
import aiohttp
import sys

import utils
from utils import context, env
from utils.translations import Translations


description = """
Hola!, soy Oneki un bot multitareas y estare muy feliz en ayudarte en los que necesites :D
"""

initial_extensions = (
    "cogs.events.tournamentc",
    "cogs.events.christmas",

    "cogs.user",
)


def _prefix_callable(bot, msg):
    user_id = bot.user.id
    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('?')
        base.append('>')
    else:
        base.extend(bot.prefixes.get(str(msg.guild.id), ['?', '>']))
    return base


class OnekiBot(utils.commands.AutoShardedBot):
    def __init__(self):
        allowed_mentions = utils.discord.AllowedMentions(roles=False, everyone=False, users=True)
        intents = utils.discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            voice_states=True,
            messages=True,
            reactions=True,
            typing=True,
        )
        super().__init__(
            command_prefix=_prefix_callable,
            description=description,
            allowed_mentions=allowed_mentions,
            intents=intents,
        )
        
        # self.slash = utils.discord_slash.SlashCommand(self, sync_commands=True, sync_on_cog_reload=True)
        self.translations = Translations()
        self.session = aiohttp.ClientSession(loop=self.loop)

        # prefixes[guild_id]: list
        # languages[guild_id]: str(lang)
        self.prefixes, self.languages = self._configurations()

        # user_id mapped to True
        # these are users globally blacklisted
        self.blacklist = set(utils.db.Document(collection="config", document="bot").content.get("blacklist"))

        # cogs unload
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()


    @staticmethod
    def _configurations():
        # guild_id: list
        prefixes = {}
        # guild_id: str(lang)
        languages = {}
        
        collection = utils.db.Collection("config")
        for document in collection.documents():
            content = document.content
            if utils.is_empty(content):
                continue
            else:
                if content.get("prefixes", None) is not None:
                    prefixes[document.id] = content.get("prefixes", None)
                    
                if content.get("lang", None) is not None:
                    languages[document.id] = content.get("lang", None)

        return prefixes, languages

    def get_guild_prefixes(self, guild, *, local_inject=_prefix_callable):
        proxy_msg = utils.discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(str(guild_id), ['?', '>'])

    def get_raw_guild_lang(self, guild_id):
        return self.languages.get(str(guild_id), "en")

    def add_to_blacklist(self, object_id):
        utils.db.Document(collection="config", document="bot").update("blacklist", str(object_id), array=True)
        self.blacklist.add(str(object_id))

    def remove_from_blacklist(self, object_id):
        utils.db.Document(collection="config", document="bot").delete("blacklist", str(object_id), array=True)
        self.blacklist.remove(str(object_id))

    async def on_ready(self):
        activity = utils.discord.Activity(type=utils.discord.ActivityType.watching, name=f"{len(self.guilds)} servidores")
        await self.change_presence(status=utils.discord.Status.idle, activity=activity)

        print(f'[+] Ready: {self.user} (ID: {self.user.id})')

    async def on_command_error(self, ctx, error):
        if isinstance(error, utils.commands.errors.CommandNotFound): 
            pass
        else: 
            # Error message
            msg = "".join(traceback.format_exception(type(error), error, error.__traceback__))

            # Embed
            embed = utils.discord.Embed(color=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name="Error", url=f"{ctx.message.jump_url}")
            embed.add_field(name="Type:", value=f"```{type(error)}```", inline = False)
            embed.add_field(name="Message:", value=f"```{ctx.message.content}```")
            embed.add_field(name="Detail:", value=f"```{error}```", inline = False)

            # Send message
            channel = self.get_channel(885674115615301651)
            await ctx.send(error)
            
            print('Ignoring exception in command {}:'.format(ctx.command))
            traceback.print_exception(type(error), error, error.__traceback__)
            
            await channel.send(f"**Context:**\n```py\n{msg}\n```", embed=embed)

    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=context.Context)

        if message.author.bot:
            return

        if ctx.author.id in self.blacklist:
            return

        await self.invoke(ctx)

    async def on_message(self, message):
        if message.author.bot:
            return

        # Si pingearon al bot
        if message.content == f"<@!{self.user.id}>" or message.content == f"<@{self.user}>":
            translation = self.translations.event(self.get_raw_guild_lang(message.guild.id), "ping")
            await message.channel.send(translation.format(self.get_raw_guild_prefixes(message.guild.id)))

        await self.process_commands(message)

    async def close(self):
        await super().close()
        await self.session.close()
        print("goodbye!")

    def run(self):
        token = env.TOKEN_DEV if env.TOKEN_DEV is not None else env.TOKEN
        super().run(token, reconnect=True)

