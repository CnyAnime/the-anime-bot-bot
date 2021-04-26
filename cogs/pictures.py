import discord
from discord.ext import commands
import ujson
import qrcode
from utils.subclasses import AnimeContext
from qrcode.image.pure import PymagingImage
from pyzbar.pyzbar import decode
import re
import ratelimiter
import config
import flags
import functools
import aiohttp
import asyncio
from twemoji_parser import emoji_to_url
import typing
import os
from utils.asyncstuff import asyncexe
import polaroid
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
from PIL import ImageSequence
from PIL import ImageOps
from io import BytesIO
from asyncdagpi import ImageFeatures
import typing

ree = re.compile(r"\?.+")
authorizationthing = config.ksoft


class pictures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_cdn_ratelimiter = ratelimiter.RateLimiter(
            max_calls=1, period=6
        )
        self.cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=3, period=7)
        self.ocr_ratelimiter = ratelimiter.RateLimiter(max_calls=2, period=10)

    async def get_gif_url(self, ctx: AnimeContext, thing, **kwargs):
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        if ctx.message.reference:
            message = ctx.message.reference.resolved
            if message.embeds and message.embeds[0].type == "image":
                url = message.embeds[0].thumbnail.proxy_url
                url = url.replace("cdn.discordapp.com", "media.discordapp.net")
                return url
            elif message.embeds and message.embeds[0].type == "rich":
                if message.embeds[0].image.proxy_url:
                    url = message.embeds[0].image.proxy_url
                    url = url.replace(
                        "cdn.discordapp.com", "media.discordapp.net"
                    )
                    return url
                elif message.embeds[0].thumbnail.proxy_url:
                    url = message.embeds[0].thumbnail.proxy_url
                    url = url.replace(
                        "cdn.discordapp.com", "media.discordapp.net"
                    )
                    return url
            elif (
                message.attachments
                and message.attachments[0].width
                and message.attachments[0].height
            ):
                url = message.attachments[0].proxy_url
                url = url.replace("cdn.discordapp.com", "media.discordapp.net")
                return url

        if (
            ctx.message.attachments
            and ctx.message.attachments[0].width
            and ctx.message.attachments[0].height
        ):
            return ctx.message.attachments[0].proxy_url.replace(
                "cdn.discordapp.com", "media.discordapp.net"
            )

        if thing is None and avatar:
            url = str(ctx.author.avatar_url_as(static_format="png"))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            url = str(thing.url_as())
        elif isinstance(thing, (discord.Member, discord.User)):
            url = str(thing.avatar_url_as(static_format="png"))
        else:
            thing = str(thing).strip("<>")
            if self.bot.url_regex.match(thing):
                url = thing
            else:
                url = await emoji_to_url(thing)
                if url == thing:
                    raise commands.CommandError("Invalid url")
        if not avatar:
            return None
        if check:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    raise commands.CommandError("Invalid Picture")
        url = url.replace("cdn.discordapp.com", "media.discordapp.net")
        return url

    async def get_url(self, ctx: AnimeContext, thing, **kwargs):
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        if ctx.message.reference:
            message = ctx.message.reference.resolved
            if message.embeds and message.embeds[0].type == "image":
                url = message.embeds[0].thumbnail.proxy_url
                url = url.replace("cdn.discordapp.com", "media.discordapp.net")
                return url
            elif message.embeds and message.embeds[0].type == "rich":
                if message.embeds[0].image.proxy_url:
                    url = message.embeds[0].image.proxy_url
                    url = url.replace(
                        "cdn.discordapp.com", "media.discordapp.net"
                    )
                    return url
                elif message.embeds[0].thumbnail.proxy_url:
                    url = message.embeds[0].thumbnail.proxy_url
                    url = url.replace(
                        "cdn.discordapp.com", "media.discordapp.net"
                    )
                    return url
            elif (
                message.attachments
                and message.attachments[0].width
                and message.attachments[0].height
            ):
                url = message.attachments[0].proxy_url
                url = url.replace("cdn.discordapp.com", "media.discordapp.net")
                return url

        if (
            ctx.message.attachments
            and ctx.message.attachments[0].width
            and ctx.message.attachments[0].height
        ):
            return ctx.message.attachments[0].proxy_url.replace(
                "cdn.discordapp.com", "media.discordapp.net"
            )

        if thing is None and avatar:
            url = str(ctx.author.avatar_url_as(format="png"))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            url = str(thing.url)
        elif isinstance(thing, (discord.Member, discord.User)):
            url = str(thing.avatar_url_as(format="png"))
        else:
            thing = str(thing).strip("<>")
            if self.bot.url_regex.match(thing):
                url = thing
            else:
                url = await emoji_to_url(thing)
                if url == thing:
                    raise commands.CommandError("Invalid url")
        if not avatar:
            return None
        if check:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    raise commands.CommandError("Invalid Picture")
        #                 with Image.open(BytesIO(await resp.read())) as img:
        #                     if img.width >= 3000 or img.height >= 3000:
        #                         raise commands.CommandError("Image too large")

        url = url.replace("cdn.discordapp.com", "media.discordapp.net")
        return url

    async def bot_cdn(self, url):
        async with self.bot_cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                content = resp.content_type
                if (
                    "image" not in resp.content_type
                    and "webm" not in resp.content_type
                ):
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://theanimebot.is-ne.at/upload",
                    data={"image": await resp.read(), "noembed": "True"},
                ) as resp:
                    if resp.status != 200:
                        return "something went wrong"
                    js = await resp.json()
                    return f"<{js.get('url')}>"

    async def cdn_(self, url):
        async with self.cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                if "image" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://idevision.net/api/cdn",
                    headers={
                        "Authorization": config.idevision,
                        "File-Name": ree.split(str(resp.url).split("/")[-1])[
                            0
                        ],
                    },
                    data=resp.content,
                ) as resp:
                    return (await resp.json())["url"]

    async def ocr_(self, url):
        async with self.ocr_ratelimiter:
            async with self.bot.session.get(url) as resp:
                if "image" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.get(
                    f"https://idevision.net/api/public/ocr?filetype={resp.content_type[1]}",
                    headers={"Authorization": config.idevision},
                    data=resp.content,
                ) as resp:
                    return (await resp.json())["data"]
    
    def resize(self, image: BytesIO) -> BytesIO:
        with Image.open(image) as img:
            resized = img.resize((300, 300))
            b = BytesIO()
            resized.save(b, img.format)
            b.seek(0)
            resized.close()
            del resized
            return b

    def run_polaroid(self, image1, method, *args, **kwargs):
        # image1 = self.resize(BytesIO(image1))
        with Image.open(BytesIO(image1)) as img:
            if (
                img.format == "GIF"
                and img.n_frames < 200
                and img.width <= 3000
                and img.height <= 3000
            ):
                to_process = []
                to_make_gif = []
                for im in ImageSequence.Iterator(img):
                    b = BytesIO()
                    im_ = im.resize((300, 300))
                    im_.save(b, "PNG")
                    b.seek(0)
                    to_process.append(b)
                for i in to_process:
                    p_image = polaroid.Image(i.read())
                    method1 = getattr(p_image, method)
                    method1(*args, **kwargs)
                    b = BytesIO(p_image.save_bytes("png"))
                    to_make_gif.append(Image.open(b))
                    b.flush()
                    del p_image
                final = BytesIO()
                to_make_gif[0].save(
                    final,
                    format="GIF",
                    append_images=to_make_gif[1:],
                    save_all=True,
                    duration=img.info["duration"],
                    loop=0,
                )
                for i in to_process:
                    i.flush()
                    del i
                for i in to_make_gif:
                    i.close()
                    del i
                final.seek(0)
                return discord.File(final, filename=f"{method}.gif")

        image1 = self.resize(BytesIO(image1))
        im = polaroid.Image(image1.read())
        method1 = getattr(im, method)
        method1(*args, **kwargs)
        b = BytesIO(im.save_bytes("png"))
        del im
        return discord.File(b, filename=f"{method}.png")

    async def polaroid_(self, image, method, *args, **kwargs):
        async with self.bot.session.get(image) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(
            self.run_polaroid, image1, method, *args, **kwargs
        )
        result = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        return result

    @staticmethod
    def circle__(background_color, circle_color):
        frames = []
        mid = 100
        for i in range(500):
            with Image.new("RGB", (200, 200), background_color) as img:
                imgr = ImageDraw.Draw(img)
                imgr.ellipse(
                    (100 - i * 20, 100 - i * 20, 100 + i * 20, 100 + i * 20),
                    fill=circle_color,
                )
                fobj = BytesIO()
                img.save(fobj, "GIF")
                img = Image.open(fobj)
                frames.append(img)
                fobj.flush()
                del fobj
        igif = BytesIO()
        frames[0].save(
            igif,
            format="GIF",
            append_images=frames[1:],
            save_all=True,
            duration=3,
            loop=0,
        )
        igif.seek(0)
        for i in frames:
            i.close()
            del i
        return igif

    def process_gif(self, image, function, *args):
        with Image.open(BytesIO(image)) as img:
            if (
                img.format == "GIF"
                and img.n_frames < 200
                and img.width <= 3000
                and img.height <= 3000
            ):
                to_make_gif = []
                for im in ImageSequence.Iterator(img):
                    im_ = im.resize((300, 300))
                    im_ = im_.convert("RGB")
                    im_final = function(im_, *args)
                    to_make_gif.append(im_final)
                final = BytesIO()
                to_make_gif[0].save(
                    final,
                    format="GIF",
                    append_images=to_make_gif[1:],
                    save_all=True,
                    disposal=2,
                    duration=img.info["duration"],
                    loop=0,
                )
                for i in to_make_gif:
                    i.close()
                    del i
                final.seek(0)
                return final, "gif"
        image = self.resize(BytesIO(image))
        with Image.open(image) as img_:
            format_ = img_.format
            img_ = img_.convert("RGB")
            img = function(img_, *args)
            b = BytesIO()
            img.save(b, "PNG")
            b.seek(0)
            return b, "png"


    async def grayscale_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.grayscale)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_grayscale.{format_}")
        return result


    async def posterize_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.posterize, 3)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_posterize.{format_}")
        return result


    async def solarize_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        result, format_ = await self.bot.loop.run_in_executor(e, self.process_gif, image1, ImageOps.solarize)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_solarize.{format_}")
        return result

    async def circle_(self, background_color, circle_color):
        e = ThreadPoolExecutor(max_workers=5)
        result = await self.bot.loop.run_in_executor(e, self.circle__, background_color, circle_color)
        e.shutdown()
        return result

    @asyncexe()
    def qr_enc(self, thing):
        q = qrcode.make(thing, image_factory=PymagingImage)
        pic = BytesIO()
        q.save(pic)
        pic.seek(0)
        return pic

    @asyncexe()
    def qr_dec(self, bytes_):
        with Image.open(bytes_) as img:
            return decode(img)[0].data.decode("utf-8")

    @commands.group(invoke_without_command=True)
    async def qr(self, ctx, *, thing):
        try:
            pic = await self.qr_enc(thing)
        except:
            return await ctx.send("Too big big")
        await ctx.send(file=discord.File(pic, "qrcode.png"))

    @qr.command(name="decode")
    async def qr_decode(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        url = await self.get_url(ctx, thing)
        async with self.bot.session.get(url) as resp:
            bytes_ = BytesIO(await resp.read())
            try:
                data = await self.qr_dec(bytes_)
            except:
                return await ctx.send("Can't regonize qrcode")
            embed = discord.Embed(color=self.bot.color, description=data)
            await ctx.send(embed=embed)

    @commands.command()
    async def caption(
        self,
        ctx: AnimeContext,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        url = await self.get_url(ctx, thing)
        data = {"Content": url, "Type": "CaptionRequest"}
        async with self.bot.session.post(
            "https://captionbot.azurewebsites.net/api/messages",
            headers={"Content-Type": "application/json; charset=utf-8"},
            data=ujson.dumps(data),
        ) as resp:
            text = await resp.text()
            embed = discord.Embed(color=self.bot.color, title=text)
            embed.set_image(url="attachment://caption.png")
            async with self.bot.session.get(url) as resp:
                bytes_ = BytesIO(await resp.read())
            await ctx.send(
                embed=embed, file=discord.File(bytes_, "caption.png")
            )

    @commands.command()
    async def botcdn(
        self,
        ctx: AnimeContext,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        url = await self.get_url(ctx, thing)
        await ctx.send(f"{await self.bot_cdn(url)}")

    @commands.command()
    async def cdn(
        self,
        ctx: AnimeContext,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        url = await self.get_url(ctx, thing)
        await ctx.send(f"<{await self.cdn_(url)}>")

    @commands.command()
    async def ocr(
        self,
        ctx: AnimeContext,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        url = await self.get_url(ctx, thing)
        await ctx.send(f"```\n{await self.ocr_(url)}\n```")

    @commands.command()
    async def aww(self, ctx):
        async with self.bot.session.get(
            "https://api.ksoft.si/images/random-aww",
            headers={"Authorization": authorizationthing},
        ) as resp:
            res = await resp.json()
            link = res.get("image_url")
            async with self.bot.session.get(link) as resp:
                buffer = BytesIO(await resp.read())
        await ctx.send(file=discord.File(buffer, "aww.png"))

    @commands.command()
    async def womancat(
        self,
        ctx: AnimeContext,
        woman: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
        cat: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
    ):
        url = await self.get_url(ctx, woman)
        url1 = await self.get_url(ctx, cat)
        pic = await self.bot.vacefron_api.woman_yelling_at_cat(
            woman=url, cat=url1
        )
        await ctx.send(
            file=discord.File(
                await pic.read(), filename=f"woman_yelling_at_cat.png"
            )
        )

    @commands.command()
    async def circle(
        self, ctx: AnimeContext, background_color="white", circle_color="blue"
    ):
        igif = await self.circle_(background_color, circle_color)
        await ctx.send(file=discord.File(igif, "circle.gif"))

    @commands.command()
    async def npc(
        self,
        ctx,
        text1: str = "You gotta enter something",
        text2: str = "yeye",
    ):
        pic = await self.bot.vacefron_api.npc(text1, text2)
        await ctx.send(
            file=discord.File(
                await pic.read(), filename=f"npc_{text1}_{text2}.png"
            )
        )

    @commands.command()
    async def amongus(
        self, ctx, name: str = "you", color: str = "red", imposter: bool = True
    ):
        pic = await self.bot.vacefron_api.ejected(name, color, imposter)
        await ctx.send(
            file=discord.File(
                await pic.read(),
                filename=f"among_us_{name}_{color}_{imposter}.png",
            )
        )

    @commands.command()
    async def randompicture(self, ctx: AnimeContext, *, seed: str = None):
        if seed:
            async with self.bot.session.get(
                f"https://picsum.photos/seed/{seed}/3840/2160"
            ) as resp:
                pic = BytesIO(await resp.read())
        else:
            async with self.bot.session.get(
                "https://picsum.photos/3840/2160"
            ) as resp:
                pic = BytesIO(await resp.read())
        await ctx.send(file=discord.File(pic, filename="randompicture.png"))

    @commands.command()
    async def dym(self, ctx: AnimeContext, up, bottom):
        """
        Google do you mean picture
        Usage: ovo dym \"anime bot is bad bot\" \"anime bot is good bot\"
        """
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.didyoumean(up, bottom)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def gradiant(self, ctx):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.colour_image_gradient()).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def amiajoke(
        self,
        ctx,
        thing: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
        level: float = 0.3,
    ):
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.amiajoke(url)).read(), "alex.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.group(invoke_without_command=True)
    async def supreme(
        self, ctx: AnimeContext, *, text: str = "enter something here"
    ):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.supreme(text=text)).read(), "alex.png"
        )
        await ctx.send(embed=embed, file=image)

    @supreme.command(name="dark")
    async def supreme_dark(
        self, ctx: AnimeContext, *, text: str = "enter something here"
    ):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.supreme(text=text, dark=True)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def archive(self, ctx: AnimeContext, *, text):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.achievement(text=text)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def pixelate(
        self,
        ctx,
        thing: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
        level: float = 0.3,
    ):
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.pixelate(url, level)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://pixelate.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="pixelate.png"),
                embed=embed,
            )

    @commands.command()
    async def swirl(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.swirl(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://swirl.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="swirl.gif"), embed=embed
            )

    @commands.command()
    async def sobel(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.sobel(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://sobel.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="sobel.png"), embed=embed
            )

    @commands.command()
    async def palette(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.palette(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://palette.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="palette.png"),
                embed=embed,
            )

    @commands.command()
    async def sort(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.sort(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://sort.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="sort.png"), embed=embed
            )

    @commands.command()
    async def cube(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.cube(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://cube.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="cube.png"), embed=embed
            )

    @commands.command()
    async def braille(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.braille(url)
            await ctx.send(image)

    @commands.command(aliases=["dot"])
    async def dots(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.dots(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://dots.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="dots.png"), embed=embed
            )

    @commands.command()
    async def threshold(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.threshold(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://threshold.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="threshold.png"),
                embed=embed,
            )

    @commands.command()
    async def spread(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.spread(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://spread.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="spread.gif"), embed=embed
            )

    @commands.command()
    async def jpeg(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.jpeg(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://jpeg.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="jpeg.gif"), embed=embed
            )

    @commands.command(aliases=["magik"])
    async def magic(
        self,
        ctx,
        thing: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
        level: float = 0.6,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.magic(url, level)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://magic.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="magic.gif"), embed=embed
            )

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.user)
    async def floor(
        self,
        ctx,
        thing: commands.Greedy[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ] = None,
    ):
        async with ctx.channel.typing():
            if not thing:
                url = await self.get_url(ctx, thing)
                image = await self.bot.zaneapi.floor(url)
                embed = discord.Embed(color=0x00FF6A).set_image(
                    url="attachment://floor.gif"
                )
                return await ctx.send(
                    file=discord.File(fp=image, filename="floor.gif"),
                    embed=embed,
                )

            if len(thing) > 10:
                return await ctx.send("the max is 10")
            for i in thing:
                url = await self.get_url(ctx, i)
                image = await self.bot.zaneapi.floor(url)
                embed = discord.Embed(color=0x00FF6A).set_image(
                    url="attachment://floor.gif"
                )
                await ctx.send(
                    file=discord.File(fp=image, filename="floor.gif"),
                    embed=embed,
                )

    @commands.command()
    async def noise(self, ctx):
        stat_ = await self.image(
            ctx,
            await ctx.author.avatar_url_as(format="png").read(),
            "add_noise_rand",
        )

    @commands.command(aliases=["wtp"])
    async def pokemon(self, ctx):
        await ctx.trigger_typing()
        wtp = await self.bot.dag.wtp()
        tried = 3
        if ctx.author.id == 590323594744168494:
            await ctx.author.send(wtp.name)
        embed = discord.Embed(color=0x2ECC71)
        ability = "".join(wtp.abilities)
        embed.set_author(name=f"{ctx.author} has {tried} tries")
        embed.add_field(name="pokemon's ability", value=ability)
        embed.set_image(url=wtp.question)
        message = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author

        for x in range(3):
            msg = await self.bot.wait_for("message", check=check)
            tried -= 1
            embed = discord.Embed(color=0x2ECC71)
            ability = "".join(wtp.abilities)
            embed.set_author(name=f"{ctx.author} has {tried} tries")
            embed.add_field(name="Pokemon's Ability", value=ability)
            embed.set_image(url=wtp.question)
            await message.edit(embed=embed)
            if msg.content.lower() == wtp.name.lower():
                embed = discord.Embed(color=0x2ECC71)
                embed.set_author(name=f"{ctx.author} won")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                await message.delete()
                tried = 3
                return
            if tried == 0:
                await message.delete()
                embed = discord.Embed(color=0x2ECC71)
                embed.set_author(name=f"{ctx.author} lost")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                tried = 3
                return

    @commands.command()
    async def captcha(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
        *,
        text="enter something here",
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            text1 = text
        img = await self.bot.dag.image_process(
            ImageFeatures.captcha(), url, text=text1
        )
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def solarize(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.solarize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def invert(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "invert"))

    @commands.command()
    async def oil(
        self,
        ctx,
        thing: typing.Optional[
            typing.Union[
                discord.Member,
                discord.User,
                discord.PartialEmoji,
                discord.Emoji,
                str,
            ]
        ],
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "oil", 3, 10))

    @commands.command()
    async def rainbow(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "apply_gradient"))

    @commands.command()
    async def awareness(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.magik(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def night(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.night(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def paint(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.paint(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def polaroid(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.polaroid(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def sepia(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.sepia(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def posterize(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.posterize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def grayscale(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            file = await self.grayscale_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def ascii(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.ascii(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def deepfry(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.deepfry(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def trash(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.trash(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def gay(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.gay(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def shatter(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.shatter(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def delete(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.delete(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def fedora(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.fedora(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def jail(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.jail(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def sith(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.sith(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def bad(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.bad(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def obama(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.obama(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def hitler(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.hitler(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command(aliases=["evil"])
    async def satan(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.satan(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def angel(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.angel(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def rgb(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.rgb(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def blur(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.blur(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def hog(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.hog(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def triangle(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.triangle(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def wasted(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.wasted(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def america(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.america(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def triggered(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.triggered(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def wanted(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.wanted(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def colors(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.colors(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def pixel(
        self,
        ctx,
        thing: typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ] = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.pixel(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)


def setup(bot):
    bot.add_cog(pictures(bot))
