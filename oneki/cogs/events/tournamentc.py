import uuid
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

import utils
from utils.context import Context
from utils.views import confirm, forms

import aiohttp


class Player:
    def __init__(self, user_id):
        self._participants_document = utils.db.Document(collection="tournamentc", document="participants")
        self._eliminated_document = utils.db.Document(collection="tournamentc", document="eliminated")
        self.id = str(user_id)
    
    @property
    def eliminated(self) -> bool:
        return True if self._eliminated_document.content.get(self.id, None) is not None else False
    
    @property
    def data(self) -> dict:
        return self._participants_document.content.get(self.id, self._eliminated_document.content.get(self.id))
    
    @property
    def name(self) -> str:
        return self.data.get('name')
    
    def delete(self):
        self._eliminated_document.update(self.id, self.data)
        self._participants_document.delete(self.id)


class Game:
    def __init__(self, ctx: Context, game_id):
        self.ctx = ctx
        self.id = str(game_id)
        self._document = utils.db.Document(collection="tournamentc", document="games")
        self._waiting = utils.db.Document(collection="tournamentc", document="games", subcollection="waiting", subdocument=self.id)
        self._finished = utils.db.Document(collection="tournamentc", document="games", subcollection="finished", subdocument=self.id)
    
    @property
    def waiting(self) -> bool:
        return self._waiting.exists
    
    @property
    def playing(self) -> bool:
        return None if utils.is_empty(self._document.content.get("playing")) else self._document.content.get("playing").get("game_id") == self.id
    
    @property
    def finished(self) -> bool:
        return self._finished.exists
    
    @property
    def round(self):
        return self._finished.content.get("round") if self._finished else self._document.content.get("round")
    
    @property
    def opponents(self) -> dict or None:
        if self.waiting:
            return {player_id: Player(player_id) for player_id in self._waiting.content.get("opponents")}
        elif self.finished:
            return {player_id: Player(player_id) for player_id in self._finished.content.get("opponents")}
        elif self.playing: 
            return {player_id: Player(player_id) for player_id in self._document.content.get("playing").get("opponents")}
        else: return None

    async def get_new_link(self):
        response = await self.ctx.session.post(
            f"https://lichess.org/api/tournament",
            headers={'Content-Type': 'application/json', 'Authorization': f"Bearer {utils.env.TOKEN_LICHESS}"},
            json={'name':f"LR Tournament 2021", 
                    'clockTime': 5, 
                    'clockIncrement': 3, 
                    'minutes': 120, 
                    'waitMinutes': 5}
        )
        
        data = await response.json()
        print(data['id'])
        return f"https://lichess.org/tournament/{data['id']}"
        
    async def start(self):
        if self.playing is None:
            if self.waiting == False:
                await self.ctx.send("Nop, nada que ver por aqui, la partida no existe o ya fue terminada <:awita:852216204512329759>")
                return None

            data = self._waiting.content
            data["game_id"] = self.id
            data["game_links"] = [await self.get_new_link()]

            self._waiting.delete()
            self._document.update("playing", data)

            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    for player_id in self.opponents.keys():
                        object_member: utils.discord.Member = await self.ctx.guild.fetch_member(int(player_id))
                        await object_member.add_roles(role)
                    
            await self.ctx.send("Partida iniciada!")
            return data
        else:
            await self.ctx.send("Lo siento, ya hay una partida en curso 🙄")
            return None
    
    async def winner(self, user_id):
        if self.playing:
            opponents = self.opponents
            data = self._document.content.get("playing")
            # data['round'] = self.round
            data.pop("game_id")
            for player_id, player_object in opponents.items():
                if player_id == str(user_id):
                    data["winner"] = player_object.id
                else:
                    player_object.delete()

            self._document.delete("playing")
            self._finished.set(content=data)
            
            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    for player_id in self.opponents.keys():
                        object_member: utils.discord.Member = await self.ctx.guild.fetch_member(int(player_id))
                        await object_member.remove_roles(role)
            
            await self.ctx.send("Partida finalizada y ganador establecido")
        else: 
            await self.ctx.send("No se puede definir a un ganador porque este juego no se a iniciado 🙄")

    async def vs_image(self):
        if self.opponents is not None:
            img = Image.open("resource/img/vs_template.png")
            num = 0
            for player_id in self.opponents.keys():
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
        self._waiting.delete()


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
        await ctx.author.send("Pronto estará lista tu inscripción al torneo!, solo necesitamos que llenes este pequeño formulario:", embed=form.embed, view = form)

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def players(self, ctx: Context, member: utils.discord.Member=None):
        if member is not None:
            player = Player(member.id)

            embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name=player.name, icon_url=player.data.get('pfp'))
            embed.add_field(name="ID:", value=f"`{player.id}`", inline=False)
            embed.add_field(name="Eliminated?:", value=f"`{player.eliminated}`")
            embed.add_field(name="Country:", value=f"`{player.data.get('country')}`")
            embed.add_field(name="Question:", value=f"`{player.data.get('question')}`")
            
            await ctx.send(embed=embed)
        else:    
            num = 1
            players = utils.db.Document(collection="tournamentc", document="participants")
            for user_id, data in players.content.items():
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
        player = Player(member.id)
        if player.eliminated == False:
            view = confirm.Confirm()
            await ctx.send(f"Seguro que quieres descalificar a {member.name}#{member.discriminator}?", view=view)

            await view.wait()
            if view.value is None:
                await ctx.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")
            elif view.value:
                player.delete()
                await ctx.send(f"{member.name}#{member.discriminator} fue descalificado :(")
        else:
            await ctx.send(f"{member.name}#{member.discriminator} ya esta descalificado o no esta en la lista de participantes 🙄")

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_games(self, ctx: Context):
        collection = utils.db.Collection(collection="tournamentc", document="games", subcollection="waiting")
        collection.delete()
        
        players = list(utils.db.Document(collection="tournamentc", document="participants").content.keys())
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
            collection.set(id_game, opponents=[player1.id, player2.id])

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
            embed.add_field(name="State:", value=f"```{'waiting' if game.waiting else 'finished'}```", inline=False)
            
            num = 1
            for player in game.opponents.values():
                embed.add_field(name=f"Player {num}:", value=f"```{player.name}/{player.id}```")
                num += 1
                
            await ctx.send(embed=embed)
        else: 
            num = 1
            waiting = utils.db.Collection(collection="tournamentc", document="games", subcollection="waiting")
            for game_document in waiting.documents():
                game = Game(ctx, game_document.id)
                embed = utils.discord.Embed(title=f"Game #{num}", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
                embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)

                _num = 1
                for player in game.opponents.values():
                    embed.add_field(name=f"Player {_num}:", value=f"```{player.name}/{player.id}```")
                    object_user: utils.discord.User = await ctx.bot.fetch_user(int(player.id))
                    await ctx.send(f"Pfp user {player.name}:", file=utils.discord.File(
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
        playing = utils.db.Document(collection="tournamentc", document="games")
        if utils.is_empty(playing.content.get("playing", {})):
            await ctx.send("No hay un juego definido")
        else:
            game = Game(ctx, playing.get("game_id"))
            new_link = await game.get_new_link()
            
            playing.update("playing.game_links", new_link, array=True)
            channel: utils.discord.TextChannel = self.bot.get_channel(921937676817530920)
            await channel.send(new_link)
        
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def winner(self, ctx: Context, member: utils.discord.Member):
        playing = utils.db.Document(collection="tournamentc", document="games").content.get("playing", {})
        if utils.is_empty(playing):
            await ctx.send("No se puede definir a un ganador porque no hay ningun juego iniciado 🙄")
        else:
            game = Game(ctx, playing.get("game_id"))
            await game.winner(member.id)
        

def setup(bot):
    bot.add_cog(Tournament_Chess(bot))
