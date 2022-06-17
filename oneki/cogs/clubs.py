import utils
from utils import ui, db
from utils.ui import confirm

import io
import json
import yaml
import uuid


class Club:
    """Represents a club data model"""
    def __init__(self, *, guild: utils.discord.Guild) -> None:        
        self.guild = guild
        self.channel_id = None
        
        self.name = ""
        self.description = ""
        self.owner_id = None
        self.is_public = False
        self.is_nsfw = False
        self._banner = None
        
        self.members: dict[int, utils.discord.Member] = {}
        self.mods: dict[int, utils.discord.Member] = {}
        self.bans: dict[int, utils.discord.Member] = {}
        self.mutes: dict[int, utils.discord.Member] = {}
    
    @classmethod
    async def from_data(cls, data: dict, *, guild: utils.discord.Guild):
        club = cls(guild=guild)
        
        club.channel_id = int(data["channel"])
        club.name = data["name"]
        club.description = data["description"]
        club.owner_id = int(data["owner"])
        club.is_public = data["public"]
        club.is_nsfw = data["nsfw"]
        club._banner = data.get("banner")

        for mid in data["members"]:
            member = await club._fetch_member(int(mid))
            club.members[int(mid)] = member
            
        for mid in data.get("mods", []):
            member = club.members[int(mid)]
            club.mods[int(mid)] = member
            
        for mid in data.get("bans", []):
            member = await club._fetch_member(int(mid))
            club.bans[int(mid)] = member

        for mid in data.get("mutes", []):
            member = club.members[int(mid)]
            club.mutes[int(mid)] = member
            
        return club
    
    async def _fetch_member(self, member_id: int) -> utils.discord.Member:
        member = self.guild.get_member(member_id)
        if member is None:
            member = await self.guild.fetch_member(member_id)
            
        return member
                
    def _add_member(self, member: utils.discord.Member) -> None:
        self.members[member.id] = member
                
    def _remove_member(self, member: utils.discord.Member) -> None:
        self.members.pop(member.id, None)
        
    def _add_ban(self, member: utils.discord.Member) -> None:
        self.bans[member.id] = member
        self._remove_member(member)
                
    def _remove_ban(self, member: utils.discord.Member) -> None:
        self.bans.pop(member.id, None)
        
    def _add_member(self, member: utils.discord.Member) -> None:
        self.mutes[member.id] = member
                
    def _remove_member(self, member: utils.discord.Member) -> None:
        self.mutes.pop(member.id, None)
        
    @property
    def banner_url(self) -> str:
        return self._banner
    
    def get_member(self, member_id: int) -> utils.discord.Member:
        return self.members.get(member_id)
    
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
        embed.add_field(name="Owner", value=f"```{self.owner}```")
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

        if not utils.is_empty(self.bans):
            bans = []
            for mid in self.bans.keys():
                bans.append(str(mid))
                
            payload["bans"] = bans
            
        if not utils.is_empty(self.mutes):
            mutes = []
            for mid in self.mutes.keys():
                bans.append(str(mid))
                
            payload["mutes"] = mutes
            
        return payload
        

class IsNsfw(ui.View):
    def __init__(self):
        super().__init__()
        self.value = False
        
    async def get_content(self, _) -> str:
        return "¿El club sera nsfw?"
        
    @ui.button(label="Yes", style=utils.discord.ButtonStyle.red)
    @ui.disable_when_pressed
    async def yes(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button):
        self.value = True
        return {
            "content": f"Gracias por tu solicitud, {interaction.user.name}!\nEspere la aprobación de los admins/mods ;)"
        }
        
    @ui.button(label="No", style=utils.discord.ButtonStyle.blurple)
    @ui.disable_when_pressed
    async def no(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button):
        return {
            "content": f"Gracias por tu solicitud, {interaction.user.name}!\nEspere la aprobación de los admins/mods ;)", 
        }


