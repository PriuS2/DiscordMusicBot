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
    'source_address': '0.0.0.0',
    'extract_flat': True,  # Added to prevent detailed extraction
    'force_generic_extractor': True  # Added to use generic extractor
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

music_queue = []
queue_info = []
current_player = None
auto_added_count = 0  # 자동 추가된 곡 수를 추적하는 변수
max_auto_add = 10  # 최대 자동 추가 곡 수

# 연관곡을 가져오는 새로운 함수 추가
async def get_related_video(video_id):
    try:
        # 현재 곡의 ID로 연관 비디오 검색
        search_url = f"https://www.youtube.com/watch?v={video_id}"
        loop = asyncio.get_event_loop()

        # 연관 비디오 정보 추출 설정
        related_options = ytdl_format_options.copy()
        related_options.update({
            'skip_download': True,
            'extract_flat': True,
            'noplaylist': False,  # 관련 동영상 가져오기 위해 필요
        })

        with yt_dlp.YoutubeDL(related_options) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(search_url, download=False))

            # 추천 비디오 목록 가져오기
            if 'entries' in info.get('related_videos', {}):
                related = info.get('related_videos', [])

                # 첫 번째 연관 비디오 URL 생성
                if related and len(related) > 0:
                    for video in related:
                        if video.get('id'):
                            return f"https://www.youtube.com/watch?v={video['id']}"
    except Exception as e:
        print(f"Error getting related video: {str(e)}")

    return None

# play_next 함수 수정
async def play_next(voice_client):
    global current_player, auto_added_count
    await asyncio.sleep(1)  # 안정성을 위해 추가

    try:
        if music_queue:
            next_source = music_queue.pop(0)
            queue_info.pop(0)
            current_player = next_source
            voice_client.play(next_source, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(voice_client), bot.loop))
        else:
            # 대기열이 비었고 자동 추가 횟수가 최대치 미만일 때
            if current_player and auto_added_count < max_auto_add:
                # 현재 재생 중이던 곡의 ID 추출
                video_id = None
                if current_player and current_player.url:
                    # URL에서 동영상 ID 추출
                    import re
                    match = re.search(r'(?:youtube\.com\/watch\?v=|youtu.be\/)([a-zA-Z0-9_-]+)', current_player.url)
                    if match:
                        video_id = match.group(1)

                if video_id:
                    related_url = await get_related_video(video_id)
                    if related_url:
                        try:
                            # 연관곡 추가
                            player = await YTDLSource.from_url(related_url, loop=bot.loop, stream=True)
                            music_queue.append(player)
                            queue_info.append((player.title, "자동 추천", player.url))
                            auto_added_count += 1

                            # 추가 후 바로 재생
                            await play_next(voice_client)

                            # 서버의 모든 채널에서 알림 전송 (텍스트 채널 찾기)
                            if voice_client and voice_client.guild:
                                for channel in voice_client.guild.text_channels:
                                    try:
                                        await channel.send(f'🎵 자동 추천 곡 추가: [{player.title}](<{player.url}>) (남은 자동 추천: {max_auto_add - auto_added_count})')
                                        break  # 메시지를 보냈으면 루프 종료
                                    except:
                                        continue

                            return
                        except Exception as e:
                            print(f"Error adding related song: {str(e)}")

            # 자동 추가 실패 또는 최대치 도달
            current_player = None
            auto_added_count = 0  # 초기화
            await disconnect_if_idle(voice_client)
    except Exception as e:
        print(f"Error in play_next: {str(e)}")
        await disconnect_if_idle(voice_client)


