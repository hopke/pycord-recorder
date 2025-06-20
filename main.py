import discord
import pydub
import io
import json
import os
from dotenv import load_dotenv
import gc


load_dotenv()

bot = discord.Bot(intents=discord.Intents.default())
connections = {}

with open(('config.json'), 'r') as f:
    config = json.load(f)

@bot.event
async def on_ready():
    print("Bot is ready!")
    bot.voice_channel = bot.get_channel(config['verifyChannel'])
    bot.verify_logs = bot.get_channel(config['verifyLogs'])

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is bot.voice_channel:
        _count = 0
        for member in before.channel.members:
            if not member.bot:
                _count += 1
        if _count == 1:
            if config['guild'] in connections:
                vc = connections[config['guild']]
                del connections[config['guild']]
                vc.stop_recording()
        if _count < 1:
            await bot.voice_client.disconnect()
    if after.channel != bot.voice_channel:
        return
    if member.bot:
        return
    if after.channel == bot.voice_channel:
        count = 0
        for member in after.channel.members:
            if not member.bot:
                count += 1
        if count == 1:
            if isinstance(bot.voice_channel, discord.VoiceChannel):
                bot.voice_client = await bot.voice_channel.connect()
                connections.update({config['guild']: bot.voice_client})
        if count > 1:
            try:
                bot.voice_client.start_recording(
                    discord.sinks.MP3Sink(),
                    once_done,
                    bot.voice_channel,
                    sync_start=True
                )
            except Exception:
                pass

async def once_done(sink: discord.sinks, channel: discord.TextChannel):
    mention_strs = []
    audio_segs: list[pydub.AudioSegment] = []
    log = bot.get_channel(config['verifyLogs'])

    longest = pydub.AudioSegment.empty()

    for user_id, audio in sink.audio_data.items():
        mention_strs.append(f"<@{user_id}>")

        seg = pydub.AudioSegment.from_file(audio.file, format="mp3")

        if len(seg) > len(longest):
            audio_segs.append(longest)
            longest = seg
        else:
            audio_segs.append(seg)

    for seg in audio_segs:
        longest = longest.overlay(seg)

    embed = discord.Embed(
        title="Аудіофайл",
        description=f"Записані: {', '.join(mention_strs)}",
        color=0x00ff00,
        timestamp=discord.utils.utcnow()
    )
    embed.author = discord.EmbedAuthor(name=bot.user.display_name, icon_url=bot.user.display_avatar)

    with io.BytesIO() as f:
        longest.export(f, format="mp3")
        await log.send(
            embed=embed,
            files=[discord.File(f, filename="Verify.mp3")]
        )

    del audio_segs
    del longest
    gc.collect()

bot.run(os.environ['TOKEN'])
