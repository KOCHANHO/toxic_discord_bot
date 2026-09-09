import os
import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime, timezone, timedelta

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BOARD_URL = "https://inno.hongik.ac.kr/EmpInfo/Part/B/partb0020s.aspx?mc=0638"
LAST_ID_FILE = "last_post_id.txt"
LAST_DAILY_FILE = "last_daily_check.txt"

# 감지할 키워드 설정 (모든 글의 알림을 원하면 [] 빈 리스트로 변경)
TARGET_KEYWORDS = ["TOEIC", "토익"]


def get_saved_data(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_data(filename, content):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(content))


def send_discord_message(title, description, url=None, color=3447003):
    if not DISCORD_WEBHOOK_URL:
        print("[에러] DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return

    embed = {
        "title": title,
        "description": description,
        "color": color
    }
    if url:
        embed["url"] = url

    payload = {
        "username": "홍익대 토익 알바 알림이",
        "embeds": [embed]
    }
    
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code == 204:
            print(f"[성공] 디스코드 메시지 전송 완료: {title}")
    except Exception as e:
        print(f"[에러] 디스코드 전송 실패: {e}")


def check_daily_status():
    """매일 아침 9시(KST 기준)에 1회 생존 알림 전송"""
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    today_str = now.strftime("%Y-%m-%d")
    
    last_daily_date = get_saved_data(LAST_DAILY_FILE)
    
    # 아침 9시 대이고 오늘 아직 생존 신고를 안 했다면 발송
    if now.hour == 9 and last_daily_date != today_str:
        send_discord_message(
            title="🟢 [동작 확인] 봇이 정상 작동 중입니다",
            description=f"**현재 날짜:** {today_str}\n홍익대 토익 아르바이트 게시판을 모니터링하고 있습니다.",
            color=5763719  # 초록색
        )
        save_data(LAST_DAILY_FILE, today_str)


def check_new_post():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(BOARD_URL, headers=headers, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        a_tags = soup.find_all('a')
        
        for a in a_tags:
            href = a.get('href', '')
            title = a.text.strip()
            
            if not title or title in ['처음', '이전', '다음', '끝', '검색', '글쓰기', '목록']:
                continue
            
            if 'partb' in href.lower() or 'seq' in href.lower() or 'view' in href.lower():
                # 키워드 필터링 (TARGET_KEYWORDS에 있는 단어가 포함되어 있는지 확인)
                if TARGET_KEYWORDS:
                    if not any(kw.lower() in title.lower() for kw in TARGET_KEYWORDS):
                        continue
                
                # URL 주소 정제
                if href.startswith('/'):
                    link = f"https://inno.hongik.ac.kr{href}"
                elif href.startswith('http'):
                    link = href
                else:
                    link = f"https://inno.hongik.ac.kr/EmpInfo/Part/B/{href}"
                
                post_id = href.split('Seq=')[1].split('&')[0] if 'Seq=' in href else title
                
                return {'id': post_id, 'title': title, 'link': link}

        return None
    except Exception as e:
        print(f"[에러] 크롤링 실패: {e}")
        return None


def main():
    # 1. 매일 아침 동작 확인 체크
    check_daily_status()
    
    # 2. 새로운 토익 알바 공고 감지
    latest_post = check_new_post()
    
    if latest_post:
        saved_id = get_saved_data(LAST_ID_FILE)
        
        if latest_post['id'] != saved_id:
            print(f"✨ target 글 발견: {latest_post['title']}")
            send_discord_message(
                title="📢 [토익 알바] 새로운 공고가 등록되었습니다!",
                description=f"**제목:** {latest_post['title']}",
                url=latest_post['link'],
                color=3447003
            )
            save_data(LAST_ID_FILE, latest_post['id'])
        else:
            print("최신 토익 공고에 변화가 없습니다.")

if __name__ == "__main__":
    main()