async def disconnect_if_idle(voice_client):
    await asyncio.sleep(5)  # 5초 대기 후 확인

    try:
        doDisconnect = False
        if voice_client and voice_client.channel:
            if len(voice_client.channel.members) == 1:
                doDisconnect = True
            if not music_queue or len(music_queue) == 0:
                doDisconnect = True

            if doDisconnect:
                await voice_client.disconnect()
    except Exception as e:
        print(f"Error in disconnect_if_idle: {str(e)}")


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            # URL인지 검색어인지 확인
            import re
            is_url = bool(re.match(r'https?://', url))
    
            if not is_url:
                # 검색어인 경우 먼저 검색 수행
                info_ytdl = yt_dlp.YoutubeDL({
                    'format': 'bestaudio/best',
                    'default_search': 'ytsearch',
                    'noplaylist': True,
                    'quiet': True,
                    'extract_flat': False  # 상세 정보 추출을 위해 False로 설정
                })
    
                info = await loop.run_in_executor(None, lambda: info_ytdl.extract_info(f"ytsearch:{url}", download=False))
                if 'entries' in info:
                    # 검색 결과에서 첫 번째 항목의 URL 추출
                    if not info['entries']:
                        raise ValueError("검색 결과가 없습니다.")
                    # 실제 URL을 사용하여 다시 정보 추출
                    actual_url = info['entries'][0]['webpage_url']
                    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(actual_url, download=not stream))
                else:
                    raise ValueError("검색 결과를 처리할 수 없습니다.")
            else:
                # URL인 경우 그대로 처리
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
    
                if 'entries' in data:
                    # 플레이리스트인 경우 첫 번째 항목 사용
                    data = data['entries'][0]
    
            if not data.get('url'):
                raise ValueError("오디오 URL을 추출할 수 없습니다.")
    
            filename = data['url'] if stream else ytdl.prepare_filename(data)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        except Exception as e:
            print(f"Error in from_url: {str(e)}")
            raise e


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=member.guild)

        if voice_client and voice_client.channel:
            await asyncio.sleep(5)  # 5초 대기 후 확인
            if len(voice_client.channel.members) == 1:
                await voice_client.disconnect()
    except Exception as e:
        print(f"Error in voice_state_update: {str(e)}")


# 재생 명령어에서 유저가 곡을 추가할 때 자동 추가 카운트 초기화 추가
@bot.tree.command(name="재생", description="유튜브 음악을 URL 또는 검색어로 재생합니다.")
@app_commands.describe(search="재생할 유튜브 URL 또는 검색어")
async def play(interaction: discord.Interaction, search: str):
    try:
        global current_player, auto_added_count
        auto_added_count = 0  # 유저가 직접 곡을 추가하면 자동 추가 카운트 초기화

        # 이하 기존 코드 동일
        if not interaction.user.voice:
            await interaction.response.send_message("먼저 음성 채널에 입장해야 합니다.", ephemeral=True)
            return

        await interaction.response.defer()

        channel = interaction.user.voice.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

        if not voice_client:
            voice_client = await channel.connect(self_deaf=True)

        try:
            player = await YTDLSource.from_url(search, loop=bot.loop, stream=True)
        except Exception as e:
            await interaction.followup.send(f"음악을 재생할 수 없습니다: {str(e)}")
            return

        thisUrl = player.url

        music_queue.append(player)
        queue_info.append((player.title, interaction.user.name, thisUrl))

        await interaction.followup.send(f'대기열 추가: [{player.title}](<{thisUrl}>) (신청자: {interaction.user.name})')

        if not voice_client.is_playing():
            await play_next(voice_client)
    except Exception as e:
        await interaction.followup.send(f"오류가 발생했습니다: {str(e)}")


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


# 멈춤 명령어 수정 - 자동 추가 카운트 초기화 추가
@bot.tree.command(name="멈춰", description="음악을 멈추고 봇을 퇴장시킵니다.")
async def stop(interaction: discord.Interaction):
    global current_player, auto_added_count
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message("음악을 멈추고 봇이 퇴장했습니다.")
        current_player = None
        music_queue.clear()
        queue_info.clear()
        auto_added_count = 0  # 자동 추가 카운트 초기화
    else:
        await interaction.response.send_message("봇이 음성 채널에 있지 않습니다.")


@bot.tree.command(name="도움말", description="봇의 모든 명령어를 안내합니다.")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**🎵 음악 봇 명령어 안내 🎵**\n\n"
        "`/재생 <유튜브 URL>` - YouTube 음악을 재생합니다.\n"
        "`/대기열` - 현재 대기열을 확인합니다.\n"
        "`/스킵` - 현재 재생 중인 음악을 스킵합니다.\n"
        "`/멈춰` - 음악을 멈추고 봇을 퇴장시킵니다.\n"
        "`/현재곡` - 현재 재생 중인 곡의 정보를 확인합니다.\n"
        "`/도움말` - 사용 가능한 모든 명령어를 안내합니다.\n"
    )
    await interaction.response.send_message(help_text)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')


bot.run(DISCORD_TOKEN)