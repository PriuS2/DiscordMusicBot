import json
import os
import asyncio
from dotenv import load_dotenv
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', help_command=None, intents=intents)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

music_queue = []
queue_info = []
current_player = None

recommend_count = 0  # 연속 추천곡 카운터


async def play_next(voice_client):
    global current_player, recommend_count
    await asyncio.sleep(1)  # 안정성을 위해 추가

    if music_queue:
        next_source = music_queue.pop(0)
        queue_info.pop(0)
        current_player = next_source

        # 🔹 추천곡인지 확인 (추천곡의 신청자는 "추천곡"으로 저장됨)
        if queue_info and queue_info[0][1] == "추천곡":
            recommend_count += 1
        else:
            recommend_count = 0  # 사용자가 추가한 곡이 재생되면 초기화

        # 🔹 추천곡이 10곡 연속 재생되었으면 자동 퇴장
        if recommend_count >= 10:
            await voice_client.disconnect()
            current_player = None
            music_queue.clear()
            queue_info.clear()
            recommend_count = 0
            return  # 함수 종료

        voice_client.play(next_source, after=lambda e: bot.loop.create_task(play_next(voice_client)))
    else:
        # 🔹 대기열이 비었을 경우 현재곡 기준으로 추천곡 추가
        if current_player:
            related_url = await get_related_video_url(current_player.url)
            if related_url:
                await add_to_queue(voice_client, related_url, auto_added=True)
                return  # 새로운 곡이 추가되었으므로 종료

        current_player = None
        await disconnect_if_idle(voice_client)


async def get_related_video_url(video_url):
    """
    현재곡의 추천 영상 URL을 가져오는 함수
    """
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))

    if 'related_videos' in data:
        for related in data['related_videos']:
            if 'id' in related:
                return f"https://www.youtube.com/watch?v={related['id']}"

    return None


async def add_to_queue(voice_client, url, auto_added=False):
    """
    추천곡을 대기열에 추가하는 함수
    """
    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    music_queue.append(player)
    queue_info.append((player.title, "추천곡" if auto_added else "사용자", player.url))

    if auto_added:
        channel = voice_client.channel
        if channel:
            await channel.send(f'🔄 추천곡 추가: [{player.title}](<{player.url}>)')

    if not voice_client.is_playing():
        await play_next(voice_client)

async def disconnect_if_idle(voice_client):
    # print("disconnect_if_idle")
    await asyncio.sleep(5)  # 5초 대기 후 확인
    # print(f"music_queue : {music_queue}")
    # print(f"current_player : {current_player}")
    # print(f"voice_client.channel : {voice_client.channel}")
    # print(f"voice_client.channel.members : {voice_client.channel.members}")

    doDisconnect = False
    if voice_client.channel and len(voice_client.channel.members) == 1:
        doDisconnect = True
    if not music_queue or len(music_queue) == 0:
        doDisconnect = True

    if doDisconnect:
        await voice_client.disconnect()


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        #data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)




@bot.event
async def on_voice_state_update(member, before, after):
    voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

    if voice_client and voice_client.channel:
        await asyncio.sleep(5)  # 5초 대기 후 확인
        if len(voice_client.channel.members) == 1:
            await voice_client.disconnect()




@bot.tree.command(name="재생", description="유튜브 링크의 음악을 재생합니다.")
@app_commands.describe(url="재생할 유튜브 URL")
async def play(interaction: discord.Interaction, url: str):
    global current_player
    if not interaction.user.voice:
        await interaction.response.send_message("먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
        return

    await interaction.response.defer()

    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not voice_client:
        voice_client = await channel.connect(self_deaf=True)

    player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
    thisUrl = player.url

    music_queue.append(player)
    queue_info.append((player.title, interaction.user.name, thisUrl))

    await interaction.followup.send(f'대기열 추가: [{player.title}](<{thisUrl}>) (신청자: {interaction.user.name})')

    if not voice_client.is_playing():
        await play_next(voice_client)


@bot.tree.command(name="대기열", description="현재 대기열을 확인합니다.")
async def queue(interaction: discord.Interaction):
    if not music_queue:
        await interaction.response.send_message("현재 대기열이 비어 있습니다.")
    else:
        queue_list = "\n".join(
            [f'{idx + 1}. [{title}](<{urlstr}>) (신청자: {requester})' for idx, (title, requester, urlstr) in
             enumerate(queue_info)])
        await interaction.response.send_message(f'현재 대기열:\n{queue_list}')


@bot.tree.command(name="현재곡", description="현재 재생 중인 음악을 확인합니다.")
async def now_playing(interaction: discord.Interaction):
    global current_player

    if current_player:
        await interaction.response.send_message(
            f'현재 재생 중: [{current_player.title}](<{current_player.url}>)')
    else:
        await interaction.response.send_message("현재 재생 중인 곡이 없습니다.")


@bot.tree.command(name="스킵", description="현재 재생 중인 음악을 스킵합니다.")
async def skip(interaction: discord.Interaction):
    global current_player
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("현재 재생 중인 음악을 스킵했습니다.")
    else:
        await interaction.response.send_message("현재 재생 중인 음악이 없습니다.")


@bot.tree.command(name="멈춰", description="음악을 멈추고 봇을 퇴장시킵니다.")
async def stop(interaction: discord.Interaction):
    global current_player
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("음악을 멈추고 봇이 퇴장했습니다.")
        current_player = None
        music_queue.clear()
        queue_info.clear()
    else:
        await interaction.response.send_message("봇이 음성 채널에 있지 않습니다.")


@bot.tree.command(name="도움말", description="봇의 모든 명령어를 안내합니다.")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**🎵 음악 봇 명령어 안내 🎵**\n\n"
        "/재생 <유튜브 URL> - YouTube 음악을 재생합니다.\n"
        "/대기열 - 현재 대기열을 확인합니다.\n"
        "/스킵 - 현재 재생 중인 음악을 스킵합니다.\n"
        "/멈춰 - 음악을 멈추고 봇을 퇴장시킵니다.\n"
        "/현재곡 - 현재 재생 중인 곡의 정보를 확인합니다.\n"
        "/도움말 - 사용 가능한 모든 명령어를 안내합니다.\n"
    )
    await interaction.response.send_message(help_text)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')


bot.run(DISCORD_TOKEN)
