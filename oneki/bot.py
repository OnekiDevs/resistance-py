import traceback
import aiohttp
import sys

import utils
from utils import context, db, env
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
        
        self.db = db.async_client()
        self.translations = Translations()
        self.session = aiohttp.ClientSession(loop=self.loop)

        # prefixes[guild_id]: list
        # languages[guild_id]: str(lang)
        self.prefixes, self.languages = self._get_guild_settings()

        # user_id mapped to True
        # these are users globally blacklisted
        self.blacklist = self._get_blacklist()

        # cogs unload
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    def _get_guild_settings(self):
        # guild_id: list
        prefixes = {}
        # guild_id: str(lang)
        languages = {}
        
        collection = self.db.collection("guilds")
        async def iterator():
            async for doc_ref in collection.list_documents():
                doc: db.firestore.firestore.DocumentSnapshot = await doc_ref.get()
                if doc.exists: 
                    doc_content = doc.to_dict()
                    if doc_content.get("prefixes") is not None:
                        prefixes[doc.id] = doc_content.get("prefixes")
                    
                    if doc_content.get("lang") is not None:
                        languages[doc.id] = doc_content.get("lang")
        
        self.loop.run_until_complete(iterator())
        return prefixes, languages

    def _get_blacklist(self):
        # {users: {id, ...}, guilds: {id, ...}}
        blacklist = {"users": set(), "guilds": set()}
        
        collection = self.db.collection("blacklist")
        async def iterator():
            async for doc_ref in collection.list_documents(): 
                doc: db.firestore.firestore.DocumentSnapshot = await doc_ref.get()
                if doc.exists: 
                    doc_content = doc.to_dict()
                    blacklist["users" if doc_content.get("type") == "user" else "guilds"].add(doc.id)
        
        self.loop.run_until_complete(iterator())
        return blacklist

    def get_guild_prefixes(self, guild, *, local_inject=_prefix_callable):
        proxy_msg = utils.discord.Object(id=0)
        proxy_msg.guild = guild
        return local_inject(self, proxy_msg)

    def get_raw_guild_prefixes(self, guild_id):
        return self.prefixes.get(str(guild_id), ['?', '>'])

    def get_guild_lang(self, guild_id):
        return self.languages.get(str(guild_id), "en")

    async def add_to_blacklist(self, object_id, *, type, reason=None):
        doc_ref = self.db.document(f"blacklist/{object_id}")
        await doc_ref.set({"type": type, "reason": reason})
        
        self.blacklist["users" if type == "user" else "guilds"].add(str(object_id))

    async def remove_from_blacklist(self, object_id):
        doc_ref = self.db.document(f"blacklist/{object_id}")
        doc = await doc_ref.get()
        if not doc.exists():
            raise Exception(f"{object_id} not in blacklist")
        
        self.blacklist["users" if doc.to_dict().get("type") == "user" else "guilds"].remove(str(object_id)) 

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

        if ctx.author.id in self.blacklist["users"]:
            return
        
        if ctx.guild.id in self.blacklist["guilds"]:
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
        token = env.TOKEN_DISCORD_DEV if env.TOKEN_DISCORD_DEV is not None else env.TOKEN_DISCORD
        super().run(token, reconnect=True)

