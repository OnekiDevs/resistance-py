import utils
from utils import ui, db
from utils.ui import confirm
from typing import AsyncGenerator, Optional, Coroutine, TYPE_CHECKING

import io
import json
import yaml
import uuid
from bot import OnekiBot

if TYPE_CHECKING:
    from utils.db import AsyncClient, AsyncDocumentReference


class ClubError(utils.app_commands.CheckFailure):
    pass


class Club:
    """Represents a club data model"""
    def __init__(self, *, guild: utils.discord.Guild) -> None:        
        self.guild = guild
        self.doc_ref: Optional[AsyncDocumentReference] = None
        self.channel_id = None
        
        self.name: str = ""
        self.description: str = ""
        self.owner_id: int = None
        self.is_public: bool = False
        self.is_nsfw: bool = False
        self.banner_url: Optional[str] = None
        
        self.members: dict[int, utils.discord.Member] = {}
        self.mods: dict[int, utils.discord.Member] = {}
        
        self.bans: list[int] = {}
        self.mutes: dict[int, utils.discord.Member] = {}
    
    @classmethod
    async def from_data(cls, data: dict, *, guild: utils.discord.Guild, doc_ref: db.AsyncDocumentReference):
        club = cls(guild=guild)
        
        club.doc_ref = doc_ref
        club.channel_id = int(data["channel"])
        club.name = data["name"]
        club.description = data["description"]
        club.owner_id = int(data["owner"])
        club.is_public = data["public"]
        club.is_nsfw = data["nsfw"]
        club.banner_url = data.get("banner")

        for mid in data["members"]:
            member = await club._fetch_member(int(mid))
            club.members[int(mid)] = member
            
        for mid in data.get("mods", []):
            member = club.members[int(mid)]
            club.mods[int(mid)] = member
            
        club.bans = data.get("bans", [])

        for mid in data.get("mutes", []):
            member = club.members[int(mid)]
            club.mutes[int(mid)] = member
            
        return club
    
    async def _fetch_member(self, member_id: int) -> utils.discord.Member:
        member = self.guild.get_member(member_id)
        if member is None:
            member = await self.guild.fetch_member(member_id)
            
        return member
    
    def get_member(self, member_id: int) -> utils.discord.Member:
        return self.members.get(member_id)
                
    def add_member(self, member: utils.discord.Member) -> Coroutine:
        self.members[member.id] = member
        return self.doc_ref.update({
            "members": db.firestore.firestore.ArrayUnion([str(member.id)])
        })
                
    def remove_member(self, member: utils.discord.Member) -> Coroutine:
        self.members.pop(member.id, None)
        return self.doc_ref.update({
            "members": db.firestore.firestore.ArrayRemove([str(member.id)])
        })
        
    def add_mod(self, member: utils.discord.Member) -> Coroutine:
        self.mods[member.id] = member
        return self.doc_ref.update({
            "mods": db.firestore.firestore.ArrayUnion([str(member.id)])
        })
                
    def remove_mod(self, member: utils.discord.Member) -> Coroutine:
        self.mods.pop(member.id, None)
        return self.doc_ref.update({
            "mods": db.firestore.firestore.ArrayRemove([str(member.id)])
        })
        
    async def add_ban(self, member: utils.discord.Member) -> None:
        self.bans.append(member.id)
        await self.doc_ref.update({
            "bans": db.firestore.firestore.ArrayUnion([str(member.id)])
        })
        await self.remove_member(member)
                
    def remove_ban(self, member: utils.discord.Member) -> Coroutine:
        self.bans.pop(member.id, None)
        return self.doc_ref.update({
            "bans": db.firestore.firestore.ArrayRemove([str(member.id)])
        })
        
    def add_mute(self, member: utils.discord.Member) -> Coroutine:
        self.mutes[member.id] = member
        return self.doc_ref.update({
            "mutes": db.firestore.firestore.ArrayUnion([str(member.id)])
        })
                
    def remove_mute(self, member: utils.discord.Member) -> Coroutine:
        self.mutes.pop(member.id, None)
        return self.doc_ref.update({
            "mutes": db.firestore.firestore.ArrayRemove([str(member.id)])
        })
    
    @property
    def owner(self) -> utils.discord.Member:
        return self.get_member(self.owner_id)
    
    @property
    def channel(self) -> utils.discord.TextChannel:
        return self.guild.get_channel(self.channel_id)
        
    def get_embed(self) -> utils.discord.Embed:
        embed = utils.discord.Embed(
            title=self.name, 
            description=f"```{self.description}```", 
            colour=utils.discord.Colour.blurple(), 
            timestamp=utils.utcnow()
        )
        embed.add_field(name="Owner", value=f"```{self.owner}/{self.owner_id}```")
        embed.add_field(name="Is Nsfw:", value="```"+ {True: "Si", False: "No"}[self.is_nsfw] + "```")
        
        if self.banner_url is not None:
            embed.set_image(url=self.banner_url)
            
        return embed
        
    def to_dict(self) -> dict:
        payload = {
            "owner": str(self.owner_id),
            "name": self.name,
            "description": self.description,
            "public": self.is_public,
            "nsfw": self.is_nsfw
        }
        
        if self.channel_id is not None:
            payload["channel"] = self.channel_id
        
        if utils.is_empty(self.members):
            payload["members"] = [str(self.owner_id)]
        else:
            members = []
            for mid in self.members.keys():
                members.append(str(mid))
                
            payload["members"] = members

        if self.bans:
            payload["bans"] = self.bans
            
        if self.mutes:
            mutes = []
            for mid in self.mutes.keys():
                mutes.append(str(mid))
                
            payload["mutes"] = mutes
            
        return payload
        
    def update(self) -> Coroutine:
        return self.doc_ref.update(self.to_dict())
        

