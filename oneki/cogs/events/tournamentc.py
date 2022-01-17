import uuid
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

import utils
from utils import env
from utils.context import Context
from utils.views import confirm, forms


class Player:
    def __init__(self, ctx: Context, user_id):
        self.ctx = ctx
        self.id = str(user_id)
        self._participants_doc_ref = ctx.db.document("tournamentc/participants")
        self._eliminated_doc_ref = ctx.db.document("tournamentc/eliminated")
        
    
    async def eliminated(self) -> bool:
        doc = await self._eliminated_doc_ref.get()
        if doc.exists:
            return True if doc.to_dict().get(self.id, None) is not None else False
    
    async def _data_eliminated(self) -> dict:
        doc = await self._eliminated_doc_ref.get()
        if doc.exists:
            return doc.to_dict().get(self.id)
    
    async def data(self) -> dict:
        doc = await self._participants_doc_ref.get()
        if doc.exists:
            return doc.to_dict().get(self.id, await self._data_eliminated())
    
    async def name(self) -> str:
        data = await self.data()
        return data.get('name')
    
    async def delete(self):
        await self._eliminated_document.update(self.id, self.data)
        await self._participants_document.delete(self.id)


class Game:
    def __init__(self, ctx: Context, game_id):
        self.ctx = ctx
        self.loop = ctx.bot.loop
        self.id = str(game_id)
        self._games_doc_ref = ctx.db.document("tournamentc/games")
        self._waiting_doc_ref = ctx.db.document(f"tournamentc/games/waiting/{self.id}")
        self._finished_doc_ref = ctx.db.document(f"tournamentc/games/finished/{self.id}")
    
    async def round(self):
        doc = await self._finished_doc_ref.get()
        if doc.exists:
            return doc.to_dict().get("round") 
        else:
            doc = await self._games_doc_ref.get()
            return doc.to_dict().get("round") 
    
    async def opponents(self) -> dict or None:
        waiting_doc = await self._waiting_doc_ref.get()
        playing_doc = await self._games_doc_ref.get()
        finished_doc = await self._finished_doc_ref.get()
        if waiting_doc.exists:
            return {player_id: Player(self.ctx, player_id) for player_id in waiting_doc.to_dict().get("opponents")}
        elif finished_doc.exists:
            return {player_id: Player(self.ctx, player_id) for player_id in finished_doc.to_dict().get("opponents")}
        elif playing_doc.exists: 
            return {player_id: Player(self.ctx, player_id) for player_id in playing_doc.to_dict().get("playing").get("opponents")}
        else: return None

    @staticmethod
    async def get_new_link(session):
        response = await session.post(
            "https://lichess.org/api/tournament",
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {env.TOKEN_LICHESS}"},
            json={'name':f"LR Tournament 2021", 
                    'clockTime': 5, 
                    'clockIncrement': 3, 
                    'minutes': 120, 
                    'waitMinutes': 5}
        )
        
        data = await response.json()
        return f"https://lichess.org/tournament/{data['id']}"
        
    async def start(self):
        playing_doc = await self._games_doc_ref.get()
        if playing_doc.exists and utils.is_empty(playing_doc.to_dict().get("playing")):
            waiting_doc = await self._waiting_doc_ref.get()
            if waiting_doc.exists == False:
                await self.ctx.send("Nop, nada que ver por aqui, la partida no existe o ya fue terminada <:awita:852216204512329759>")
                return None

            data = waiting_doc.to_dict()
            data["game_id"] = self.id
            data["game_links"] = [await self.get_new_link()]

            self._waiting_doc_ref.delete()
            self._games_doc_ref.update({"playing": data})

            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    opponents = await self.opponents()
                    for player_id in opponents.keys():
                        object_member: utils.discord.Member = await self.ctx.guild.fetch_member(int(player_id))
                        await object_member.add_roles(role)
                    
            await self.ctx.send("Partida iniciada!")
            return data
        else:
            await self.ctx.send("Lo siento, ya hay una partida en curso 🙄")
            return None
    
    async def winner(self, user_id):
        playing_doc = await self._games_doc_ref.get()
        if playing_doc.exists and playing_doc.to_dict().get("playing"):
            opponents = await self.opponents()
            data = playing_doc.to_dict().get("playing")
            data['round'] = self.round()
            data.pop("game_id")
            for player_id, player_object in opponents.items():
                if player_id == str(user_id):
                    data["winner"] = player_object.id
                else:
                    player_object.delete()

            self._games_doc_ref.delete("playing")
            self._finished_doc_ref.set(data)
            
            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    for player_id in self.opponents.keys():
                        object_member: utils.discord.Member = await self.ctx.guild.fetch_member(int(player_id))
                        await object_member.remove_roles(role)
            
            await self.ctx.send("Partida finalizada y ganador establecido")
        else: 
            await self.ctx.send("No se puede definir a un ganador porque este juego no se a iniciado 🙄")

    async def vs_image(self):
        opponents = await self.opponents()
        if opponents is not None:
            img = Image.open("resource/img/vs_template.png")
            num = 0
            for player_id in opponents.keys():
                # BytesIO(object_player.data.get('pfp').split('=')[0]+"=128")
                object_user: utils.discord.User = await self.ctx.bot.fetch_user(int(player_id))
                pfp = Image.open(BytesIO(await object_user.avatar.with_size(128).read()))
                pfp = pfp.resize((178, 178))
                img.paste(pfp, (112 if num == 0 else 112+(pfp.size[0]+269), 170))
                num = 1
            
            img.save("resource/img/vs_cache.png")
            return utils.discord.File(
                fp="resource/img/vs_cache.png",
                filename=f"{self.id}.png"
            )
        
    def delete(self):
        self._waiting_doc_ref.delete()


