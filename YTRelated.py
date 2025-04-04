
import requests
from bs4 import BeautifulSoup
import re
import json

def get_related_video(youtube_url, debug=False):
    """
    YouTube URL에서 연관 영상 1개의 URL을 추출합니다.
    
    Args:
        youtube_url (str): YouTube 영상 URL
        debug (bool, optional): 디버그 모드 활성화 여부. 기본값은 False.
        
    Returns:
        str: 연관 영상의 URL 또는 에러 메시지
    """
    try:
        # 유효한 YouTube URL인지 확인
        if 'youtube.com/watch' not in youtube_url and 'youtu.be/' not in youtube_url:
            return "유효한 YouTube URL이 아닙니다."

        # HTTP 요청 헤더 설정 (YouTube는 User-Agent를 확인함)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # YouTube 페이지 요청
        # youtu.be 형식 URL 처리
        if 'youtu.be/' in youtube_url:
            video_id = youtube_url.split('youtu.be/')[1].split('?')[0]
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        response = requests.get(youtube_url, headers=headers)

        if debug:
            print(f"상태 코드: {response.status_code}")
            print(f"응답 헤더: {response.headers}")

        if response.status_code != 200:
            return f"요청 실패: 상태 코드 {response.status_code}"

        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')

        # 방법 1: JSON 데이터에서 추출 (더 안정적)
        script_tags = soup.find_all('script')

        for script in script_tags:
            if script.string and 'var ytInitialData' in script.string:
                # JSON 데이터 추출
                try:
                    json_str = script.string.split('var ytInitialData = ')[1].split(';</script>')[0]
                    # 때로는 JSON 문자열 끝에 세미콜론이 있을 수 있음
                    if json_str.endswith(';'):
                        json_str = json_str[:-1]
                    data = json.loads(json_str)
                except Exception as e:
                    continue  # 이 스크립트 태그 건너뛰기

                # 연관 동영상 정보 추출 시도
                try:
                    secondary_contents = data['contents']['twoColumnWatchNextResults']['secondaryResults']['secondaryResults']['results']
                    urls = []
                    for item in secondary_contents:
                        if 'compactVideoRenderer' in item:
                            video_id = item['compactVideoRenderer']['videoId']
                            related_url = f"https://www.youtube.com/watch?v={video_id}"
                            length_text = item['compactVideoRenderer']['lengthText']['simpleText']
                            if debug:
                                video_title = item['compactVideoRenderer']['title']['simpleText']
                                print('-'*20)
                                print(f"raw : {item['compactVideoRenderer']}")
                                print(f"제목: {video_title}, 길이: {length_text}, url: {related_url}")
                                
                            # 시간 문자열을 초로 변환
                            time_parts = length_text.split(':')
                            total_seconds = 0
                            if len(time_parts) == 3:  # HH:MM:SS 형식
                                total_seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
                            elif len(time_parts) == 2:  # MM:SS 형식
                                total_seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                            else:  # SS 형식 (1분 미만)
                                total_seconds = int(time_parts[0])

                            if debug:
                                print(f"영상 길이(초): {total_seconds}")
                            
                            if total_seconds < 335:
                                urls.append(related_url)
                    
                    return urls[0]
                except KeyError:
                    pass  # JSON 구조가 다른 경우 다음 방법 시도

        # 방법 2: HTML에서 직접 추출
        related_videos = soup.select('a.yt-simple-endpoint.style-scope.ytd-compact-video-renderer')

        if related_videos:
            for video in related_videos:
                href = video.get('href', '')
                if '/watch?v=' in href:
                    return f"https://www.youtube.com{href}"

        # 방법 3: 정규식으로 비디오 ID 추출
        video_ids = re.findall(r'"videoId":"([^"]+)"', response.text)

        if video_ids:
            # 현재 비디오 ID 확인
            current_id = None
            if 'v=' in youtube_url:
                current_id = youtube_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in youtube_url:
                current_id = youtube_url.split('youtu.be/')[1].split('?')[0]

            # 현재 비디오와 다른 첫 번째 ID 반환
            for vid in video_ids:
                if vid != current_id and len(vid) == 11:  # 유효한 YouTube 비디오 ID는 11자
                    return f"https://www.youtube.com/watch?v={vid}"

        # 방법 4: 다른 패턴 시도
        alternative_pattern = r'href="/watch\?v=([^"&]+)"'
        video_links = re.findall(alternative_pattern, response.text)

        if video_links:
            # 현재 비디오 ID 확인
            current_id = None
            if 'v=' in youtube_url:
                current_id = youtube_url.split('v=')[1].split('&')[0]

            # 현재 비디오와 다른 첫 번째 ID 반환
            for vid in video_links:
                if vid != current_id and len(vid) == 11:
                    return f"https://www.youtube.com/watch?v={vid}"

        return "연관 영상을 찾을 수 없습니다."

    except Exception as e:
        return f"오류 발생: {str(e)}"

# 사용 예시
if __name__ == "__main__":
    url = input("YouTube URL을 입력하세요: ")
    print(f"\nYouTube URL: {url}")
    related_video_url = get_related_video(url, debug=True)
    print(f"연관 영상 URL: {related_video_url}")