class IsNsfw(ui.View):
    name = "nsfw"
    
    def __init__(self):
        super().__init__()
        self.value = False
        
    async def start(self, interaction = None, *, ephemeral=False):
        await super().start(interaction, ephemeral=ephemeral)
        return await self.wait()
        
    def get_content(self, _) -> str:
        return self.translations.content
        
    @ui.button(label="Yes", style=utils.discord.ButtonStyle.red)
    async def yes(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _):
        await interaction.response.edit_message(
            content=self.translations.success.format(interaction.user.name),
            view=None
        )
        
        self.value = True
        self.stop()
        
    @ui.button(label="No", style=utils.discord.ButtonStyle.blurple)
    async def no(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _):
        await interaction.response.edit_message(
            content=self.translations.success.format(interaction.user.name),
            view=None
        )
        
        self.stop()


class Questionnaire(ui.Modal, title="Questionnaire Club"): 
    modal_name: str = "questionnaire"
    
    def get_items(self) -> dict[str, utils.discord.ui.Item]:
        return {
            "name": ui.TextInput(label="Name", placeholder="Club name", min_length=4, max_length=32),
            "description": ui.TextInput(
                label="Description", 
                placeholder="A short and concise description",
                style=utils.discord.TextStyle.paragraph, 
                min_length=15, max_length=230
            )
        }

    async def on_submit(self, interaction: utils.discord.Interaction):
        db: AsyncClient = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        doc = await doc_ref.get()
        data = doc.to_dict()
        
        club = Club(guild=interaction.guild)
        club.name = self.name.value
        club.description = self.description.value
        club.owner_id = interaction.user.id
        
        if data.get("nsfw_clubs_enabled"):
            view = IsNsfw()
            await view.start(interaction, ephemeral=True)
            
            club.is_nsfw = view.value
        else:
            await interaction.response.send_message(self.translations.sent.format(interaction.user.name), ephemeral=True)
        
        id_hex = uuid.uuid1().hex
        if doc.exists:
            await doc_ref.update({id_hex: club.to_dict()})
        else:
            await doc_ref.set({id_hex: club.to_dict()})
        
        channel = await interaction.client.fetch_channel(data["approval_channel"])
        
        embed = club.get_embed()
        embed.add_field(name="ID:", value=f"```{id_hex}```", inline=False)
        
        await channel.send(self.translations.new_club, embed=embed)


