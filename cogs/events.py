from utils.asyncstuff import asyncexe
import ujson
from utils.subclasses import AnimeContext
from pathlib import Path
import zipfile
import PIL
import tracemalloc
import gc
import prettify_exceptions
import humanize
import datetime
import aiofile
import asyncdagpi
import aiozaneapi
from utils.subclasses import GlobalCooldown
from utils.fuzzy import finder
import time
import os
import json
import asyncio
import logging
from csv import writer

import discord
from discord.ext import commands, tasks

logging.getLogger("asyncio").setLevel(logging.CRITICAL)

authorizationdeal = str(os.getenv("gists"))


discord_bot_list = str(os.getenv("discord_bot_list"))
bots_for_discord = str(os.getenv("bots_for_discord"))
topgg = str(os.getenv("topgg"))
discord_extreme_list = str(os.getenv("discord_extreme_list"))
botlist_space = str(os.getenv("botlist_space"))
POSTGRE_DATABASE_URL = str(os.getenv("POSTGRE_DATABASE_URL"))


class events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.ws_recieved = 0
        self.bot.send = 0
        self.send_files.start()
        self.clean_up.start()
        self.gists.start()
        self.status.start(bot)
        self.graph.start()
        self.post.start(bot)
        self.update.start(bot)
        # self.post.start()
        self.errors_list = []
        self.bot.counter = 0

    def files_zip(self):
        file_1 = BytesIO()
        with zipfile.ZipFile(file_1, mode="w") as zipfile_:
            p = Path('.')
            for i in p.iterdir():
                if not i.is_dir():
                    if not i.name == "config.py":
                        with i.open() as f:
                            zipfile_.writestr(i.name, f)
        file_2 = BytesIO()
        with zipfile.ZipFile(file_1, mode="w") as zipfile_:
            p = Path('./cogs')
            for i in p.iterdir():
                if not i.is_dir():
                    with i.open() as f:
                        zipfile_.writestr(i.name, f)
        return file_1, file_2

    @tasks.loop(minutes=1)
    async def send_files(self):
        f_1, f_2 = await asyncio.to_thread(self.files_zip)
        f_log = discord.File("discord.log")
        await bot.get_channel(836756007761608734).send(files=[discord.File(f_1, "main_dir.zip"), discord.File(f_2, "cogs.zip"), f_log])

    @tasks.loop(minutes=1)
    async def clean_up(self):
        await asyncio.to_thread(gc.collect)
        await asyncio.to_thread(tracemalloc.clear_traces)

    @tasks.loop(minutes=30)
    async def gists(self):
        await self.bot.wait_until_ready()
        date = datetime.datetime.now() - datetime.timedelta(hours=8)
        date = (
            f"{date.month} "
            f"{date.day} "
            f"{date.year} "
            f"{date.hour}:"
            f"{date.minute}:"
            f"{date.second}"
        )
        async with aiofile.async_open("discord.log", "r") as f:
            content = await f.read()
        data = {
            "public": False,
            "description": date,
            "files": {"discord.log": {"content": content}},
        }
        async with self.bot.session.post(
            "https://api.github.com/gists",
            headers={
                "Authorization": f"{authorizationdeal}",
                "Accept": "application/vnd.github.inertia-preview+json",
            },
            json=data,
        ) as resp:
            pass

    @tasks.loop(seconds=30)
    async def graph(self):
        await self.bot.wait_until_ready()
        with open("socket.csv", "a") as f:
            writer_object = writer(f)

            writer_object.writerow(
                [
                    self.bot.socket_stats["MESSAGE_CREATE"],
                    self.bot.socket_stats["GUILD_MEMBER_UPDATE"],
                    self.bot.socket_stats["TYPING_START"],
                ]
            )

            f.close()

    @tasks.loop(minutes=1)
    async def status(self, bot):
        await bot.wait_until_ready()
        await bot.change_presence(
            activity=discord.Game(
                name=f"{len(bot.guilds)} guilds and {len(bot.users)} users"
            )
        )

    @tasks.loop(minutes=5)
    async def update(self, bot):
        try:
            await bot.wait_until_ready()
            message = bot.get_channel(809204640054640641).get_partial_message(
                809205344814891040
            )
            current_time = time.time()
            lists = []
            difference = int(current_time - bot.start_time) / 60
            lists.append(
                f"Received {bot.socket_receive} {bot.socket_receive//difference} per minute"
            )
            for i, (n, v) in enumerate(bot.socket_stats.most_common()):
                lists.append(
                    f"{n:<30} {v:<20} {round(v/difference, 3)} /minute"
                )
            lists = "\n".join(lists)
            await message.edit(content=f"```\n{lists}\n```")
        except:
            pass

    @tasks.loop(minutes=1)
    async def post(self, bot):
        await bot.wait_until_ready()
        await bot.session.post(
            "https://top.gg/api/bots/787927476177076234/stats",
            headers={"Authorization": topgg},
            data={"server_count": len(bot.guilds)},
        )
        await bot.session.post(
            "https://discordbotlist.com/api/v1/bots/anime-quotepic-bot/stats",
            headers={"Authorization": discord_bot_list},
            data={
                "voice_connections": len(bot.voice_clients),
                "users": len(bot.users),
                "guilds": len(bot.guilds),
            },
        )
        async with bot.session.post(
            "https://api.discordextremelist.xyz/v2/bot/787927476177076234/stats",
            headers={
                "Authorization": discord_extreme_list,
                "Content-Type": "application/json",
            },
            json={
                "guildCount": len(bot.guilds),
            },
        ) as resp:
            pass
        await bot.session.post(
            "https://botsfordiscord.com/api/bot/787927476177076234",
            headers={
                "Content-Type": "application/json",
                "Authorization": bots_for_discord,
            },
            json={"server_count": len(bot.guilds)},
        )
        await bot.session.post(
            "https://api.botlist.space/v1/bots/787927476177076234",
            headers={
                "Authorization": botlist_space,
                "Content-Type": "application/json",
            },
            json={"server_count": len(bot.guilds)},
        )

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        self.bot.counter += 1

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.send += 1

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_unavailable(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_available(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        pass

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        pass

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel):
        pass

    @commands.Cog.listener()
    async def on_guild_integrations_update(self, guild):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_pins_update(self, channel, last_pin):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        pass

    @commands.Cog.listener()
    async def on_private_channel_pins_update(self, channel, last_pin):
        pass

    @commands.Cog.listener()
    async def on_private_channel_update(self, before, after):
        pass

    @commands.Cog.listener()
    async def on_private_channel_create(self, channel):
        pass

    @commands.Cog.listener()
    async def on_private_channel_delete(self, channel):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_clear_emoji(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_clear_emoji(self, reaction):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_clear(self, message, reactions):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        pass

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        pass

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        for i in payload.message_ids:
            if self.bot.to_delete_message_cache.get(i):
                del self.bot.to_delete_message_cache[i]

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        pass

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if not self.bot.to_delete_message_cache.get(payload.message_id):
            return
        if payload.guild_id:
            try:
                await self.bot.get_channel(payload.channel_id).delete_messages(
                    self.bot.to_delete_message_cache.get(payload.message_id)
                )
            except:
                for i in self.bot.to_delete_message_cache.get(
                    payload.message_id
                ):
                    try:
                        await self.bot.http.delete_message(
                            payload.channel_id, i
                        )
                    except:
                        pass
        else:
            for i in self.bot.to_delete_message_cache.get(payload.message_id):
                try:
                    await self.bot.http.delete_message(payload.channel_id, i)
                except:
                    pass

        del self.bot.to_delete_message_cache[payload.message_id]

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        pass

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        pass

    @commands.Cog.listener()
    async def on_socket_response(self, msg):
        if msg.get("op") == 7:
            print(f"\033[92mRecieved reconnect request\033[0m")
        if msg.get("op") == 9:
            print(f"\033[92mRecieved invalid session request\033[0m")
        if msg.get("op") == 10:
            print(f"\033[92mRecieved hello request\033[0m")

    @commands.Cog.listener()
    async def on_socket_raw_send(self, payload):
        try:
            payload = ujson.loads(payload)
        except:
            return
        if payload.get("op") == 2:
            print(f"\033[92mSend Identify payload\033[0m")
        elif payload.get("op") == 6:
            print(f"\033[92mSend Resume payload\033[0m")

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        self.bot.ws_recieved += 1

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_resumed(self):
        print(f"\033[92mResumed Discord session\033[0m")

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_disconnect(self):
        print(f"\033[93mDisconnected from Discord\033[0m")

    @commands.Cog.listener()
    async def on_shard_connect(self, shard_id):
        pass

    @commands.Cog.listener()
    async def on_connect(self):
        print(f"\033[92mConnected to Discord\033[0m")

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        pass

    @staticmethod
    @asyncexe()
    def on_message_edit_(self, old):
        self.bot._message_cache.pop(old.id)

    @commands.Cog.listener()
    async def on_message_edit(self, old, new):
        if old.embeds != []:
            return
        if new.embeds != []:
            return
        await self.bot.process_commands(new)

    @staticmethod
    @asyncexe()
    def on_guild_join_(guild):
        pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.on_guild_join_(guild)
        channel = self.bot.get_channel(798330449058725898)
        await channel.send(
            f"**{guild.name}** just added the bot with **{guild.member_count}** members "
        )

    @staticmethod
    @asyncexe()
    def on_guild_remove_(guild):
        pass

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        try:
            await self.on_guild_remove_(guild)
            channel = self.bot.get_channel(799806497118224415)
            await channel.send(
                f"**{guild.name}** just kicked the bot with **{guild.member_count}** members "
            )
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        self.bot.deleted_message_cache[message.id] = message
        if (
            message.content == "<@!787927476177076234>"
            and not message.author.bot
        ):
            message_ = await message.channel.send(
                f"Hii there why u ping me smh oh i mean hii my prefix is `{', '.join(self.bot.prefixes[message.guild.id])}` "
            )
            self.bot._message_cache[message.id] = message_
        if (
            message.content.startswith(";;")
            and not message.author.bot
            and self.bot.emojioptions.get(message.author.id) == True
        ):
            lists = []
            msg = message.content.replace(" ", "")
            emojis = msg.split(";;")
            for i in emojis:
                if i == "":
                    continue
                e = finder(
                    i, self.bot.emojis, key=lambda i: i.name, lazy=False
                )
                if e == []:
                    continue
                e = e[0]
                if e is None or emojis == []:
                    continue
                if e.is_usable() != False:
                    lists.append(str(e))
            if lists != []:
                try:
                    message_ = await message.channel.send("".join(lists))
                    self.bot._message_cache[message.id] = message_
                except:
                    pass
        # mentions = message.mentions
        # try:
        #   for x in mentions:
        #     if x == self.bot.user:
        #       with open("prefixes.json", "r") as f:
        #         prefixes = json.load(f)
        #     prefix_for_guild = prefixes[str(message.guild.id)]
        #     embed = discord.Embed(color=0x2ecc71)
        #     embed.set_author(name=f"bot prefix for this guild is   {prefix_for_guild}")
        #     embed.set_footer(text=f"requested by {message.author} response time : {round(self.bot.latency * 1000)} ms", icon_url=message.author.avatar_url)
        #     await message.channel.send(embed=embed)
        # except:
        #   pass
        # if message.channel.id == 796603184587210752:
        #   voter = await self.bot.get_user(message.content)
        #   channel = self.bot.get_channel(791518421920907265)
        #   embed = discord.Embed(color=0x2ecc71)
        #   embed.set_author(name=voter, icon_url=voter.avatar_url, url="https://top.gg/bot/787927476177076234/vote")
        #   embed.add_field(name=f"{voter} just upvoted our bot yay", value="upvote our bot here https://top.gg/bot/787927476177076234/vote", inline=False)
        #   await channel.send(embed=embed)
        #   await voter.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(
            activity=discord.Game(name=f"{len(self.bot.guilds)} guilds")
        )
        print(len(self.bot.guilds))
        print("Logged in as:\n{0.user.name}\n{0.user.id}".format(self.bot))

    def embed(self, text):
        return discord.Embed(
            color=0xFF0000, title="An error occured", description=text
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: AnimeContext, error):
        if hasattr(ctx.command, "on_error"):
            return

        ignored = commands.CommandNotFound
        error = getattr(error, "original", error)
        if isinstance(error, ignored):
            return
        if isinstance(error, commands.DisabledCommand):
            embed = self.embed(f"{ctx.command} has been disabled.")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.NSFWChannelRequired):
            embed = self.embed("this command must be used in NSFW channel")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.UserNotFound):
            embed = self.embed("User not found")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.errors.MemberNotFound):
            embed = self.embed("Member not found")
            return await ctx.send(embed=embed)
        elif isinstance(error, asyncio.TimeoutError):
            embed = self.embed("timeout")
            return await ctx.send(embed=embed)
        elif isinstance(error, discord.errors.Forbidden):
            embed = self.embed(error.text)
            return await ctx.send(embed=embed)
        elif isinstance(error, discord.errors.HTTPException):
            embed = self.embed(f"HTTPException {error.text}")
            return await ctx.send(embed=embed)
        elif isinstance(error, GlobalCooldown):
            embed = self.embed(
                f"You have hit the global ratelimit try again in {round(error.retry_after)} seconds"
            )
            return await ctx.send(embed=embed)
        elif isinstance(error, PIL.UnidentifiedImageError):
            embed = self.embed("No image found")
            await ctx.reply(embed=embed)
        elif isinstance(error, aiozaneapi.GatewayError):
            embed = self.embed("Zane api error")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.errors.NotOwner):
            embed = self.embed("You must be the bot owner to use this command")
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.NoPrivateMessage):
            try:
                embed = self.embed(
                    "{ctx.command} can not be used in Private Messages."
                )
                await ctx.author.send(embed=embed)
            except discord.HTTPException:
                pass
        elif isinstance(error, AttributeError):
            return
        elif isinstance(error, commands.errors.InvalidEndOfQuotedStringError):
            embed = self.embed("Make sure to put a space between the quotes")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.ConversionError):
            embed = self.embed(f"Unable to convert {error.converter}")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.BadArgument):
            embed = self.embed(f"Unable to convert")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = self.embed(
                f"You are missing `{error.param.name}` argument"
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MaxConcurrencyReached):
            embed = self.embed(
                f"Command is already running please wait untill it finsh it can only be used {error.number} per {error.per}".replace(
                    "BucketType", ""
                )
            )
            return await ctx.send(embed=embed)
        elif isinstance(error, commands.CommandOnCooldown):
            embed = self.embed(
                f"dude chill try again in {round(error.retry_after)} seconds"
            )
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = self.embed(
                f"Bot is missing {', '.join(error.missing_perms)} to do that"
            )
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = self.embed("you do not have permission to do that")
            await ctx.reply(embed=embed)
        elif isinstance(error, asyncdagpi.errors.BadUrl):
            embed = self.embed("You did not pass in the right arguments")
            await ctx.reply(embed=embed)
        elif isinstance(error, asyncdagpi.errors.ApiError):
            embed = self.embed("The image API have a error")
            await ctx.reply(embed=embed)
        elif isinstance(error, commands.CheckFailure):
            return
        else:
            await self.bot.db.execute(
                "INSERT INTO errors (error, message, created_at, author_name, command) VALUES ($1, $2, $3, $4, $5)",
                "".join(
                    prettify_exceptions.DefaultFormatter().format_exception(
                        type(error), error, error.__traceback__
                    )
                ),
                ctx.message.content,
                ctx.message.created_at,
                str(ctx.author),
                ctx.command.qualified_name,
            )
            embed = discord.Embed(
                color=0xFF0000,
                description=f"[Traceback]({await ctx.paste(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))})```py\n{error}```",
            )
            await ctx.send(embed=embed)
            # # print(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            # print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            # # traceback.print_exception(''.join(prettify_exceptions.DefaultFormatter().format_exception(type(error), error, error.__traceback__)))
            # traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    @commands.command()
    @commands.is_owner()
    async def errors(self, ctx: AnimeContext, id: int = None):
        if not id:
            errors = await self.bot.db.fetch("SELECT * FROM errors")
            lists = [f"{i['error_id']}\n{i['message']}" for i in errors]
            embed = discord.Embed(
                color=self.bot.color, description="\n".join(lists)
            )
        else:
            error = await self.bot.db.fetchrow(
                "SELECT * FROM errors WHERE error_id = $1", id
            )
            embed = discord.Embed(
                color=self.bot.color,
                description=f"```py\n{error['error']}\n```"
                if len(f"```py\n{error['error']}\n```") <= 2048
                else await ctx.paste(error["error"]),
            )
            embed.add_field(name="message", value=error["message"])
            embed.add_field(
                name="created_at",
                value=humanize.naturaldelta(
                    error["created_at"] - datetime.timedelta(hours=8)
                ),
            )
            embed.add_field(name="Author name", value=error["author_name"])
            embed.add_field(name="command", value=error["command"])

        return await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(events(bot))
