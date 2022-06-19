import utils
from utils.ui import confirm
from utils.context import Context

import math
import cmath


class Counting(utils.Cog):
    def __init__(self, bot) -> None:
        super().__init__(bot)
        self.countings = {}
        self.emojis = {
            "yes": "<:yes:885693508533489694>",
            "no": "<:no:885693492632879104>",
            "disgustado": "<:perturbado:897292618692718622>"
        }

    async def cog_load(self):
        await self.get_countings()    

    async def get_countings(self):
        db = self.bot.db
        async for doc_ref in db.collection("countings").list_documents():
            if doc_ref.id != "users":
                doc = await doc_ref.get()
                self.countings[int(doc_ref.id)] = doc.to_dict()

    async def update_counting(self, doc_ref, guild_id, key, value): 
        await doc_ref.update({key: value})
        self.countings[guild_id][key] = value

    @utils.commands.hybrid_group()
    async def count_settings(self, ctx: Context):
        pass 

    @count_settings.command()
    async def set_channel(self, ctx: Context, channel: utils.discord.TextChannel):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        doc = await doc_ref.get()
        if doc.exists:
            await self.update_counting(doc_ref, ctx.guild.id, "channel", str(channel.id))
        else:
            data = {
                "channel": str(channel.id),
                "numbers_only": True,
                "record": 0
            }
            
            self.countings[ctx.guild.id] = data
            await doc_ref.set(data) 

        await ctx.send(ctx.translation.success)

    @count_settings.command()
    async def fail_role(self, ctx: Context, role: utils.discord.Role):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        try:
            await self.update_counting(doc_ref, ctx.guild.id, "fail_role", str(role.id))
            await ctx.send(ctx.translation.success)
        except:
            await ctx.send(ctx.translation.no_settings)

    @count_settings.command()
    async def numbers_only(self, ctx: Context, val: bool):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        try:
            await self.update_counting(doc_ref, ctx.guild.id, "numbers_only", val)
            await ctx.send(ctx.translation.success)
        except:
            await ctx.send(ctx.translation.no_settings)
            
    @count_settings.command()
    async def disable_counting(self, ctx: Context):
        doc_ref = ctx.db.document(f"countings/{ctx.guild.id}")
        
        async def get_content(self, _):
            return ctx.translation.confirm.content
        
        view = confirm.Confirm(ctx)
        view.get_content = get_content
        
        await view.start(ephemeral=True)
        if view.value is None:
            await ctx.send(ctx.translation.confirm.timeout)
        elif view.value:
            await doc_ref.delete()
            self.countings.pop(doc_ref.id)
            
            await ctx.send(ctx.translation.confirm.ok)
        else:
            await ctx.send(ctx.translation.confirm.cancel)     
       
    # @utils.commands.hybrid_command()
    # async def global_stats(self, ctx: Context):
    #     ...
        
    @utils.commands.hybrid_command()
    async def server_stats(self, ctx: Context):
        counting = self.countings.get(ctx.guild.id)
        if counting is not None:
            embed = utils.discord.Embed(
                title=ctx.translation.embed.title,
                colour=utils.discord.Colour.purple(),
                timestamp=utils.utcnow()
            )
            
            embed.add_field(name=ctx.translation.embed.fields[0], value=counting['record'])
            if recordt := counting.get("recordt"):
                timestamp = utils.discord.utils.format_dt(recordt, "R")
                embed.add_field(name=ctx.translation.embed.fields[1], value=timestamp,)
            
            current_number = counting.get("current_number")
            if current_number is not None:
                embed.add_field(name=ctx.translation.embed.fields[2], value=current_number['num'])
                
                by = await ctx.guild.fetch_member(int(current_number["by"]))
                embed.add_field(name=ctx.translation.embed.fields[3], value=f"```{by}```", inline=False)
                
            await ctx.send(embed=embed)
        else:
            await ctx.send(ctx.translation.not_there_server_stats)
            
    @utils.commands.hybrid_command()
    async def user_stats(self, ctx: Context, member: utils.discord.Member = None):
        member = member or ctx.author
        doc = await ctx.db.document("countings/users").get()
        embed = utils.discord.Embed(
            colour=utils.discord.Colour.purple(),
            timestamp=utils.utcnow()
        )

        embed.set_author(name=member, icon_url=member.display_avatar.url)
        
        data = doc.to_dict() or {}
        if global_stats := data.get(str(member.id)):
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
            
        server_stats = self.countings.get(ctx.guild.id, {}).get("users", {}).get(str(member.id))
        if server_stats is not None:
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
        
        doc_ref = db.document("countings/users")
        doc = await doc_ref.get()
        if doc.exists:
            if correct:
                await doc_ref.update({f"{user_id}.correct": db.Increment(1)})
            else:
                await doc_ref.update({f"{user_id}.incorrect": db.Increment(1)})
        else:
            await doc_ref.set({
                f"{user_id}": {
                    "correct": 1 if correct else 0,
                    "incorrect": 0 if correct else 1
                }
            })
        
        if users_stats := self.countings.get(guild_id).get("users"):
            if correct:
                user_stats = users_stats.get(str(user_id))
                if user_stats is not None:
                    num = user_stats.get("correct", 0)
                    user_stats.update({"correct": num + 1})
                else:
                    users_stats[str(user_id)] = {"correct": 1}
                  
                await db.document(f"countings/{guild_id}").update({f"users.{user_id}.correct": db.Increment(1)})
            else:
                user_stats = users_stats.get(str(user_id))
                if user_stats is not None:
                    num = user_stats.get("incorrect", 0)
                    user_stats.update({"incorrect": num + 1})
                else:
                    users_stats[str(user_id)] = {"incorrect": 1}
                    
                await db.document(f"countings/{guild_id}").update({f"users.{user_id}.incorrect": db.Increment(1)})
        else:
            self.countings[guild_id]["users"] = {
                "correct": 1 if correct else 0,
                "incorrect": 0 if correct else 1
            }
                                
    def increase_or_decrease_number(self, counting: dict, num: int, by: utils.discord.Member):
        current_number = counting.pop("current_number", {"num": 0})
        if (int(current_number["num"]) + 1) == num:
            if current_number.get("by") == str(by.id): 
                return None
            
            if int(counting["record"]) < num:
                counting["record"] = num
                counting["recordt"] = utils.utcnow()
            
            counting["current_number"] = {
                "num": int(current_number["num"]) + 1,
                "by": str(by.id)
            }
            
            return True
        else:
            return False
            
    @utils.Cog.listener()
    async def on_message(self, message: utils.discord.Message): 
        if message.author.bot:
            return
        
        counting: dict = self.countings.get(message.guild.id)
        if counting is not None:
            if str(message.channel.id) == counting["channel"]:
                db = self.bot.db
                doc_ref = db.document(f"countings/{message.guild.id}")
                try:
                    result = int(eval(message.content, {
                        "pow": math.pow, 
                        "factorial": math.factorial,
                        "sqrt": math.sqrt, 
                        "math": math,
                        "cmath": cmath
                    }, {}))
                except:
                    if counting["numbers_only"]:
                        await message.add_reaction(self.emojis["no"])
                        
                        await self.update_user_stats(
                            guild_id=message.guild.id, 
                            user_id=message.author.id,
                            correct=False
                        )
                        
                        try: 
                            counting.pop("current_number")
                            await doc_ref.delete(camp="current_number")
                        except:
                            pass
                        
                        return
                        
                increase = self.increase_or_decrease_number(counting, result, message.author)
                if increase:
                    await message.add_reaction(self.emojis["yes"])
                    
                    await doc_ref.update(counting)
                    await self.update_user_stats(
                        guild_id=message.guild.id, 
                        user_id=message.author.id,
                        correct=True
                    )
                    
                    return
                
                await message.add_reaction(self.emojis["no"])
                
                if increase is None:
                    await message.channel.send(f"¡¡Lo arruinaste!! {self.emojis['disgustado']}, No puedes contar 2 veces consecutivas")
                else:
                    await message.channel.send(f"¡¡Lo arruinaste!! {self.emojis['disgustado']}, El numero es incorrecto")
                
                await self.update_user_stats(
                    guild_id=message.guild.id, 
                    user_id=message.author.id,
                    correct=False
                )
                await doc_ref.delete(camp="current_number")
                            
    
async def setup(bot):
    await bot.add_cog(Counting(bot))