class Explorer(ui.CancellableView):
    name: str = "explorer"
    
    def __init__(self, context = None, **kwargs):
        super().__init__(context, **kwargs)
        self.generator: Optional[AsyncGenerator[AsyncDocumentReference]] = None
        self.clubs: list[Club] = []
        self.num = 0
        
    async def generate_new_club(self, guild: utils.discord.Guild, member: utils.discord.Member): 
        while True:
            doc_ref = await self.generator.__anext__()
            if doc_ref.id == "wait_approval":
                continue
            
            doc = await doc_ref.get()
            club = await Club.from_data(doc.to_dict(), guild=guild, doc_ref=doc_ref)
            if club.is_public: 
                if member.id in club.bans:
                    continue

                self.clubs.append(club)
                return club
        
    async def get_data(self, *, bot: OnekiBot, guild: utils.discord.Guild, member: utils.discord.Member):
        if self.generator is None:
            collec_ref = bot.db.collection(f"guilds/{guild.id}/clubs")
            self.generator = collec_ref.list_documents()
        
        try:
            club = self.clubs[self.num]
        except IndexError:
            try:
                club = await self.generate_new_club(guild, member)
            except StopAsyncIteration:
                club = None
        
        return (club, member)

    def get_content(self, club: Club, _) -> str: 
        if club is not None:
            return self.translations.content
        
        if utils.is_empty(self.clubs):
            return

        return self.translations.no_more_clubs 

    def get_embed(self, club: Club, _) -> utils.discord.Embed:  
        if club is not None:
            return club.get_embed()

        if utils.is_empty(self.clubs):
            return utils.discord.Embed(
                title=self.translations.embed_not_found.title, 
                description=self.translations.embed_not_found.description,
                colour=utils.discord.Colour.red(),
                timestamp=utils.utcnow()
            )

    def update_components(self, club: Club, member: utils.discord.Member):         
        if club is not None:
            self.back.disabled = False
            self.join_or_exit.disabled = False
            self.next.disabled = False        

            if self.num == 0:
                self.back.disabled = True
            
            if (len(self.clubs) - 1) == self.num:
                self.next.disabled = False
                
            if member.id == club.owner_id:
                self.join_or_exit.disabled = True
            
            if member.id in club.mutes:
                self.join_or_exit.disabled = True
            
            self.join_or_exit.label = "Exit" if member.id in club.members else "Join"
            self.join_or_exit.style = utils.discord.ButtonStyle.red if member.id in club.members else utils.discord.ButtonStyle.green
        elif utils.is_empty(self.clubs):
            self.back.disabled = True
            self.join_or_exit.disabled = True
            self.next.disabled = True 
        else:
            self.back.disabled = False
            self.next.disabled = True
            self.join_or_exit.disabled = True
             
    @ui.button(label="Back", emoji="⬅️", style=utils.discord.ButtonStyle.grey)
    async def back(self, interaction: utils.discord.Interaction, *_): 
        self.num -= 1        
        self.msg = await self.update(interaction) 
        
    @ui.button(label="Join/Exit", style=utils.discord.ButtonStyle.green)
    async def join_or_exit(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, translation): 
        club = self.clubs[self.num]
        if interaction.user.id in club.members: # Exit
            overwrites = {**club.channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=False)}
            
            await club.remove_member(interaction.user)
            await interaction.response.send_message(translation.exit.format(club.name), ephemeral=True)
        else: # Join
            overwrites = {**club.channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=True)}
            await club.add_member(interaction.user)
            
            await interaction.response.send_message(translation.join.format(club.name), ephemeral=True)
            await club.channel.send(translation.new_user.format(club.name))
        
        await club.channel.edit(overwrites=overwrites)
    
    @ui.button(label="Next", emoji="➡️", style=utils.discord.ButtonStyle.grey)
    async def next(self, interaction: utils.discord.Interaction, *_): 
        self.num += 1
        self.msg = await self.update(interaction) 
        
