import uuid
import utils
from utils import ui, db
from utils.ui import confirm


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
        data = {
            "owner": str(interaction.user.id),
            "name": self.name.value,
            "description": self.description.value,
            "public": False,
            "users": [str(interaction.user.id)]
        }
        
        view = IsNsfw()
        await view.start(interaction, ephemeral=True)

        await view.wait()
        data["nsfw"] = view.value
        
        _id = uuid.uuid1().hex
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/wait_approval")
        doc = await doc_ref.get()
        if doc.exists:
            await doc_ref.update({_id: data})
        else:
            await doc_ref.set({_id: data})
        
        channel = await interaction.client.fetch_channel(doc.to_dict()["approval_channel"])
        embed = utils.discord.Embed(
            title=data["name"], 
            description=f"```{data['description']}```", 
            colour=utils.discord.Colour.blurple(), 
            timestamp=utils.utcnow()
        ).add_field(name="Owner:", value=f"```{data['owner']}```").add_field(name="Is Nsfw:", value=f"```{data['nsfw']}```")
        embed.add_field(name="ID:", value=f"```{_id}```", inline=False)
        
        await channel.send("Nuevo club por aprobar", embed=embed)


class Explorer(ui.View):
    NAME = "explorer"
    
    def __init__(self, context = None, **kwargs):
        super().__init__(context, **kwargs)
        self.generator = None
        self.clubs: list[list[utils.discord.Embed, dict, db.AsyncDocumentReference]] = []
        self.num = 0
        
    def create_embed(self, owner, data):
        embed = utils.discord.Embed(title=data["name"], description=data["description"])
        embed.add_field(name="Owner:", value=f"```{owner}```", inline=False).add_field(name="Users:", value=f"```{len(data['users'])}```").add_field(name="Is Nsfw:", value="```"+ {True: "Si", False: "No"}[data['nsfw']] + "```")
        embed.set_image(url=data.get("banner"))
        
        return embed
        
    async def generate_new_club(self, client, user_id: int): 
        while True:
            doc_ref = await self.generator.__anext__()
            if doc_ref.id == "wait_approval":
                continue
            
            doc = await doc_ref.get()
            data = doc.to_dict()
            if data["public"]:  
                if str(user_id) in data.get("bans", []):
                    continue
                
                owner = await client.fetch_user(data["owner"])
                
                embed = self.create_embed(owner, data)
                self.clubs.append([embed, data, doc_ref])
                return embed
        
    async def get_data(self, *, client, guild_id: int, user_id: int):
        collec_ref = client.db.collection(f"guilds/{guild_id}/clubs")
        self.generator = collec_ref.list_documents()
        
        return (client, guild_id, user_id)

    async def get_content(self, _) -> str:
        return "Club Explorer"

    async def get_embed(self, data) -> utils.discord.Embed:
        client, _, user_id = data
        
        try:
            return await self.generate_new_club(client, user_id)
        except StopAsyncIteration:
            embed = utils.discord.Embed(
                title="Nada que ver aqui", 
                description="Lo siento explorador, pero parece que no hay clubs por explorar :(",
                colour=utils.discord.Colour.red(),
                timestamp=utils.utcnow()
            )
            return embed

    async def update_components(self, data):
        _, _, user_id = data
        _, data, _ = self.clubs[self.num]
        
        if self.num == 0:
            self.back.disabled = True
        
        if str(user_id) in data.get("mutes"):
            self.join_or_exit.disabled = True

    @ui.button(label="Back", emoji="⬅️", style=utils.discord.ButtonStyle.green)
    async def back(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        if self.num != 0:
            self.num -= 1
        
        self.next.disabled = False
        await self.update_components((None, None, interaction.user.id))
        await interaction.response.edit_message(embed=self.clubs[self.num][0], view=self)
    
    @ui.button(label="Join/Exit", style=utils.discord.ButtonStyle.red)
    async def join_or_exit(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        _, data, doc_ref = self.clubs[self.num]
        channel = await interaction.client.fetch_channel(data["channel"])
        if str(interaction.user.id) in data.get("users", []):             
            overwrites = {**channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=False)}
            await doc_ref.update({"users": interaction.client.db.ArrayRemove([str(interaction.user.id)])})
        
            await interaction.response.send_message(f"Te has salido de {data['name']}", ephemeral=True)
        else: 
            overwrites = {**channel.overwrites, interaction.user: utils.discord.PermissionOverwrite(view_channel=True)}
            await doc_ref.update({"users": interaction.client.db.ArrayUnion([str(interaction.user.id)])})
            
            await interaction.response.send_message(f"Te has unido a {data['name']}", ephemeral=True)
            await channel.send(f"¡**{interaction.user}** se ha unido al club!")
        
        await channel.edit(overwrites=overwrites)
        
        # update data
        doc = await doc_ref.get()
        data = doc.to_dict()
        owner = await interaction.client.fetch_user(data["owner"])                
        self.clubs[self.num] = [self.create_embed(owner, data), data, doc_ref]
    
    @ui.button(label="Next", emoji="➡️", style=utils.discord.ButtonStyle.green)
    async def next(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        self.num += 1
        try:
            embed = self.clubs[self.num][0]
        except IndexError:
            try:
                embed = await self.generate_new_club(interaction)
            except StopAsyncIteration:
                button.disabled = True
                self.join_or_exit.disabled = True
                return await interaction.response.edit_message(content="Ya no hay mas clubs por explorar :(", embed=None, view=self)
                
        await interaction.response.edit_message(embed=embed)
            
                  
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

    async def check_is_owner(self, interaction: utils.discord.Interaction, club: str):
        db = interaction.client.db
        
        doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{club}")
        doc = await doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict()
            if data["owner"] == str(interaction.user.id):   
                return (doc_ref, doc)
            
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
            doc_ref, doc = data
            data = doc.to_dict()

            await doc_ref.update({"name": new_name})
            
            channel = await interaction.client.fetch_channel(data["channel"])
            await channel.edit(name=new_name)
            
            await interaction.response.send_message(f"El nombre del club se cambio a {new_name}!", ephemeral=True)
            await channel.send(f"Atentos todos, el nombre del club fue cambiado a {new_name}!")
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def set_as_public(self, interaction: utils.discord.Interaction, club: str): 
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            doc_ref, doc = data
            data = doc.to_dict()
  
            await doc_ref.update({"public": True})
            await interaction.response.send_message("El club a sido establecido como publico, ahora todos podran verlo en el explorador de clubs!", ephemeral=True)
        
    @utils.app_commands.command()
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def set_banner(self, interaction: utils.discord.Interaction, club: str, banner: utils.discord.Attachment):
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            doc_ref, doc = data
            data = doc.to_dict()
        
            url = banner.url.split("?")[0] + "?width=750&height=240"
            
            async def get_content(_):
                return "Seguro que quieres establecer este banner?"
            
            async def get_embed(_):
                embed = utils.discord.Embed(title=data["name"], description=data["description"])
                embed.add_field(name="Owner", value=f"```{interaction.user}```")
                embed.add_field(name="Is Nsfw:", value="```"+ {True: "Si", False: "No"}[data['nsfw']] + "```")
                embed.set_image(url=url)
                return embed
            
            view = confirm.Confirm()
            view.get_content = get_content
            view.get_embed = get_embed
            
            view.start(interaction, ephemeral=True)
                        
            await view.wait()    
            if view.value:
                await doc_ref.update({"banner": url})
                
    @group.command(name="add")
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def add_mod(self, interaction: utils.discord.Interaction, club: str, member: utils.discord.Member):
        db = interaction.client.db
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            doc_ref, doc = data
            data = doc.to_dict()
            
            await doc_ref.update({"mods": db.ArrayUnion([str(member.id)])})
            await interaction.response.send_message(f"Ahora {member}, es un moderador del club", ephemeral=True)
            
            channel = await interaction.client.fetch_channel(data["channel"])
            await channel.send(f"Atentos, {member} a sido ascendido a moderador del club!")
            
    @group.command(name="remove")
    @utils.app_commands.autocomplete(club=your_clubs_autocomplete)
    async def remove_mod(self, interaction: utils.discord.Interaction, club: str, member: utils.discord.Member):
        db = interaction.client.db
        data = await self.check_is_owner(interaction, club)
        if data is not None:
            doc_ref, doc = data
            data = doc.to_dict()
            
            await doc_ref.update({"mods": db.ArrayRemove([str(member.id)])})
            await interaction.response.send_message(f"Ahora {member} a dejado de ser un moderador del club", ephemeral=True)
            
            channel = await interaction.client.fetch_channel(data["channel"])
            await channel.send(f"Atentos, {member} a dejado de ser un moderador del club :(")
        

class ClubModerator(utils.app_commands.Group, name="club_moderator"): 
    """Group command of moderation in a club"""
    
    @utils.app_commands.command()
    @check_is_mod()
    async def mute(self, interaction: utils.discord.Interaction, member: utils.discord.Member):
        db = interaction.client.db
        
        docs = db.collection(f"guilds/{interaction.guild_id}/clubs").where("channel", "==", str(interaction.channel_id)).stream()
        async for doc in docs: # should only be one
            data = doc.to_dict()
            if not str(member.id) in data.get("mods", []) or str(interaction.user.id) == data["owner"]:
                if not str(member.id) == data["owner"]:
                    doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
                    channel = await interaction.client.fetch_channel(data["channel"])
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
            data = doc.to_dict()
            if not str(member.id) in data.get("mods", []) or str(interaction.user.id) == data["owner"]:
                if not str(member.id) == data["owner"]:
                    doc_ref = db.document(f"guilds/{interaction.guild_id}/clubs/{doc.id}")
                    channel = await interaction.client.fetch_channel(data["channel"])
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
    