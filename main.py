import os
import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# GitHub Secrets에서 웹훅 주소를 안전하게 불러옵니다.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
BOARD_URL = "https://inno.hongik.ac.kr/EmpInfo/Part/B/partb0020s.aspx?mc=0638"
LAST_ID_FILE = "last_post_id.txt"


def get_saved_last_id():
    if os.path.exists(LAST_ID_FILE):
        with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_last_id(post_id):
    with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(post_id))


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


def send_discord_notification(post):
    if not DISCORD_WEBHOOK_URL:
        print("[에러] DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")
        return

    payload = {
        "username": "홍익대 알바 알림이",
        "embeds": [{
            "title": "📢 새 아르바이트 공고가 등록되었습니다!",
            "description": f"**제목:** {post['title']}",
            "url": post['link'],
            "color": 3447003
        }]
    }
    
    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if res.status_code == 204:
            print(f"[성공] 디스코드 알림 발송 완료: {post['title']}")
    except Exception as e:
        print(f"[에러] 웹훅 전송 오류: {e}")


def main():
    latest_post = check_new_post()
    
    if latest_post:
        saved_id = get_saved_last_id()
        
        if latest_post['id'] != saved_id:
            print(f"✨ 새 글 발견: {latest_post['title']}")
            send_discord_notification(latest_post)
            save_last_id(latest_post['id'])
        else:
            print("새로운 게시글이 없습니다.")

if __name__ == "__main__":
    main()