def check_is_mod():
    async def predicate(interaction: utils.discord.Interaction) -> bool:
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            data = doc.to_dict()
            return str(interaction.user.id) in data.get("mods", []) or str(interaction.user.id) == data["owner"]
    
    return utils.app_commands.check(predicate)
                        
            
async def clubs_autocomplete(
    interaction: utils.discord.Interaction,
    current: str,
) -> list[utils.app_commands.Choice[str]]:
    db = interaction.client.db
    
    doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
    doc = await doc_ref.get()
    if doc.exists:
        return [
            utils.app_commands.Choice(name=f"{data['name']} / {club_id}", value=club_id)
            for club_id, data in doc.to_dict().items() if not club_id in ["approval_channel", "clubs_category", "nsfw_clubs_enabled"]
        ]


async def your_clubs_autocomplete(
    interaction: utils.discord.Interaction,
    current: str,
) -> list[utils.app_commands.Choice[str]]:
    db = interaction.client.db
    
    docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("owner", "==", f"{interaction.user.id}").stream()
    return [
        utils.app_commands.Choice(name=f"{doc.to_dict()['name']} / {doc.id}", value=f"{doc.id}")
        async for doc in docs
    ]


class ClubSettings(utils.app_commands.Group, name="club_settings"):
    """Manage settings of a club"""

    async def get_club(self, interaction: utils.discord.Interaction, club_id: str): 
        db: AsyncClient = interaction.client.db
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{club_id}")
        doc = await doc_ref.get()
        
        if doc.exists:
            club = await Club.from_data(
                doc.to_dict(), 
                guild=interaction.guild, 
                doc_ref=doc_ref
            )
            
            if interaction.user.id == club.owner.id:
                return club
                
            raise ClubError("You are not have permissions for this action")
        
        raise ClubError("Club not found")
        
    @utils.app_commands.command()
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def change_name(self, interaction: utils.discord.Interaction, club_id: str, new_name: str): 
        translation = interaction.client.translations.command(interaction.locale.value, "change_name")
        club = await self.get_club(interaction, club_id)
        await club.doc_ref.update({"name": new_name})
        
        channel = club.channel
        await channel.edit(name=new_name)
        
        await interaction.response.send_message(translation.success.format(new_name), ephemeral=True)
        await channel.send(translation.announcement.format(new_name))
        
    @utils.app_commands.command()
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def set_as_public(self, interaction: utils.discord.Interaction, club_id: str): 
        translation = interaction.client.translations.command(interaction.locale.value, "set_as_public")
        club = await self.get_club(interaction, club_id)
        club.doc_ref.update({"public": True})
        
        await interaction.response.send_message(translation.success, ephemeral=True)

    @utils.app_commands.command()
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def set_banner(self, interaction: utils.discord.Interaction, club_id: str, banner: utils.discord.Attachment):
        translation = interaction.client.translations.command(interaction.locale.value, "set_banner")
        club = await self.get_club(interaction, club_id)
        
        url = banner.url.split("?")[0] + "?width=750&height=240"
        club.banner_url = url

        view = confirm.Confirm(content=translation.content, embed=club.get_embed())
        await view.start(interaction, ephemeral=True)
        
        if view.value:
            await club.doc_ref.update({"banner": url})
                
    @utils.app_commands.command()
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def export(self, interaction: utils.discord.Interaction, club_id: str):
        translation = interaction.client.translations.command(interaction.locale.value, "export")
        club = await self.get_club(interaction, club_id)
        
        club.mods = []
        club.bans = []
        club.mutes = []

        data = club.to_dict()
        del data["channel"]
        del data["owner"]
        del data["members"]
                    
        file = utils.discord.File(
            fp=io.StringIO(json.dumps(data, indent=4)),
            filename="club_settings.json",
            description=translation.file_description.format(club.name)
        )
        await interaction.response.send_message(file=file, ephemeral=True)
            
    @utils.app_commands.command(name="import")
    @utils.app_commands.rename(club_id="club", file="json")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def _import(self, interaction: utils.discord.Interaction, club_id: str, file: utils.discord.Attachment):
        translation = interaction.client.translations.command(interaction.locale.value, "import")
        club = await self.get_club(interaction, club_id)
        
        data = club.to_dict()
        if file.content_type.startswith("application/json"):
            j = json.loads(await file.read())
            data.update(j)
        elif file.filename.endswith((".yml", ".yaml")):
            y = yaml.safe_load(await file.read())
            data.update(y)
        else:
            raise ClubError(translation.not_supported_file_extension)
        
        await club.doc_ref.update(data)
        await interaction.response.send_message("Configuraciones cargadas correctamente", ephemeral=True)
             
    mod_group = utils.app_commands.Group(name="mod", description="...")
                        
    @mod_group.command(name="add")
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def add_mod(self, interaction: utils.discord.Interaction, club_id: str, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "add_mod")
        club = await self.get_club(interaction, club_id)
        await club.add_mod(member)
            
        await interaction.response.send_message(translation.success.format(member), ephemeral=True)
        await club.channel.send(translation.announcement.format(member))
        
    @mod_group.command(name="remove")
    @utils.app_commands.rename(club_id="club")
    @utils.app_commands.autocomplete(club_id=your_clubs_autocomplete)
    async def remove_mod(self, interaction: utils.discord.Interaction, club_id: str, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "remove_mod")
        club = await self.get_club(interaction, club_id)
        await club.remove_mod(member)
        
        await interaction.response.send_message(translation.success.format(member), ephemeral=True)
        await club.channel.send(translation.announcement.format(member))
        

