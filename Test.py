import yt_dlp
import asyncio
import requests
from bs4 import BeautifulSoup
import re



# ytdl_format_options = {
#     'format': 'bestaudio/best',
#     'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
#     'restrictfilenames': True,
#     'noplaylist': True,
#     'nocheckcertificate': True,
#     'ignoreerrors': False,
#     'logtostderr': False,
#     'quiet': True,
#     'no_warnings': True,
#     'default_search': 'auto',
#     'source_address': '0.0.0.0'
# }
#
#
# ffmpeg_options = {
#     'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
#     'options': '-vn'
# }
#
#
# ytdl = yt_dlp.YoutubeDL(ytdl_format_options)



# async def get_related_video_url(video_url):
#     """
#     현재 곡의 추천 영상 URL을 가져오는 함수
#     """
#     loop = asyncio.get_event_loop()
#     data = await loop.run_in_executor(None, lambda: ytdl.extract_info(video_url, download=False))
#
#     print(f"🔍 데이터 확인: {data.keys()}")  # Debugging 용도
#     print(f"🔍 관련 영상 리스트: {data.get('related_videos')}")
#
#     # 1️⃣ 'related_videos'가 있는 경우
#     if 'related_videos' in data and data['related_videos']:
#         for related in data['related_videos']:
#             if 'id' in related:
#                 return f"https://www.youtube.com/watch?v={related['id']}"
#
#     # 2️⃣ 'related_videos'가 없는 경우, 제목 기반으로 검색
#     return await search_related_video(data.get('title'))
#
#
# async def search_related_video(title):
#     """
#     현재 재생 중인 곡의 제목을 기반으로 검색하여 유사한 곡 추천
#     """
#     search_query = f"{title} 관련 음악"
#     search_url = f"ytsearch10:{search_query}"  # yt_dlp 검색 기능 활용
#
#     loop = asyncio.get_event_loop()
#     search_data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search_url, download=False))
#
#     print(search_data['entries'])
#
#
#     if 'entries' in search_data and search_data['entries']:
#         return search_data['entries'][0]['webpage_url']  # 가장 첫 번째 검색 결과 반환
#
#     return None  # 검색 결과가 없을 경우 None 반환



async def testMain():
    # YOUTUBE_VIDEO_URL = "https://www.youtube.com/watch?v=jzxJkfcYCDs"
    # related_video_url = await get_related_video_url(YOUTUBE_VIDEO_URL)
    # print(related_video_url)
    pass


if __name__ == "__main__":
    asyncio.run(testMain())