class Questionnaire(ui.Modal, title="Questionnaire Club"):
    name = ui.TextInput(label="Nombre", placeholder="Nombre del club", min_length=4, max_length=32)
    description = ui.TextInput(
        label="description", 
        placeholder="Una descripcion corta y concisa",
        style=utils.discord.TextStyle.paragraph, 
        min_length=15, max_length=120
    )

    async def on_submit(self, interaction: utils.discord.Interaction):
        db = interaction.client.db
        
        club = Club(guild=interaction.guild)
        club.name = self.name.value
        club.description = self.description.value
        club.owner_id = interaction.user.id
        
        view = IsNsfw()
        await view.start(interaction, ephemeral=True)

        await view.wait()
        club.is_nsfw = view.value
        
        id_hex = uuid.uuid1().hex
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        doc = await doc_ref.get()
        if doc.exists:
            await doc_ref.update({id_hex: club.to_dict()})
        else:
            await doc_ref.set({id_hex: club.to_dict()})
        
        channel = await interaction.client.fetch_channel(doc.to_dict()["approval_channel"])
        
        embed = club.get_embed()
        embed.add_field(name="ID:", value=f"```{id_hex}```", inline=False)
        
        await channel.send("Nuevo club por aprobar", embed=embed)


class Explorer(ui.View):
    NAME = "explorer"
    
    def __init__(self, context = None, **kwargs):
        super().__init__(context, **kwargs)
        self.generator = None
        self.clubs: list[list[Club, db.AsyncDocumentReference]] = []
        self.num = 0
        
    async def generate_new_club(self, guild: utils.discord.Guild, member: utils.discord.Member): 
        while True:
            doc_ref = await self.generator.__anext__()
            if doc_ref.id == "wait_approval":
                continue
            
            doc = await doc_ref.get()
            club = await Club.from_data(doc.to_dict(), guild=guild)
            # data = doc.to_dict()
            if club.is_public: 
                if member.id in club.bans:
                    continue

                self.clubs.append([club, doc_ref])
                return club
        
    async def get_data(self, *, client, guild: utils.discord.Guild, member: utils.discord.Member):
        collec_ref = client.db.collection(f"guilds/{guild.id}/clubs")
        self.generator = collec_ref.list_documents()
        
        return (client, guild, member)

    async def get_content(self, _) -> str:
        return "Club Explorer"

    async def get_embed(self, data) -> utils.discord.Embed:
        _, guild, user = data
        
        try:
            club = await self.generate_new_club(guild, user)
            return club.get_embed()
        except StopAsyncIteration:
            embed = utils.discord.Embed(
                title="Nada que ver aqui", 
                description="Lo siento explorador, pero parece que no hay clubs por explorar :(",
                colour=utils.discord.Colour.red(),
                timestamp=utils.utcnow()
            )
            return embed

    async def update_components(self, data):
        _, _, user = data
        club, _ = self.clubs[self.num]
        
        if self.num == 0:
            self.back.disabled = True
        
        if (len(self.clubs) - 1) == self.num:
            self.next.disabled = False
        
        if user.id in club.mutes:
            self.join_or_exit.disabled = True

    @ui.button(label="Back", emoji="⬅️", style=utils.discord.ButtonStyle.green)
    async def back(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        if self.num != 0:
            self.num -= 1
        
        await self.update_components((None, None, interaction.user.id))
        await interaction.response.edit_message(embed=self.clubs[self.num][0], view=self)
    
    @ui.button(label="Join/Exit", style=utils.discord.ButtonStyle.red)
    async def join_or_exit(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        club, doc_ref = self.clubs[self.num]
        if interaction.user.id in club.members:             
            overwrites = {**club.channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=False)}
            
            club._remove_member(interaction.user)
            await doc_ref.update({"members": interaction.client.db.ArrayRemove([str(interaction.user.id)])})
            
            await interaction.response.send_message(f"Te has salido de {club.name}", ephemeral=True)
        else: 
            overwrites = {**club.channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=True)}
            
            club._add_member(interaction.user)
            await doc_ref.update({"members": interaction.client.db.ArrayUnion([str(interaction.user.id)])})
            
            await interaction.response.send_message(f"Te has unido a {club.name}", ephemeral=True)
            await club.channel.send(f"¡**{interaction.user}** se ha unido al club!")
        
        await club.channel.edit(overwrites=overwrites)
    
    @ui.button(label="Next", emoji="➡️", style=utils.discord.ButtonStyle.green)
    async def next(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        self.num += 1
        try:
            club = self.clubs[self.num][0]
            embed = club.get_embed()
        except IndexError:
            try:
                embed = await self.generate_new_club(interaction)
            except StopAsyncIteration:
                button.disabled = True
                self.join_or_exit.disabled = True
                return await interaction.response.edit_message(content="Ya no hay mas clubs por explorar :(", embed=None, view=self)
                
        await self.update_components((None, None, interaction.user.id))
        await interaction.response.edit_message(embed=embed, view=self)
            
                  
def check_is_admin():
    def predicate(interaction: utils.discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator == True
    
    return utils.app_commands.check(predicate)
        
        
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
            for club_id, data in doc.to_dict().items() if not club_id in ["approval_channel", "clubs_category"]
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

    async def check_is_owner(self, interaction: utils.discord.Interaction, club_name: str):
        db = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{club_name}")
        doc = await doc_ref.get()
        
        if doc.exists:
            club = await Club.from_data(doc.to_dict(), guild=interaction.guild)
            if interaction.user.id == club.owner_id: 
                return (club, doc_ref)
            
            await interaction.response.send_message("No tienes permisos para hacer esto D:", ephemeral=True)
            return
            
        await interaction.response.send_message("P-Pero, el club no existe :/", ephemeral=True)
        return

    group = utils.app_commands.Group(name="mod", description="...")
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def change_name(self, interaction: utils.discord.Interaction, club: str, new_name: str): 
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, doc_ref = data

            await doc_ref.update({"name": new_name})
            
            channel = _club.channel
            await channel.edit(name=new_name)
            
            await interaction.response.send_message(f"El nombre del club se cambio a {new_name}!", ephemeral=True)
            await channel.send(f"Atentos todos, el nombre del club fue cambiado a {new_name}!")
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def set_as_public(self, interaction: utils.discord.Interaction, club: str): 
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _, doc_ref = data
  
            await doc_ref.update({"public": True})
            await interaction.response.send_message("El club a sido establecido como publico, ahora todos podran verlo en el explorador de clubs!", ephemeral=True)
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def set_banner(self, interaction: utils.discord.Interaction, club: str, banner: utils.discord.Attachment):
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, doc_ref = data
        
            url = banner.url.split("?")[0] + "?width=750&height=240"
            
            async def get_content(_):
                return "Seguro que quieres establecer este banner?"
            
            async def get_embed(_):
                return _club.get_embed()
            
            view = confirm.Confirm()
            view.get_content = get_content
            view.get_embed = get_embed
            
            view.start(interaction, ephemeral=True)
                        
            await view.wait()    
            if view.value:
                await doc_ref.update({"banner": url})
                
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def export(self, interaction: utils.discord.Interaction, club: str):
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, _ = data
            
            _club.channel_id = None
            _club.mods = []
            _club.bans = []
            _club.mutes = []
            
            data = _club.to_dict()
            del data["owner"]
            del data["members"]
            
            file = utils.discord.File(
                fp=io.StringIO(json.dumps(data, indent=4)),
                filename="club_settings.json",
                description=f"Las configuraciones de: {_club.name}"
            )
            await interaction.response.send_message(file=file, ephemeral=True)
            
    @utils.app_commands.command(name="import")
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    @utils.app_commands.rename(file="json")
    async def _import(self, interaction: utils.discord.Interaction, club: str, file: utils.discord.Attachment):
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, doc_ref = data
            
            data = _club.to_dict()
            if file.content_type.startswith("application/json"):
                j = json.loads(await file.read())
                data.update(j)
            elif file.filename.endswith((".yml", ".yaml")):
                y = yaml.safe_load(await file.read())
                data.update(y)
            else:
                return await interaction.response.send_message("Solo se admiten archivo con extension .json, .yml o .yaml", ephemeral=True)
                
            await doc_ref.update(data)
            await interaction.response.send_message("Configuraciones cargadas correctamente", ephemeral=True)
                        
    @group.command(name="add")
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def add_mod(self, interaction: utils.discord.Interaction, club: str, member: utils.discord.Member):
        db = interaction.client.db
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, doc_ref = data
            await doc_ref.update({"mods": db.ArrayUnion([str(member.id)])})
            
            await interaction.response.send_message(f"Ahora {member}, es un moderador del club", ephemeral=True)
            await _club.channel.send(f"Atentos, {member} a sido ascendido a moderador del club!")
            
    @group.command(name="remove")
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def remove_mod(self, interaction: utils.discord.Interaction, club: str, member: utils.discord.Member):
        db = interaction.client.db
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            _club, doc_ref = data
            await doc_ref.update({"mods": db.ArrayRemove([str(member.id)])})
            
            await interaction.response.send_message(f"Ahora {member} a dejado de ser un moderador del club", ephemeral=True)
            await _club.channel.send(f"Atentos, {member} a dejado de ser un moderador del club :(")
        

class ClubModerator(utils.app_commands.Group, name="club_moderator"): 
    """Group command of moderation in a club"""
    
    @utils.app_commands.command()
    @check_is_mod()
    async def mute(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            club = await Club.from_data(doc.to_dict(), guild=interaction.guild)
            if not member.id in club.mods or interaction.user.id == club.owner_id:
                if not member.id == club.owner_id:
                    doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
                    
                    channel = club.channel
                    overwrites = {
                        **channel.overwrites,
                        member: utils.discord.PermissionOverwrite(send_messages=False, add_reactions=False),
                    }
                    
                    await channel.edit(overwrites=overwrites)
                    
                    await doc_ref.update({"mutes": db.ArrayUnion([str(member.id)])})
                    return await interaction.response.send_message(f"{member} a sido muteado :(")
            
            await interaction.response.send_message("Lo siento, pero no puedes mutear a este usuario :/", ephemeral=True)
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def unmute(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
            
            channel = await interaction.client.fetch_channel(doc.to_dict()["channel"])
            overwrites = {
                **channel.overwrites,
                member: utils.discord.PermissionOverwrite(send_messages=True, add_reactions=False),
            }
            
            await channel.edit(overwrites=overwrites)
            
            await doc_ref.update({"mutes": db.ArrayRemove([str(member.id)])})
            await interaction.response.send_message(f"{member} a sido desmuteado :D")
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def ban(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            club = await Club.from_data(doc.to_dict(), guild=interaction.guild)
            if not member.id in club.mods or interaction.user.id == club.owner_id:
                if not member.id == club.owner_id:
                    doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
                    
                    channel = club.channel
                    overwrites = {
                        **channel.overwrites,
                        member: utils.discord.PermissionOverwrite(view_channel=False),
                    }
                    
                    await channel.edit(overwrites=overwrites)
                    
                    await doc_ref.update({"bans": db.ArrayUnion([str(member.id)])})
                    return await interaction.response.send_message(f"{member} a sido baneado :(")
            
            await interaction.response.send_message("Lo siento, pero no puedes banear a este usuario :/", ephemeral=True)
            
    @utils.app_commands.command()
    @check_is_mod() 
    async def unban(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
            await doc_ref.update({"bans": db.ArrayRemove([str(member.id)])})
            await interaction.response.send_message(f"{member} a sido desbaneado :D", ephemeral=True)
    

class Clubs(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    club_settings = ClubSettings()
    club_moderator = ClubModerator()
    
    async def create_channel(self, category: utils.discord.CategoryChannel, owner: utils.discord.Member, data: dict): 
        overwrites = {
            category.guild.default_role: utils.discord.PermissionOverwrite(view_channel=False),
            owner: utils.discord.PermissionOverwrite.from_pair(utils.discord.Permissions.all(), utils.discord.Permissions.none())
        }
        channel = await category.create_text_channel(data["name"], overwrites=overwrites, nsfw=data["nsfw"])
        await channel.edit(description=data["description"])
        
        await channel.send("Su aventura comienza aqui!")
        return channel
    
    @utils.app_commands.command()
    async def create_club(self, interaction: utils.discord.Interaction):
        await interaction.response.send_modal(Questionnaire())
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=clubs_autocomplete)
    @check_is_admin()
    async def approval(self, interaction: utils.discord.Interaction, club: str):
        db = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        doc = await doc_ref.get()
        if doc.exists:
            clubs_data = doc.to_dict()
            club_data = clubs_data.get(club)
            if club_data is not None:
                await doc_ref.delete(club)
                
                guild = await interaction.client.fetch_guild(interaction.guild_id)
                category = await guild.fetch_channel(clubs_data["clubs_category"])
                owner = await guild.fetch_member(club_data["owner"])
                
                channel = await self.create_channel(category, owner, club_data)
                club_data["channel"] = str(channel.id)
                
                doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{club}")
                await doc_ref.set(club_data)
                
                return await interaction.response.send_message("Club aprobado con exito!")

            return await interaction.response.send_message("No puedo aprobar algo que no existe :(")
                
        await interaction.response.send_message("No hay clubs por aprobar")
    
    @utils.app_commands.command()
    async def explorer(self, interaction: utils.discord.Interaction): 
        view = Explorer(
            client=interaction.client, 
            guild_id=interaction.guild_id, 
            user_id=interaction.user.id
        )
        await view.start(interaction, ephemeral=True)
    

async def setup(bot: utils.commands.Bot):
    await bot.add_cog(Clubs(bot))
    