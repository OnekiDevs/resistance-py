import uuid

import utils
from utils.context import Context
from utils.views import confirm, forms


class Player:
    def __init__(self, user_id):
        self._document = utils.db.Document(collection="tournamentc", document="participants")
        self.id = str(user_id)
    
    @property
    def data(self) -> dict:
        return self._document.content.get(self.id)
    
    @property
    def name(self) -> str:
        return self.data.get('name')
    
    def delete(self):
        self._document.delete(self.id)


class Game:
    def __init__(self, ctx: Context, game_id):
        self.ctx = ctx
        self.id = str(game_id)
        self._document = utils.db.Document(collection="tournamentc", document="games")
        self._waiting = utils.db.Document(collection="tournamentc", document="games", subcollection="waiting", subdocument=self.id)
        self._finished = utils.db.Document(collection="tournamentc", document="games", subcollection="finished", subdocument=self.id)
    
    @property
    def waiting(self):
        return self._waiting.exists
    
    @property
    def playing(self):
        if utils.is_empty(self._document.content.get("playing")):
            return None
        
        return self._document.content.get("playing").get("game_id") == self.id
    
    @property
    def finished(self):
        return self._finished.exists
    
    @property
    def opponents(self) -> dict[Player] or None:
        if self.waiting:
            return {player_id: Player(player_id) for player_id in self._waiting.content.get("opponents")}
        elif self.finished:
            return {player_id: Player(player_id) for player_id in self._finished.content.get("opponents")}
        elif self.playing: 
            return {player_id: Player(player_id) for player_id in self._document.content.get("playing").get("opponents")}
        else: return None
        
    async def start(self):
        if self.waiting == False:
            return await self.ctx.send("Nop, nada que ver por aqui, la partida no existe o ya fue terminada <:awita:852216204512329759>")
        
        data = self._waiting.content
        data["game_id"] = self.id
        data["game_link"] = None
        
        if self.playing is None:
            self._waiting.delete()
            self._document.update("playing", data)

            for role in self.ctx.guild.roles:
                if role.id == 913036870701682699:
                    await self.ctx.author.add_roles(role)
                    
            await self.ctx.send("Partida iniciada!")
        else:
            await self.ctx.send("Lo siento, ya hay una partida en curso 🙄")
    
    async def winner(self, user_id):
        if self.playing:
            opponents = self.opponents
            data = self._document.content.get("playing")
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
                    await self.ctx.author.remove_roles(role)
            
            await self.ctx.send("Partida finalizada y ganador establecido")
        else: 
            await self.ctx.send("No se puede definir a un ganador porque este juego no se a iniciado 🙄")
        
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
            
            embed: utils.discord.Embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.set_author(name=player.name, icon_url=player.data.get('pfp'))
            embed.add_field(name="ID:", value=f"`{player.id}`")
            embed.add_field(name="Country:", value=f"`{player.data.get('country')}`")
            embed.add_field(name="Question:", value=f"`{player.data.get('question')}`")
            
            await ctx.send(embed=embed)
        else:    
            num = 1
            players = utils.db.Document(collection="tournamentc", document="participants")
            for user_id, data in players.content.items():
                embed: utils.discord.Embed = utils.discord.Embed(colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
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

        view = confirm.Confirm()
        await ctx.send(f"Seguro que quieres descalificar a {member.name}#{member.discriminator}?", view=view)

        await view.wait()
        if view.value is None:
            await ctx.send("Se te acabó el tiempo, intenta pensarlo antes de navidad 🙄")
        elif view.value:
            player.delete()
            await ctx.send(f"{member.name}#{member.discriminator} fue descalificado :(")

        
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def generate_games(self, ctx: Context):
        collection = utils.db.Collection(collection="tournamentc", document="games", subcollection="waiting")
        collection.delete()
        
        players = list(utils.db.Document(collection="tournamentc", document="participants").content.keys())
        while utils.is_empty(players) == False:
            if len(players) == 1:
                break

            player1 = Player(utils.random.choice(players))
            players.pop(players.index(player1.id))
            
            player2 = Player(utils.random.choice(players))
            players.pop(players.index(player2.id))
            
            id = str(uuid.uuid1().int)
            collection.set(id, opponents=[player1.id, player2.id])
            
            await ctx.send("Partidas generadas exitosamente!")
            
    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def games(self, ctx: Context, game_id=None):
        if game_id is not None:
            game = Game(ctx, game_id)
            embed = utils.discord.Embed(title="Game", colour=utils.discord.Colour.blue(), timestamp=utils.datetime.datetime.utcnow())
            embed.add_field(name="ID:", value=f"```{game.id}```", inline=False)
            
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
                    _num += 1
                
                await ctx.send(embed=embed)
                num += 1

    @utils.commands.command(hidden=True)
    @utils.commands.has_permissions(administrator=True)
    async def start_game(self, ctx: Context, game_id):
        game = Game(ctx, game_id)
        await game.start()
        
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
