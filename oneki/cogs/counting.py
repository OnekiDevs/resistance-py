import utils
from utils import ui
from utils.ui import confirm
from utils.context import Context
from typing import Optional, AsyncGenerator, TYPE_CHECKING

import math
import cmath

if TYPE_CHECKING:
    from utils.db import firestore
    DocumentSnapshot = firestore.firestore.DocumentSnapshot


class CountingStruct:
    def __init__(self, data: dict, *, guild: utils.discord.Guild) -> None:
        self.guild = guild
        
        self.channel_id = int(data["channel"])
        self.current_number = data.get("current_number", {"num": 0})
        self.current_number["num"] = int(self.current_number["num"])
        
        self.numbers_only = data.get("numbers_only", True)
        self.record = data.get("record", {"num": 0})
        self.record["num"] = int(self.record["num"])
        
        self.fail_role_id = data.get("fail_role")
        self.users = data.get("users", {})
    
    @property
    def channel(self):
        return self.guild.get_channel(self.channel_id)
    
    @property
    def fail_role(self) -> Optional[utils.discord.Role]:
        if self.fail_role_id is None:
            return None
        
        return self.guild.get_role(self.fail_role_id)
    
    def to_dict(self) -> dict:
        payload = {
            "channel": self.channel_id,
            "numbers_only": self.numbers_only
        }
        
        if self.current_number["num"] != 0:
            payload["current_number"] = self.current_number
        
        if self.record["num"] != 0:
            payload["record"] = self.record
            
        if self.fail_role_id is not None:
            payload["fail_role"] = self.fail_role_id
            
        if self.users:
            payload["users"] = self.users
        
        return payload
        