class Tournament_Chess(utils.commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @utils.commands.command(hidden=True)
    async def inscription(self, ctx: Context):
        await ctx.message.add_reaction('❌')
        return await ctx.send("Ups!, Lamentablemente ya se cerraron las inscripciones :(")
        
        if ctx.guild is None:
            return

        form = forms.Tournament(ctx)
        await ctx.author.send("Pronto estasssrá lista tu inscripción al torneo!, solo necesitamos que llenes este pequeño formulario:", embed=form.embed, view = form)

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def players(self, ctx: Context, member: utils.discord.Member=None):
        if member is not None:
            player = Player(ctx, member.id)

            embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name=await player.name(), icon_url=player.data().get('pfp'))
            embed.add_field(name="ID:", value=f"`{player.id}`", inline=False)
            embed.add_field(name="Eliminated?:", value=f"`{player.eliminated()}`")
            embed.add_field(name="Country:", value=f"`{player.data().get('country')}`")
            embed.add_field(name="Question:", value=f"`{player.data().get('question')}`")
            
            await ctx.send(embed=embed)
        else:    
            num = 1
            doc_ref = ctx.db.document("tournamentc/participants")
            doc = await doc_ref.get()
            if doc.exists:
                players = doc.to_dict()
                for user_id, data in players.items():
                    embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
                    embed.set_author(name=data.get('name'), icon_url=data.get('pfp'))
                    embed.add_field(name="ID:", value=f"`{user_id}`")
                    embed.add_field(name="Country:", value=f"`{data.get('country')}`")
                    embed.add_field(name="Question:", value=f"`{data.get('question')}`")

                    await ctx.send(f"#{num}", embed=embed)
                    num += 1

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def remove_player(self, ctx: Context, member: utils.discord.Member):
        player = Player(ctx, member.id)
        if await player.eliminated() == False:
            view = confirm.View()
            await ctx.send(f"Seguro que quieres descalificar a {member.name}#{member.discriminator}?", view=view)

            await view.wait()
            if view.value is None:
                await ctx.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")
            elif view.value:
                await player.delete()
                await ctx.send(f"{member.name}#{member.discriminator} fue descalificado :(")
        else:
            await ctx.send(f"{member.name}#{member.discriminator} ya esta descalificado o no esta en la lista de participantes 🙄")

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_link(self, ctx: Context):
        await ctx.send(await Game.get_new_link(ctx.session))

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_games(self, ctx: Context):
        collection_ref = ctx.db.collection("tournamentc/games/waiting")
        utils.delete_collection(collection_ref)
        
        doc_ref = ctx.db.document("tournamentc/participants")
        doc = await doc_ref.get()
        if doc.exists:
            players = list(doc.to_dict().keys())
            img = Image.open("resource/img/dashboard_template.png")

            num = 1
            xy = [50, 50]
            pfp_size = (100, 100)
            while utils.is_empty(players) == False:
                if len(players) == 1:
                    break

                # <------ Generacion de juegos ------>
                player1 = Player(utils.random.choice(players))
                players.pop(players.index(player1.id))
                                                    
                player2 = Player(utils.random.choice(players))
                players.pop(players.index(player2.id))

                id_game = str(uuid.uuid1().int)     
                collection_ref.add({"opponents": [player1.id, player2.id]}, id_game)

                # <------------- Imagen ------------->
                # pfp user 1 
                object_user1: utils.discord.User = await ctx.bot.fetch_user(int(player1.id))
                pfp = Image.open(BytesIO(await object_user1.avatar.with_format("png").with_size(128).read()))
                pfp = pfp.resize(pfp_size)
                # x: xy[0]; y: xy[1]
                if num == 11:
                    xy[0] = xy[0] + (pfp.size[0] + (img.size[0] - (pfp.size[0] + xy[0])*2))
                    xy[1] = 50
                
                if num != 1 and num != 11:
                    # print(num, xy[1] + (pfp_user1.size[1] + 100))
                    xy[1] = xy[1] + (pfp.size[1] + 100)
                
                img.paste(pfp, tuple(xy))
                num += 1
                
                # pfp user 2
                object_user2: utils.discord.User = await ctx.bot.fetch_user(int(player2.id))
                pfp = Image.open(BytesIO(await object_user2.avatar.with_size(128).read()))
                pfp = pfp.resize(pfp_size)
                # print(num, xy[1] + (pfp_user2.size[1] + 100), "par")
                xy[1] = xy[1] + (pfp.size[1] + 100)
                img.paste(pfp, tuple(xy))
                num += 1
            
            img.save("resource/img/dashboard.png")
            await ctx.send("Partidas generadas exitosamente!", file=utils.discord.File(
                fp="resource/img/dashboard.png",
                filename="dashboard.png"
            ))
            
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def games(self, ctx: Context, game_id=None):
        if game_id is not None:
            game = Game(ctx, game_id)
            embed = utils.discord.Embed(title="Game", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)
            embed.add_field(name="State:", value=f"```finished'```", inline=False)
            
            num = 1
            opponents = await game.opponents()
            for player in opponents.values():
                embed.add_field(name=f"Player {num}:", value=f"```{await player.name()}/{player.id}```")
                num += 1
                
            await ctx.send(embed=embed)
        else: 
            num = 1
            waiting = ctx.db.collection("tournamentc/games/waiting")
            async for doc_ref in waiting.list_documents():
                game = Game(ctx, doc_ref.id)
                embed = utils.discord.Embed(title=f"Game #{num}", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
                embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)

                _num = 1
                opponents = await game.opponents()
                for player in opponents.values():
                    embed.add_field(name=f"Player {_num}:", value=f"```{await player.name()}/{player.id}```")
                    object_user: utils.discord.User = await ctx.bot.fetch_user(int(player.id))
                    await ctx.send(f"Pfp user {await player.name()}:", file=utils.discord.File(
                        fp=BytesIO(await object_user.avatar.with_size(128).read()),
                        filename=f"{player.id}.png" 
                    ))
                    
                    _num += 1
                
                await ctx.send(embed=embed)
                num += 1

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def start_game(self, ctx: Context, game_id):
        game = Game(ctx, game_id)
        game_data = await game.start()
        if game_data is not None:
            channel: utils.discord.TextChannel = self.bot.get_channel(911764600146501674)
            await channel.send(file=await game.vs_image())
            
            channel2: utils.discord.TextChannel = self.bot.get_channel(921937676817530920)
            await channel2.send(game_data['game_links'][0])
    
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_new_game_link(self, ctx: Context):
        doc_ref = ctx.db.document("tournamentc/games")
        doc = await doc_ref.get()
        if doc.exists:
            playing = doc.to_dict().get("playing", {})
            if utils.is_empty(playing):
                await ctx.send("No hay un juego definido")
            else:
                game = Game(ctx, playing.get("game_id"))
                new_link = await game.get_new_link()
                
                doc_ref.update({"playing.game_links": ctx.db.ArrayUnion(new_link)})
                channel: utils.discord.TextChannel = self.bot.get_channel(921937676817530920)
                await channel.send(new_link)
        
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def winner(self, ctx: Context, member: utils.discord.Member):
        doc_ref = ctx.db.document("tournamentc/games")
        doc = await doc_ref.get()
        if doc.exists:
            playing = doc.to_dict().get("playing", {})
            if utils.is_empty(playing):
                await ctx.send("No se puede definir a un ganador porque no hay ningun juego iniciado 🙄")
            else:
                game = Game(ctx, playing.get("game_id"))
                await game.winner(member.id)
        

def setup(bot):
    bot.add_cog(Tournament_Chess(bot))