class ClubModerator(utils.app_commands.Group, name="club_moderator"): 
    """Group command of moderation in a club"""
    
    @utils.app_commands.command()
    @check_is_mod()
    async def mute(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "cmute")
        db: AsyncClient = interaction.client.db
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        
        async for doc in docs: 
            club = await Club.from_data(doc.to_dict(), guild=interaction.guild, doc_ref=doc.reference)
            if not member.id in club.mods or interaction.user.id == club.owner_id:
                if not member.id == club.owner_id:
                    await club.add_mute(member)
                    
                    channel = club.channel
                    overwrites = {
                        **channel.overwrites,
                        member: utils.discord.PermissionOverwrite(send_messages=False, add_reactions=False),
                    }
                    
                    await channel.edit(overwrites=overwrites)
                    return await interaction.response.send_message(translation.success.format(member))
            
            await interaction.response.send_message(translation.not_have_permissions, ephemeral=True)
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def unmute(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "cunmute")
        db: AsyncClient = interaction.client.db
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        
        async for doc in docs: 
            await doc.reference.update({"mutes": db.ArrayRemove([str(member.id)])})
            channel = await interaction.client.fetch_channel(doc.to_dict()["channel"])
            overwrites = {
                **channel.overwrites,
                member: utils.discord.PermissionOverwrite(send_messages=True, add_reactions=False),
            }
            
            await channel.edit(overwrites=overwrites)
            await interaction.response.send_message(translation.success.format(member))
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def ban(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "cban")
        db: AsyncClient = interaction.client.db
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        
        async for doc in docs: 
            club = await Club.from_data(doc.to_dict(), guild=interaction.guild, doc_ref=doc.reference)
            if not member.id in club.mods or interaction.user.id == club.owner_id:
                if not member.id == club.owner_id:
                    await club.add_ban(member)
                    
                    channel = club.channel
                    overwrites = {
                        **channel.overwrites,
                        member: utils.discord.PermissionOverwrite(view_channel=False),
                    }
                    
                    await channel.edit(overwrites=overwrites)
                    return await interaction.response.send_message(translation.success.format(member))
            
            await interaction.response.send_message(translation.not_have_permissions, ephemeral=True)
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def unban(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        translation = interaction.client.translations.command(interaction.locale.value, "cunban")
        db: AsyncClient = interaction.client.db
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        
        async for doc in docs: 
            await doc.reference.update({"bans": db.ArrayRemove([str(member.id)])})
            await interaction.response.send_message(translation.success.format(member), ephemeral=True)
    

class Clubs(utils.Cog):
    club_settings = ClubSettings()
    club_moderator = ClubModerator()
    
    async def create_channel(self, category: utils.discord.CategoryChannel, owner: utils.discord.Member, data: dict): 
        overwrites = {
            category.guild.default_role: utils.discord.PermissionOverwrite(view_channel=False),
            owner: utils.discord.PermissionOverwrite.from_pair(utils.discord.Permissions.all(), utils.discord.Permissions.none())
        }
        channel = await category.create_text_channel(data["name"], overwrites=overwrites, nsfw=data["nsfw"])
        await channel.edit(description=data["description"])
        
        return channel
    
    @utils.app_commands.command()
    async def create_club(self, interaction: utils.discord.Interaction):
        await Questionnaire().start(interaction)
        
    @utils.app_commands.command()
    @utils.app_commands.checks.has_permissions(administrator=True)
    async def clubs_settings(
        self, 
        interaction: utils.discord.Interaction,
        category: utils.discord.CategoryChannel,
        approval_channel: utils.discord.TextChannel,
        nsfw_clubs_enabled: Optional[bool] = None
    ):
        translation = self.translations.command(interaction.locale.value, "clubs_settings")
        db: AsyncClient = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        data = {
            "clubs_category": category.id,
            "approval_channel": approval_channel.id
        }
        
        if nsfw_clubs_enabled is not None and nsfw_clubs_enabled:
            data["nsfw_clubs_enabled"] = nsfw_clubs_enabled

        doc = await doc_ref.get()
        if doc.exists:
            await doc_ref.update(data)
        else:
            await doc_ref.set(data)
        
        await interaction.response.send_message(translation.success)
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=clubs_autocomplete)
    @utils.app_commands.checks.has_permissions(administrator=True)
    async def club_approval(self, interaction: utils.discord.Interaction, club: str):
        translation = self.translations.command(interaction.locale.value, "club_approval")
        db: AsyncClient = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        doc = await doc_ref.get()
        if doc.exists:
            clubs_data = doc.to_dict()
            if club_data := clubs_data.get(club):
                await doc_ref.delete(club)
                category = await interaction.guild.fetch_channel(clubs_data["clubs_category"])
                owner = await interaction.guild.fetch_member(club_data["owner"])

                channel = await self.create_channel(category, owner, club_data)
                await channel.send(translation.create_channel)
                club_data["channel"] = str(channel.id)
                
                doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{club}")
                await doc_ref.set(club_data)
                
                return await interaction.response.send_message(translation.approved)

            return await interaction.response.send_message(translation.not_found)
            
        await interaction.response.send_message(translation.without_clubs)
    
    @utils.app_commands.command()
    async def club_explorer(self, interaction: utils.discord.Interaction): 
        view = Explorer(
            bot=interaction.client, 
            guild=interaction.guild, 
            member=interaction.user
        )
        await view.start(interaction)
    

async def setup(bot: OnekiBot):
    await bot.add_cog(Clubs(bot))
    