class GlobalStats(ui.View):
    name = "global_stats"
    
    def __init__(self, context, **kwargs):
        super().__init__(context, **kwargs)
        self.generator: Optional[AsyncGenerator[DocumentSnapshot]] = None
        self.embeds: list[utils.discord.Embed] = []
        self.num = 0
        
    async def generate_new_embed(self): 
        embed = utils.discord.Embed(
            title=self.translations.embed.title,
            colour=utils.discord.Colour.red(),
            timestamp=utils.utcnow()
        )
        
        num = 0
        while True:
            if num == 6:
                self.embeds.append(embed)
                return embed
            
            try:
                doc = await self.generator.__anext__()
                data = doc.to_dict()
                
                users = data.get("users", {})

                correct = 0
                for c in [user.get("correct", 0) for user in users.values()]:
                    correct += c
                
                incorrect = 0
                for i in [user.get("incorrect", 0) for user in users.values()]:
                    incorrect += i
                
                total = correct + incorrect
                
                correct_rate = math.floor(((correct * 100)/total) * 1000)/1000
                incorrect_rate = math.floor(((incorrect * 100)/total) * 1000)/1000
                content = self.translations.embed.field_value.format(
                    correct_rate,
                    utils.filled_bar(correct_rate),
                    incorrect_rate,
                    utils.filled_bar(incorrect_rate),
                    data["current_number"]["num"],
                    await self.ctx.bot.fetch_user(int(data["current_number"]["by"]))
                )
                
                try:
                    guild = await self.ctx.bot.fetch_guild(int(doc.id))
                except utils.discord.Forbidden:
                    continue
                    
                embed.add_field(name=guild, value=content)
            except Exception as e:
                if num != 0 or num == 6:
                    self.embeds.append(embed)
                    return embed
                
                raise e
            else:
                num += 1                    
        
    async def get_data(self, **kwargs):
        self.generator = self.ctx.db.collection("countings").order_by(
            "current_number.num", direction=self.ctx.db.Query.DESCENDING
        ).stream()

    async def get_embed(self) -> utils.discord.Embed:        
        try:
            return await self.generate_new_embed()
        except StopAsyncIteration:
            embed = utils.discord.Embed(
                title=self.translations.no_counts.title, 
                description=self.translations.no_counts.description,
                colour=utils.discord.Colour.red(),
                timestamp=utils.utcnow()
            )
            return embed

    async def update_components(self):
        if self.num == 0:
            self.back.disabled = True
        
        if (len(self.embeds) - 1) == self.num:
            self.next.disabled = False

    @ui.button(label="Back", emoji="⬅️", style=utils.discord.ButtonStyle.green)
    async def back(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        if self.num != 0:
            self.num -= 1
        
        await self.update_components()
        await interaction.response.edit_message(content=None, embed=self.embeds[self.num], view=self)
    
    @ui.button(label="Exit", style=utils.discord.ButtonStyle.red)
    async def exit(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _):
        await ui.view._StopButton.callback(button, interaction)
    
    @ui.button(label="Next", emoji="➡️", style=utils.discord.ButtonStyle.green)
    async def next(self, interaction: utils.discord.Interaction, button: utils.discord.ui.Button, _): 
        self.num += 1
        try:
            embed = self.embeds[self.num]
        except IndexError:
            try:
                embed = await self.generate_new_embed()
            except StopAsyncIteration:
                self.back.disabled = False
                button.disabled = True
                return await interaction.response.edit_message(content="Ya no hay mas servidores por explorar :(", embed=None, view=self)
                
        await self.update_components()
        await interaction.response.edit_message(embed=embed, view=self)


class Counting(utils.Cog):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.countings: dict[int, CountingStruct] = {}
        self.emojis = self.bot.bot_emojis

    async def cog_load(self):
        await self.get_countings() 

    async def get_countings(self):
        db = self.bot.db
        async for doc_ref in db.collection("countings").list_documents():
            if doc_ref.id != "users":
                doc = await doc_ref.get()
                try:
                    self.countings[int(doc_ref.id)] = CountingStruct(
                        doc.to_dict(), guild=await self.bot.fetch_guild(doc_ref.id)
                    )
                except utils.discord.Forbidden:
                    continue

    async def update_counting(self, doc_ref, guild_id, key, value): 
        await doc_ref.update({key: value})
        self.countings[guild_id][key] = value

    @utils.commands.hybrid_command()
    @utils.app_commands.checks.has_permissions(administrator=True)
    async def count_settings(
        self, 
        ctx: Context, 
        channel: utils.discord.TextChannel, 
        fail_role: Optional[utils.discord.Role] = None,
        numbers_only: Optional[bool] = None,
    ):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        counting = self.countings.get(ctx.guild.id)
        if counting is not None:
            if counting.channel_id != channel.id:
                counting.channel_id = channel.id
            
            if fail_role is not None:
                counting.fail_role_id = fail_role.id
                
            if numbers_only is not None:
                counting.numbers_only = numbers_only
                
            await doc_ref.update(counting.to_dict())
        else:
            data = {
                "channel": str(channel.id)
            }
            
            if fail_role is not None:
                data["fail_role"] = fail_role.id
                
            if numbers_only is not None:
                data["numbers_only"] = numbers_only
            
            self.countings[ctx.guild.id] = CountingStruct(data, guild=ctx.guild)
            await doc_ref.set(data)
            
        await ctx.send(ctx.translation.success)

    @utils.commands.hybrid_command()
    @utils.app_commands.checks.has_permissions(administrator=True)
    async def disable_counting(self, ctx: Context):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        view = confirm.Confirm(ctx, content=ctx.translation.confirm.content)
        await view.start(ephemeral=True)
        
        if view.value is None:
            await ctx.send(ctx.translation.confirm.timeout)
        elif view.value:
            await doc_ref.delete()
            self.countings.pop(doc_ref.id)
            
            await ctx.send(ctx.translation.confirm.ok)
        else:
            await ctx.send(ctx.translation.confirm.cancel)     
       
    @utils.commands.hybrid_command()
    async def global_stats(self, ctx: Context):
        view = GlobalStats(ctx)
        await view.start()
        
    @utils.commands.hybrid_command()
    async def server_stats(self, ctx: Context):
        counting = self.countings.get(ctx.guild.id)
        if counting is not None:
            embed = utils.discord.Embed(
                title=ctx.translation.embed.title,
                colour=utils.discord.Colour.purple(),
                timestamp=utils.utcnow()
            )
            
            embed.add_field(name=ctx.translation.embed.fields[0], value=counting.record["num"])
            record_dt = counting.record.get("time")
            if record_dt is not None:
                timestamp = utils.discord.utils.format_dt(record_dt, "R")
                embed.add_field(name=ctx.translation.embed.fields[1], value=timestamp)
            
            if counting.current_number["num"] != 0:
                embed.add_field(name=ctx.translation.embed.fields[2], value=counting.current_number["num"])
                
                by = await ctx.guild.fetch_member(int(counting.current_number["by"]))
                embed.add_field(name=ctx.translation.embed.fields[3], value=f"```{by}```", inline=False)
                
            await ctx.send(embed=embed)
        else:
            await ctx.send(ctx.translation.not_there_server_stats)
            
    @utils.commands.hybrid_command()
    async def user_stats(self, ctx: Context, member: utils.discord.Member = None):
        member = member or ctx.author
        doc = await ctx.db.document(f"users/{member.id}").get()
        embed = utils.discord.Embed(
            colour=utils.discord.Colour.purple(),
            timestamp=utils.utcnow()
        )

        embed.set_author(name=member, icon_url=member.display_avatar.url)
        
        data = doc.to_dict() or {}
        if global_stats := data.get("countings"):
            correct = global_stats.get("correct", 0)
            incorrect = global_stats.get("incorrect", 0)
            total = correct + incorrect
            
            correct_rate = math.floor(((correct * 100)/total) * 1000)/1000
            incorrect_rate = math.floor(((incorrect * 100)/total) * 1000)/1000
            content = ctx.translation.embed.field_value.format(
                correct_rate,
                utils.filled_bar(correct_rate),
                incorrect_rate,
                utils.filled_bar(incorrect_rate),
                correct,
                incorrect
            )
            embed.add_field(name="🌍 " + ctx.translation.embed.fields_names[0], value=content)
            
        server_stats = self.countings.get(ctx.guild.id)
        if server_stats is not None:
            server_stats = server_stats.users.get(str(member.id))
            
            correct = server_stats.get("correct", 0)
            incorrect = server_stats.get("incorrect", 0)
            total = correct + incorrect
            
            correct_rate = math.floor(((correct * 100)/total) * 1000)/1000
            incorrect_rate = math.floor(((incorrect * 100)/total) * 1000)/1000
            content = ctx.translation.embed.field_value.format(
                correct_rate,
                utils.filled_bar(correct_rate),
                incorrect_rate,
                utils.filled_bar(incorrect_rate),
                correct,
                incorrect
            )
            embed.add_field(name="📦 " + ctx.translation.embed.fields_names[1], value=content)

        await ctx.send(embed=embed)
           
    async def update_user_stats(self, *, guild_id: int, user_id: int, correct: bool):
        db = self.bot.db
        
        doc_ref = db.document(f"users/{user_id}")
        doc = await doc_ref.get()
        if doc.exists:
            if correct:
                await doc_ref.update({"countings.correct": db.Increment(1)})
            else:
                await doc_ref.update({"countings.incorrect": db.Increment(1)})
        else:
            await doc_ref.set({
                "countings": {
                    "correct": 1 if correct else 0,
                    "incorrect": 0 if correct else 1
                }
            })
        
        counting = self.countings.get(guild_id)
        if counting.users:
            if correct:
                user_stats = counting.users.get(str(user_id))
                if user_stats is not None:
                    num = user_stats.get("correct", 0)
                    user_stats.update({"correct": num + 1})
                else:
                    counting.users[str(user_id)] = {"correct": 1}
            else:
                user_stats = counting.users.get(str(user_id))
                if user_stats is not None:
                    num = user_stats.get("incorrect", 0)
                    user_stats.update({"incorrect": num + 1})
                else:
                    counting.users[str(user_id)] = {"incorrect": 1}
        else:
            counting.users = {
                str(user_id): {
                    "correct": 1 if correct else 0,
                    "incorrect": 0 if correct else 1
                }
            }
                                
    def increase_or_decrease_number(
        self, 
        counting: CountingStruct, 
        num: int, 
        by: utils.discord.Member, 
        message: utils.discord.Message
    ) -> int:
        if (counting.current_number["num"] + 1) == num:
            if counting.current_number.get("by") == str(by.id): 
                return 1
            
            if counting.record["num"] <= num:
                counting.record = {
                    "num": num,
                    "time": utils.utcnow()
                }
            
            counting.current_number = {
                "message": str(message.id),
                "num": counting.current_number["num"] + 1,
                "by": str(by.id)
            }
            
            return 0
        else:
            return 2

    async def pin(self, counting: CountingStruct, channel: utils.discord.TextChannel): 
        if message_id := counting.current_number.get("message"):
            if counting.current_number["num"] >= counting.record["num"]:
                old_message = await channel.fetch_message(int(message_id))
                try:
                    await old_message.pin()
                except utils.discord.HTTPException:
                    (await pin.unpin() for pin in await channel.pins())
                    await old_message.pin()

    async def add_fail_role(self, counting: CountingStruct, member: utils.discord.Member):
        fail_role = counting.fail_role
        if fail_role is not None:
            await member.add_roles(fail_role)
            await utils.asyncio.sleep(43200.0)            
            await member.remove_roles(fail_role)
    
    @utils.Cog.listener()
    async def on_message(self, message: utils.discord.Message): 
        if message.author.bot:
            return
        
        counting = self.countings.get(message.guild.id)
        if counting is not None:
            if message.channel.id == counting.channel_id:
                db = self.bot.db
                doc_ref = db.document(f"countings/{message.guild.id}")
                try:
                    content = message.content.replace("^", "**")
                    result = int(eval(content, {
                        "pow": math.pow, 
                        "factorial": math.factorial,
                        "sqrt": math.sqrt, 
                        "math": math,
                        "cmath": cmath
                    }, {}))
                except:
                    if counting.numbers_only:
                        await message.add_reaction(self.emojis["no"])

                        await self.update_user_stats(
                            guild_id=message.guild.id, 
                            user_id=message.author.id,
                            correct=False
                        )
                        
                        await self.pin(counting, message.channel)
                        
                        try: 
                            counting.pop("current_number")
                            await doc_ref.delete(camp="current_number")
                        except:
                            pass

                        await self.add_fail_role(counting, message.author)
                    
                    return
                        
                result = self.increase_or_decrease_number(counting, result, message.author, message)
                if result == 0:
                    await message.add_reaction(self.emojis["yes"])
                    await self.update_user_stats(
                        guild_id=message.guild.id, 
                        user_id=message.author.id,
                        correct=True
                    )
                    
                    await doc_ref.update(counting.to_dict())
                    return
                
                translation = self.translations.event(self.bot.get_guild_lang(message.guild), "counting")
                await message.add_reaction(self.emojis["no"])
                
                if result == 1:
                    await message.channel.send(
                        translation.count_twice_in_a_row.format(message.author.mention, self.emojis["disgustado"])
                    )
                else:
                    await message.channel.send(
                        translation.number_incorrect.format(message.author.mention, self.emojis["disgustado"])
                    )
                
                await self.update_user_stats(
                    guild_id=message.guild.id, 
                    user_id=message.author.id,
                    correct=False
                )
                
                await self.pin(counting, message.channel)
                
                counting.current_number = {"num": 0}
                await doc_ref.delete(camp="current_number")
                await self.add_fail_role(counting, message.author)
                            
    
async def setup(bot):
    await bot.add_cog(Counting(bot))
