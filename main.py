from flask import Flask
from threading import Thread
import os

app = Flask('')


@app.route('/')
def home():
    return "봇이 작동 중입니다!"


def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = Thread(target=run)
    t.start()


# ============================================
# 📦 라이브러리 임포트
# ============================================
import discord
from discord.ext import commands, tasks
import aiohttp
import requests
import json
from bs4 import BeautifulSoup
import datetime as dt
import asyncio
import time
import hashlib
import csv
import io
import random

# ============================================
# 🔍 기본 설정
# ============================================
TYPE_LIST = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 9997, 9998, 9999]
MAP_DATA = {}
LAST_NOTICE_HASH = None  # 마지막 공지사항 해시값 저장

# ============================================
# 📦 아이템 관련 함수
# ============================================

def search_item_across_types(keyword):
    """안전한 아이템 검색"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        'Referer': 'https://classicbaram.gg/',
        'Connection': 'keep-alive'
    }
    base_url = 'https://www.classicbaram.gg/api/items/popular-with-prices?appVersion=2025_06_06&type={}&days=3'

    for type_id in TYPE_LIST:
        url = base_url.format(type_id)
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 503:
                print(f"⚠️ 서비스 일시 중단 (type={type_id}), 다른 타입 시도...")
                continue
            elif response.status_code != 200:
                print(f"❌ HTTP 오류 {response.status_code} (type={type_id})")
                continue

            data = response.json()
            for item in data:
                item_name = item['name']
                if keyword.replace(" ", "").lower() in item_name.replace(" ", "").lower():
                    return {
                        'name': item_name,
                        'price': f"{item['averagePrice']:,}전",
                        'image': item.get('iconUrl', '')
                    }
        except requests.exceptions.Timeout:
            print(f"⏰ 타임아웃 (type={type_id})")
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ 네트워크 오류 (type={type_id}): {e}")
            continue
        except Exception as e:
            print(f"❌ 알 수 없는 오류 (type={type_id}): {e}")
            continue

    print(f"❌ '{keyword}' 아이템을 찾을 수 없습니다.")
    return None


def get_top_items():
    url = 'https://www.classicbaram.gg/api/items/popular-with-prices?appVersion=2025_06_06&type=-1&days=1'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    data = response.json()

    result = []
    for item in data[:30]:
        name = item['name']
        price = f"{item['averagePrice']:,}전"
        result.append(f"{name}: {price}")
    return result


def map_job(job_code):
    job_map = {0: "공용", 1: "전사", 2: "도적", 3: "주술사", 4: "도사"}
    return job_map.get(job_code, f"직업코드 {job_code}")


async def fetch_all_items():
    """아이템 데이터를 안전하게 가져오기"""
    try:
        url = "https://www.classicbaram.gg/api/items/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Referer': 'https://classicbaram.gg/',
            'Connection': 'keep-alive'
        }

        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print(f"❌ API 오류: {resp.status}")
                    return []
    except Exception as e:
        print(f"❌ 아이템 데이터 로딩 오류: {e}")
        return []


async def get_item_detail(name):
    items = await fetch_all_items()
    keyword = name.replace(" ", "").lower()

    for item in items:
        item_name = item["name"].replace(" ", "").lower()
        if keyword in item_name:
            return {
                "이름": item.get("name"),
                "설명": item.get("desc"),
                "아이콘": item.get("iconUrl"),
                "내구도": {
                    "current": item.get("maxdura", 0),
                    "max": item.get("maxdura", 0),
                    "percent": 100
                },
                "파괴력": {
                    "S": f"{item.get('smin')} ~ {item.get('smax')}",
                    "L": f"{item.get('lmin')} ~ {item.get('lmax')}"
                },
                "전투스탯": {
                    "armor": item.get("ac", 0),
                    "hit": item.get("hit", 0),
                    "damage": item.get("dam", 0)
                },
                "능력치": {
                    "체력 상승": item.get("MHP", 0),
                    "마력 상승": item.get("MMP", 0),
                    "힘 상승": item.get("M", 0),
                    "지력 상승": item.get("G", 0),
                    "재생력 상승": item.get("hr", 0),
                    "마법방어 상승": item.get("md", 0)
                },
                "조건": {
                    "job": map_job(item.get("reqjob", 0)),
                    "level": item.get("reqlevel", 0),
                    "str": item.get("reqmight", 0),
                    "dex": item.get("reqwill", 0),
                    "int": item.get("reqgrace", 0)
                },
                "기타": {
                    "tradable": item.get("trade", 0) == 1,
                    "repairable": item.get("repair", 0) == 1,
                    "droppable": item.get("ondead", 0) != 2
                },
                "가격": item.get("price", 0)
            }
    return None


async def get_item_by_name(name):
    items = await fetch_all_items()
    keyword = name.replace(" ", "").lower()
    for item in items:
        item_name = item["name"].replace(" ", "").lower()
        if keyword in item_name:
            return item
    return None


# ============================================
# 🎁 방송 쿠폰 관련 함수
# ============================================
def get_broadcast_coupons():
    """방송 쿠폰 정보를 안전하게 가져오기"""
    try:
        url = "https://www.classicbaram.gg/broadcast"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Referer': 'https://classicbaram.gg/',
            'Connection': 'keep-alive'
        }

        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 503:
            return ["⚠️ 방송 쿠폰 서비스가 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도해주세요."]
        elif response.status_code != 200:
            return [f"❌ 방송 쿠폰 로딩 오류: HTTP {response.status_code}"]

        soup = BeautifulSoup(response.text, 'html.parser')
        coupons = []
        rows = soup.select('tbody tr')

        if not rows:
            return ["📭 현재 등록된 방송 쿠폰이 없습니다."]

        for row in rows:
            cells = row.select('td')
            if len(cells) < 4:
                continue
            channel = cells[0].get_text(strip=True)
            nickname = cells[1].get_text(strip=True)
            content = cells[2].get_text(strip=True)
            time_str = cells[3].get_text(strip=True)

            time_str_korean = convert_time_to_korean(time_str)
            coupons.append(f"{time_str_korean} | {nickname} ({channel}): {content}")

        return coupons if coupons else ["📭 현재 등록된 방송 쿠폰이 없습니다."]

    except requests.exceptions.Timeout:
        return ["⏰ 방송 쿠폰 로딩 시간 초과. 잠시 후 다시 시도해주세요."]
    except requests.exceptions.RequestException:
        return [f"❌ 네트워크 오류: 잠시 후 다시 시도해주세요."]
    except Exception:
        return [f"❌ 알 수 없는 오류가 발생했습니다. 잠시 후 다시 시도해주세요."]


# ============================================
# 📢 메이플스토리 월드 공지사항 모니터링
# ============================================
async def check_maplestory_notice():
    """메이플스토리 월드 공지사항 확인 (단순화된 버전)"""
    print("🔍 공지사항 확인을 위해 대안 방법 사용")
    return await check_maplestory_notice_simple()


async def check_maplestory_notice_simple():
    """간단한 방식으로 공지사항 확인 (실제 웹사이트 모니터링)"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'
        }

        urls_to_try = [
            "https://www.nexon.com/api/news/list?locale=ko-KR&game=maplestoryworlds",
            "https://www.nexon.com/ko/news/maplestoryworlds",
            "https://maplestoryworlds.nexon.com/api/notices",
            "https://maplestoryworlds.nexon.com/feed.xml"
        ]

        for url in urls_to_try:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    if 'api' in url:
                        try:
                            data = response.json()
                            if isinstance(data, dict) and 'notices' in data:
                                notices = []
                                for notice in data['notices'][:3]:
                                    notices.append({
                                        'title': notice.get('title', '제목 없음'),
                                        'link': notice.get('url', 'https://maplestoryworlds.nexon.com'),
                                        'date': notice.get('date', dt.datetime.now().strftime('%Y-%m-%d'))
                                    })
                                return notices
                        except Exception:
                            continue

                    soup = BeautifulSoup(response.text, 'html.parser')
                    notice_selectors = [
                        'a[href*="notice"]', 'a[href*="community"]', 'a[href*="board"]',
                        '.news-title', '.notice-title', '.board-title', 'h1', 'h2', 'h3', '.title'
                    ]

                    notices = []
                    for selector in notice_selectors:
                        elements = soup.select(selector)
                        for elem in elements[:3]:
                            title = elem.get_text(strip=True)
                            link = elem.get('href')

                            if title and len(title) > 10:
                                if link and isinstance(link, str) and not link.startswith('http'):
                                    link = 'https://maplestoryworlds.nexon.com' + link
                                elif not link:
                                    link = 'https://maplestoryworlds.nexon.com/ko/community/4402/5006?headlineId=3747'

                                notices.append({
                                    'title': title,
                                    'link': link,
                                    'date': dt.datetime.now().strftime('%Y-%m-%d %H:%M')
                                })

                        if notices:
                            break

                    if notices:
                        print(f"✅ 공지사항 {len(notices)}개 발견")
                        return notices[:3]

            except Exception as e:
                print(f"⚠️ URL {url} 확인 실패: {e}")
                continue

        print("⚠️ 모든 공지사항 소스에서 데이터를 가져올 수 없음")
        return None

    except Exception as e:
        print(f"❌ 공지사항 확인 오류: {e}")
        return None


def save_notice_hash(notices):
    """공지사항 해시값 저장"""
    global LAST_NOTICE_HASH
    if notices:
        notice_text = ''.join([notice['title'] for notice in notices])
        LAST_NOTICE_HASH = hashlib.md5(notice_text.encode()).hexdigest()
        save_notice_hash_to_file(LAST_NOTICE_HASH)


def load_notice_hash():
    """저장된 공지사항 해시값 로드"""
    try:
        with open('last_notice.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_notice_hash_to_file(hash_value):
    """공지사항 해시값을 파일에 저장"""
    try:
        with open('last_notice.txt', 'w', encoding='utf-8') as f:
            f.write(hash_value)
    except Exception as e:
        print(f"❌ 공지사항 해시 저장 오류: {e}")


# ============================================
# 📋 문원목록 관련 함수
# ============================================
async def get_member_list():
    """문원목록 데이터 가져오기 (Google Sheets 우선, 로컬 백업)"""
    try:
        sheet_urls = [
            "https://docs.google.com/spreadsheets/d/1GqNtV4O_AWMN8K0ESUZoQlCyVH4Azs8pKIzRW5YC1O8/export?format=csv&gid=593094554",
            "https://docs.google.com/spreadsheets/d/1GqNtV4O_AWMN8K0ESUZoQlCyVH4Azs8pKIzRW5YC1O8/gviz/tq?tqx=out:csv&gid=593094554"
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv,application/csv,text/plain,text/html'
        }

        for sheet_url in sheet_urls:
            try:
                response = requests.get(sheet_url, headers=headers, timeout=15, allow_redirects=True)

                print(f"🔍 Google Sheets 응답: {response.status_code}, 길이: {len(response.text)}")
                if response.status_code == 200 and response.text.strip() and '닉네임' in response.text:
                    csv_data = io.StringIO(response.text)
                    reader = csv.reader(csv_data)

                    rows = list(reader)
                    if rows and len(rows) > 1:
                        headers_row = rows[0]
                        data_rows = rows[1:]

                        data_rows = [row for row in data_rows if any(cell.strip() for cell in row if cell)]

                        print(f"✅ Google Sheets 문원목록 데이터 로딩 완료: {len(data_rows)}명")
                        return {'headers': headers_row, 'data': data_rows}
            except Exception as e:
                print(f"⚠️ URL {sheet_url} 시도 실패: {e}")
                continue

        print("⚠️ Google Sheets 접근 실패, 로컬 백업 파일 확인 중...")
        try:
            with open('member_list.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ 로컬 백업 문원목록 데이터 로딩 완료: {len(data.get('data', []))}명")
                return data
        except FileNotFoundError:
            print("❌ 로컬 백업 파일도 없습니다.")

        print("❌ 모든 데이터 소스에서 문원목록을 가져올 수 없습니다.")
        return None

    except Exception as e:
        print(f"❌ 문원목록 데이터 가져오기 오류: {e}")
        return None


def create_member_list_embed():
    """문원목록 임베드 생성"""
    sheet_link = "https://docs.google.com/spreadsheets/d/1GqNtV4O_AWMN8K0ESUZoQlCyVH4Azs8pKIzRW5YC1O8/edit?gid=593094554#gid=593094554"

    embed = discord.Embed(
        title="📋 \"맛\" 문파원 목록 리스트",
        url=sheet_link,
        description="📊 클릭하여 전체 문파원 목록을 확인하세요\n\n🔗 실시간으로 업데이트되는 문파원 정보",
        color=0x00ff88
    )

    embed.add_field(name="📝 포함 정보", value="• 닉네임\n• 직업\n• 차수\n• 상태\n• 본캐 여부", inline=True)

    embed.add_field(name="⚡ 특징", value="• 실시간 동기화\n• 언제든 업데이트\n• 전체 문파원 현황", inline=True)

    embed.set_footer(text="바람의나라 게임 가이드 봇 | 문파원 목록")

    return embed


def format_member_list(member_data):
    """문원목록 데이터를 Discord 메시지 형식으로 포맷"""
    if not member_data or not member_data.get('data'):
        return ["❌ 문원목록 데이터를 가져올 수 없습니다."]

    headers = member_data.get('headers', [])
    data_rows = member_data.get('data', [])

    max_length = 1900
    messages = []
    sheet_link = "https://docs.google.com/spreadsheets/d/1GqNtV4O_AWMN8K0ESUZoQlCyVH4Azs8pKIzRW5YC1O8/edit?gid=593094554#gid=593094554"
    current_message = f"📋 **[\"맛\" 문파원 목록 리스트]({sheet_link})**\n\n"

    if headers:
        header_line = " | ".join(f"**{header}**" for header in headers[:6])
        current_message += header_line + "\n"
        current_message += "─" * min(len(header_line), 50) + "\n\n"

    for i, row in enumerate(data_rows[:50], 1):
        if not any(cell.strip() for cell in row if cell):
            continue

        row_data = []
        for j, cell in enumerate(row[:6]):
            if cell and cell.strip():
                row_data.append(str(cell).strip())
            else:
                row_data.append("-")

        row_line = f"`{i:2d}.` " + " | ".join(row_data) + "\n"

        if len(current_message + row_line) > max_length:
            if current_message.strip():
                messages.append(current_message.strip())
            current_message = "📋 **문원목록 (계속)**\n\n" + row_line
        else:
            current_message += row_line

    if current_message.strip():
        messages.append(current_message.strip())

    if not messages:
        messages = ["❌ 표시할 문원목록 데이터가 없습니다."]

    return messages


def convert_time_to_korean(time_str):
    """영어 시간 표현을 한국어로 변환"""
    time_str = time_str.strip()

    if "a few seconds ago" in time_str:
        return "몇초전"
    elif "a few minutes ago" in time_str:
        return "몇분전"
    elif "a few hours ago" in time_str:
        return "몇시간전"
    elif "an hour ago" in time_str:
        return "1시간전"
    elif "a minute ago" in time_str:
        return "1분전"
    elif "a second ago" in time_str:
        return "1초전"
    elif "a day ago" in time_str:
        return "1일전"
    elif "minutes ago" in time_str:
        minutes = time_str.replace("minutes ago", "").strip()
        return f"{minutes}분전"
    elif "minute ago" in time_str:
        minutes = time_str.replace("minute ago", "").strip()
        return f"{minutes}분전"
    elif "hours ago" in time_str:
        hours = time_str.replace("hours ago", "").strip()
        return f"{hours}시간전"
    elif "hour ago" in time_str:
        hours = time_str.replace("hour ago", "").strip()
        return f"{hours}시간전"
    elif "days ago" in time_str:
        days = time_str.replace("days ago", "").strip()
        return f"{days}일전"
    elif "day ago" in time_str:
        days = time_str.replace("day ago", "").strip()
        return f"{days}일전"
    elif "seconds ago" in time_str:
        seconds = time_str.replace("seconds ago", "").strip()
        return f"{seconds}초전"
    elif "second ago" in time_str:
        seconds = time_str.replace("second ago", "").strip()
        return f"{seconds}초전"
    elif "just now" in time_str.lower():
        return "방금전"
    else:
        return time_str


# ============================================
# 🌍 지도 데이터 관련 함수
# ============================================
async def fetch_map_data_from_api():
    """API에서 최신 맵 데이터 가져오기"""
    try:
        url = "https://www.classicbaram.gg/api/maps"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Referer': 'https://classicbaram.gg/',
            'Connection': 'keep-alive'
        }

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    map_list = await resp.json()

                    map_data = {}
                    for map_item in map_list:
                        code = str(map_item.get('code', ''))
                        name = map_item.get('name', '')
                        if code and name:
                            map_data[code] = name

                    print(f"✅ API에서 맵 데이터 로딩 완료: {len(map_data)}개")
                    return map_data
                else:
                    print(f"❌ 맵 API 오류: {resp.status}")
                    return {}
    except Exception as e:
        print(f"❌ 맵 API 호출 오류: {e}")
        return {}


def save_map_data_to_file(map_data, filename='map_data.json'):
    """맵 데이터를 파일에 저장"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(map_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {filename} 파일 업데이트 완료: {len(map_data)}개")
        return True
    except Exception as e:
        print(f"❌ {filename} 파일 저장 오류: {e}")
        return False


async def update_map_data():
    """API에서 최신 맵 데이터를 가져와서 파일 업데이트"""
    try:
        new_map_data = await fetch_map_data_from_api()

        if not new_map_data:
            print("⚠️ API에서 맵 데이터를 가져올 수 없어 기존 파일 사용")
            return load_map_data_from_file()

        try:
            with open('map_data.json', 'r', encoding='utf-8') as f:
                old_map_data = json.load(f)
        except FileNotFoundError:
            old_map_data = {}
            print("🆕 map_data.json 파일이 없어 새로 생성합니다")

        added_maps = set(new_map_data.keys()) - set(old_map_data.keys())
        removed_maps = set(old_map_data.keys()) - set(new_map_data.keys())
        updated_maps = {k for k in new_map_data.keys() if k in old_map_data and new_map_data[k] != old_map_data[k]}

        if added_maps or removed_maps or updated_maps or not old_map_data:
            if save_map_data_to_file(new_map_data):
                print(f"🔄 맵 데이터 업데이트: +{len(added_maps)} -{len(removed_maps)} ~{len(updated_maps)}")
                if added_maps:
                    print(f"   추가된 맵: {', '.join([new_map_data[k] for k in list(added_maps)[:5]])}")
                if removed_maps:
                    print(f"   제거된 맵: {', '.join([old_map_data[k] for k in list(removed_maps)[:5]])}")
                return load_map_data_from_file()
        else:
            print("✅ 맵 데이터가 최신 상태입니다.")
            return load_map_data_from_file()

    except Exception as e:
        print(f"❌ 맵 데이터 업데이트 오류: {e}")
        return load_map_data_from_file()


def load_map_data_from_file(filename='map_data.json'):
    """파일에서 지도 데이터 로딩"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            if isinstance(raw_data, dict):
                return {
                    name: {
                        'title': name,
                        'link': f"https://www.classicbaram.gg/maps/{code}"
                    }
                    for code, name in raw_data.items()
                }
            return {entry['title']: entry for entry in raw_data}
    except Exception as e:
        print(f"❌ 지도 파일 로딩 오류: {e}")
        return {}


# ============================================
# 🤖 디스코드 봇 설정
# ============================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=['#', '!'], intents=intents)

user_exp_data = {}


def parse_exp_input(content):
    content = content.replace("억", "").strip()
    return int(float(content) * 100_000_000)


@bot.command(name="사냥")
async def 사냥(ctx, 닉네임: str, 시작경험치: str):
    user_id = ctx.author.id
    try:
        start_exp = parse_exp_input(시작경험치)
        user_exp_data[user_id] = {
            'nickname': 닉네임,
            'start_exp': start_exp,
            'start_time': dt.datetime.now()
        }
        await ctx.send(f"🧙 `{닉네임}`의 사냥을 시작합니다. 종료 시 `#사냥끝 닉네임 종료경험치`를 입력해주세요.")
    except Exception:
        await ctx.send("⚠️ 경험치는 `1.23억` 또는 `123000000` 형식으로 입력해주세요.")


@bot.command(name="사냥끝")
async def 사냥끝(ctx, 닉네임: str, 종료경험치: str):
    user_id = ctx.author.id
    data = user_exp_data.get(user_id)
    if not data or data.get('nickname') != 닉네임:
        await ctx.send("⚠️ 사냥 시작 정보가 없습니다. 먼저 `#사냥 닉네임 시작경험치`를 입력해주세요.")
        return
    try:
        end_exp = parse_exp_input(종료경험치)
        gained = end_exp - data['start_exp']
        minutes = (dt.datetime.now() - data['start_time']).total_seconds() / 60
        hourly = round(gained / minutes * 60)

        gained_str = f"{round(gained / 100_000_000, 2)}억"
        hourly_str = f"{round(hourly / 100_000_000, 2)}억"

        await ctx.send(
            f"📊 `{닉네임}`님의 사냥 결과\n"
            f"- 사냥 시간: {int(minutes)}분\n"
            f"- 획득 경험치: {gained_str}\n"
            f"- 시간당 경험치: {hourly_str}"
        )
        del user_exp_data[user_id]
    except Exception:
        await ctx.send("⚠️ 종료 경험치는 `1.23억` 또는 `123000000` 형식으로 입력해주세요.")


async def _post_daily_message():
    try:
        target_guild = None
        for guild in bot.guilds:
            if "맛" in guild.name:
                target_guild = guild
                break

        if not target_guild:
            print("❌ '맛' 서버를 찾을 수 없습니다.")
            return

        target_channel = None
        for channel in target_guild.text_channels:
            if "자유" in channel.name or "채팅" in channel.name or "일반" in channel.name:
                target_channel = channel
                break

        if not target_channel:
            print("❌ 자유채팅 채널을 찾을 수 없습니다.")
            return

        messages = [
            "🤖 바람의나라 정보가 필요하시다면 (**#사용법**) 을 입력해보세요!",
            "💡 아이템 정보, 시세, 맵 정보 등을 확인하려면 (**#사용법**) 을 써보세요!",
            "🎮 게임 도우미 봇 사용법이 궁금하시다면 (**#사용법**) 명령어를 입력해주세요!",
            "📚 봇의 모든 기능을 알아보려면 (**#사용법**) 을 채팅에 입력하세요!",
            "⚔️ 바람의나라 아이템 시세와 정보 확인하기: (**#사용법**) 입력!",
            "🗺️ 맵 정보, 아이템 검색, 방송 쿠폰까지! (**#사용법**) 으로 확인하세요!",
            "🔍 궁금한 아이템이 있으신가요? (**#사용법**) 을 입력해서 확인해보세요!"
        ]

        message = random.choice(messages)
        await target_channel.send(message)
        print(f"📨 일일 메시지 전송 완료: {target_guild.name} > {target_channel.name}")

    except Exception as e:
        print(f"❌ 일일 메시지 전송 오류: {e}")


@tasks.loop(hours=24)
async def daily_message():
    await _post_daily_message()


@daily_message.before_loop
async def before_daily_message():
    await bot.wait_until_ready()

    now = dt.datetime.now()
    next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)

    if now.hour >= 9:
        next_run += dt.timedelta(days=1)

    wait_seconds = (next_run - now).total_seconds()
    print(f"⏰ 다음 일일 메시지까지 {wait_seconds/3600:.1f}시간 대기")
    await asyncio.sleep(wait_seconds)


@tasks.loop(hours=6)
async def auto_update_maps():
    try:
        global MAP_DATA
        print("🔄 맵 데이터 자동 업데이트 시작...")

        new_map_data = await update_map_data()
        if new_map_data:
            MAP_DATA = new_map_data
            print("✅ 맵 데이터 자동 업데이트 완료")
        else:
            print("⚠️ 맵 데이터 자동 업데이트 실패, 기존 데이터 유지")

    except Exception as e:
        print(f"❌ 맵 데이터 자동 업데이트 오류: {e}")


@auto_update_maps.before_loop
async def before_auto_update_maps():
    await bot.wait_until_ready()


@tasks.loop(minutes=30)
async def check_notice_updates():
    try:
        global LAST_NOTICE_HASH

        print("🔍 메이플스토리 월드 공지사항 확인 중...")

        notices = await check_maplestory_notice()

        if not notices:
            print("⚠️ 공지사항을 가져올 수 없습니다.")
            return

        current_text = ''.join([notice['title'] for notice in notices])
        current_hash = hashlib.md5(current_text.encode()).hexdigest()

        if LAST_NOTICE_HASH is None:
            LAST_NOTICE_HASH = load_notice_hash()

        if LAST_NOTICE_HASH != current_hash:
            print("🆕 새로운 공지사항 발견!")

            await send_notice_to_discord(notices)

            save_notice_hash(notices)
            print("✅ 공지사항 알림 전송 완료")
        else:
            print("✅ 공지사항 변경사항 없음")

    except Exception as e:
        print(f"❌ 공지사항 확인 오류: {e}")


@check_notice_updates.before_loop
async def before_check_notice_updates():
    await bot.wait_until_ready()

    global LAST_NOTICE_HASH
    LAST_NOTICE_HASH = load_notice_hash()


async def send_notice_to_discord(notices):
    """Discord에 공지사항 알림 전송"""
    try:
        target_guild = None
        for guild in bot.guilds:
            if "맛" in guild.name:
                target_guild = guild
                break

        if not target_guild:
            print("❌ '맛' 서버를 찾을 수 없습니다.")
            return

        target_channel = None
        for channel in target_guild.text_channels:
            if "💬자유채팅" in channel.name or "자유채팅" in channel.name:
                target_channel = channel
                break

        if not target_channel:
            for channel in target_guild.text_channels:
                if "자유" in channel.name or "채팅" in channel.name or "일반" in channel.name:
                    target_channel = channel
                    break

        if not target_channel:
            target_channel = target_guild.text_channels[0] if target_guild.text_channels else None

        if not target_channel:
            print("❌ 알림을 보낼 채널을 찾을 수 없습니다.")
            return

        embed = discord.Embed(
            title="🎮 메이플스토리 월드 새 공지사항",
            description="새로운 공지사항이 등록되었습니다!",
            color=0xff6b35,
            timestamp=dt.datetime.now(dt.timezone.utc)
        )

        for i, notice in enumerate(notices[:3], 1):
            embed.add_field(
                name=f"📋 공지 {i}",
                value=f"**{notice['title']}**\n🔗 [자세히 보기]({notice['link']})\n📅 {notice['date']}",
                inline=False
            )

        embed.set_footer(text="메이플스토리 월드 공지사항 모니터링")

        await target_channel.send(embed=embed)

    except Exception as e:
        print(f"❌ Discord 알림 전송 오류: {e}")


@bot.event
async def on_message(message):
    global MAP_DATA

    if message.author == bot.user:
        return

    content = message.content.strip()

    if content.startswith('!시작'):
        await message.channel.send('🤖 봇이 준비되었습니다!')

    if content.startswith('!재시작'):
        if message.author.id == 406762436779827200:
            await message.channel.send('🔄 봇을 재시작합니다...')
            print("🔄 봇이 재시작됩니다.")
            await bot.close()
            import subprocess
            import sys
            subprocess.Popen([sys.executable, "main.py"])
            raise SystemExit
        else:
            await message.channel.send('❌ 봇 재시작 권한이 없습니다.')

    if content.startswith('#사용법'):
        embed = discord.Embed(
            title="🤖 디스코드 봇(몸빵이) 사용법 안내",
            description=(
                "**이 봇은 [클바지지](https://classicbaram.gg) 기반으로 다양한 정보를 빠르게 확인할 수 있도록 도와줍니다.**\n"
                "아래 명령어들을 입력해보세요!"
            ),
            color=0x7289da
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="📦 아이템 정보 조회",
            value=(
                "```#템#아이템이름```\n"
                "**예시:** `#템#심판의낫`\n"
                "**설명:** 아이템의 상세 능력치, 착용 조건, 거래 여부, 가격 등을 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="🧪 아이템 조합 정보",
            value=(
                "```#조합#아이템이름```\n"
                "**예시:** `#조합#가시철도`\n"
                "**설명:** 제작에 필요한 재료와 성공 확률을 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="💰 아이템 시세 조회",
            value=(
                "```#시세#아이템이름```\n"
                "**예시:** `#시세#심판의낫`\n"
                "**설명:** 최근 3일간의 평균 시세를 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="📈 인기 아이템 TOP 30 시세",
            value=(
                "```#시세```\n"
                "**설명:** 최근 가장 많이 거래된 아이템 30개의 평균 시세를 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="🎁 실시간 방송 쿠폰 정보",
            value=(
                "```#방송```\n"
                "**설명:** 바람의나라 방송 페이지에서 등록된 쿠폰 정보를 정리해서 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="🗺️ 맵 정보 조회",
            value=(
                "```#맵#지도이름```\n"
                "**예시:** `#맵#백두산`\n"
                "**설명:** 해당 맵의 링크와 이미지 썸네일을 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="🧾 맛 문원목록 조회",
            value=(
                "```#문원목록```\n"
                "**설명:** 맛_문파원의 닉네임, 직업, 차수, 활동상태, 부캐정보 등을 출력."
            ),
            inline=False
        )

        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━━━━", value="", inline=False)

        embed.add_field(
            name="🛠️ 추가 팁",
            value=(
                "- 아이템 이름은 **띄어쓰기 없이도 검색 가능**.\n"
                "- 정보가 없을 경우 **classicbaram.gg 등록 여부**를 확인.\n"
                "- **실시간 데이터 기반**으로 최신 정보를 제공."
            ),
            inline=False
        )

        await message.channel.send(embed=embed)

    elif content.startswith('#시세#'):
        keyword = content.replace('#시세#', '').strip()
        item = search_item_across_types(keyword)
        if item:
            embed = discord.Embed(title=f"{item['name']} 시세 정보", description=f"평균 가격: {item['price']}", color=0x00ff99)
            if item['image']:
                embed.set_thumbnail(url=item['image'])
            await message.channel.send(embed=embed)
        else:
            await message.channel.send(f'"{keyword}" 아이템을 찾을 수 없습니다.')

    elif content.startswith('#시세'):
        try:
            prices = get_top_items()
            await message.channel.send('\n'.join(prices) if prices else '아이템 정보를 찾을 수 없습니다.')
        except Exception as e:
            await message.channel.send(f'❌ 오류 발생: {e}')

    elif content.startswith('#방송'):
        try:
            coupons = get_broadcast_coupons()
            if not coupons:
                await message.channel.send("방송 쿠폰 정보를 찾을 수 없습니다.")
                return

            current_message = "실시간 방송 쿠폰 정보\n\n"
            for line in coupons:
                try:
                    time_str, rest = line.split(" | ", 1)
                    nickname_channel, content_str = rest.split("): ", 1)
                    nickname, channel = nickname_channel.split(" (")
                    channel = channel.strip(")")

                    formatted = f"{time_str.ljust(3)} | {nickname.ljust(6)} ({channel.ljust(4)}) | {content_str}\n"

                    if len(current_message) + len(formatted) > 1900:
                        await message.channel.send(current_message)
                        current_message = ""
                    current_message += formatted
                except Exception as parse_error:
                    print(f"❌ 쿠폰 파싱 오류: {parse_error}")
                    continue

            if current_message:
                await message.channel.send(current_message)

        except Exception as e:
            await message.channel.send(f'❌ 방송 정보 오류: {e}')

    elif content.startswith('#맵#'):
        keyword = content.replace('#맵#', '').strip().replace(" ", "")
        if MAP_DATA:
            matches = [name for name in MAP_DATA if keyword in name.replace(" ", "")]

            if matches:
                matched = matches[0]
                map_info = MAP_DATA[matched]
                embed = discord.Embed(
                    title=f"🗺️ 맵: {matched}",
                    url=map_info['link'],
                    description="클릭하면 맵 페이지로 이동합니다.",
                    color=0x00bfff
                )
                if map_info.get('image'):
                    embed.set_thumbnail(url=map_info.get('image', ''))
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f'"{keyword}"에 해당하는 지도를 찾을 수 없습니다.')
        else:
            await message.channel.send('❌ 맵 데이터를 로딩할 수 없습니다.')

    elif content.startswith('#맵업데이트'):
        if message.author.id == 406762436779827200:
            await message.channel.send("🔄 맵 데이터 업데이트를 시작합니다...")
            try:
                new_map_data = await update_map_data()
                if new_map_data:
                    MAP_DATA = new_map_data
                    await message.channel.send(f"✅ 맵 데이터 업데이트 완료! 총 {len(MAP_DATA)}개 맵")
                else:
                    await message.channel.send("❌ 맵 데이터 업데이트 실패")
            except Exception as e:
                await message.channel.send(f"❌ 업데이트 오류: {e}")
        else:
            await message.channel.send("❌ 맵 업데이트 권한이 없습니다.")

    elif content.startswith('#맵상태'):
        if message.author.id == 406762436779827200:
            if MAP_DATA:
                total_maps = len(MAP_DATA)
                sample_maps = list(MAP_DATA.keys())[:5]
                await message.channel.send(
                    f"📊 맵 데이터 상태:\n"
                    f"- 총 맵 개수: {total_maps}개\n"
                    f"- 샘플 맵: {', '.join(sample_maps)}"
                )
            else:
                await message.channel.send("❌ 맵 데이터가 로딩되지 않았습니다.")
        else:
            await message.channel.send("❌ 맵 상태 확인 권한이 없습니다.")

    elif content.startswith('#공지확인'):
        if message.author.guild_permissions.administrator or message.author.id in {406762436779827200, 1346640980517847051}:
            await message.channel.send("🔍 메이플스토리 월드 공지사항을 확인하고 있습니다...")
            try:
                notices = await check_maplestory_notice()
                if notices:
                    embed = discord.Embed(
                        title="🎮 메이플스토리 월드 공지사항",
                        description="현재 등록된 공지사항입니다.",
                        color=0xff6b35
                    )

                    for i, notice in enumerate(notices[:3], 1):
                        embed.add_field(
                            name=f"📋 공지 {i}",
                            value=f"**{notice['title']}**\n🔗 [자세히 보기]({notice['link']})\n📅 {notice['date']}",
                            inline=False
                        )

                    await message.channel.send(embed=embed)
                else:
                    await message.channel.send("❌ 현재 새로운 공지사항이 없습니다.")
            except Exception as e:
                await message.channel.send(f"❌ 공지사항 확인 오류: {e}")
        else:
            try:
                await message.channel.send("❌ 공지사항 확인 권한이 없습니다.")
            except discord.Forbidden:
                print(f"❌ 메시지 전송 권한 없음: {message.channel.name}")

    elif content.startswith('#공지테스트'):
        if message.author.guild_permissions.administrator or message.author.id in {406762436779827200, 1346640980517847051}:
            await message.channel.send("🧪 공지사항 알림 테스트를 시작합니다...")
            try:
                test_notices = [{
                    'title': f'[테스트] 메이플스토리 월드 공지사항 알림 테스트',
                    'link': 'https://maplestoryworlds.nexon.com/ko/community/4402/5006?headlineId=3747',
                    'date': dt.datetime.now().strftime('%Y-%m-%d %H:%M')
                }]

                await send_notice_to_discord(test_notices)
                await message.channel.send("✅ 공지사항 알림 테스트 완료!")
            except Exception as e:
                await message.channel.send(f"❌ 테스트 실패: {e}")
        else:
            try:
                await message.channel.send("❌ 공지사항 테스트 권한이 없습니다.")
            except discord.Forbidden:
                print(f"❌ 메시지 전송 권한 없음: {message.channel.name}")

    elif content.startswith('#문원목록'):
        try:
            embed = create_member_list_embed()
            await message.channel.send(embed=embed)
        except Exception as e:
            await message.channel.send(f"❌ 문원목록 조회 오류: {e}")

    elif content.startswith('#조합#'):
        item_name = content.replace('#조합#', '').strip()
        try:
            item = await get_item_by_name(item_name)
            if item and item.get("recipe"):
                recipe = item["recipe"]

                embed = discord.Embed(
                    title=f"🧪 조합: {item['name']}",
                    description=f"성공 확률: {recipe['successRate']}%",
                    color=0x3498db
                )
                embed.set_thumbnail(url=item.get("iconUrl", ""))

                material_text = ""
                for mat in recipe["materials"]:
                    mat_item = mat["item"]
                    material_text += f"- {mat_item['name']} x{mat['quantity']}\n"

                embed.add_field(name="필요 재료", value=material_text, inline=False)
                await message.channel.send(embed=embed)
            else:
                await message.channel.send(f"❌ '{item_name}'에 대한 조합 정보를 찾을 수 없습니다.")
        except Exception as e:
            await message.channel.send(f"❌ 조합 정보 처리 중 오류 발생: {e}")

    elif content.startswith('#템#'):
        item_name = content.replace('#템#', '').strip()
        try:
            item = await get_item_detail(item_name)
            if not item:
                await message.channel.send(f"❌ '{item_name}'에 대한 아이템 정보를 찾을 수 없습니다.")
                return

            embed = discord.Embed(title=f"📦 {item['이름']} 상세정보", color=0xffcc00)

            if item.get("아이콘"):
                embed.set_thumbnail(url=item["아이콘"])

            durability = item.get("내구도")
            if isinstance(durability, dict) and durability.get("max", 0) > 0:
                embed.add_field(
                    name="내구도",
                    value=f"{durability.get('current', '-')} / {durability.get('max', '-')} ({durability.get('percent', '-')}%)",
                    inline=False
                )

            power = item.get("파괴력")
            if isinstance(power, dict) and (power.get("S") or power.get("L")):
                embed.add_field(
                    name="파괴력",
                    value=f"S: {power.get('S', '-')} | L: {power.get('L', '-')}",
                    inline=False
                )

            combat = item.get("전투스탯")
            if isinstance(combat, dict) and any(combat.get(k, 0) > 0 for k in ["armor", "hit", "damage"]):
                embed.add_field(
                    name="전투 스탯",
                    value=f"무장: {combat.get('armor', 0)} | Hit: {combat.get('hit', 0)} | Dam: {combat.get('damage', 0)}",
                    inline=False
                )

            stats = item.get("능력치")
            if isinstance(stats, dict):
                stat_lines = [f"{k} 상승: {v}" for k, v in stats.items() if v != 0]
                if stat_lines:
                    embed.add_field(name="능력치", value="\n".join(stat_lines), inline=False)

            condition = item.get("조건")
            if isinstance(condition, dict):
                condition_lines = []
                if condition.get("job") != "공용":
                    condition_lines.append(f"직업: {condition.get('job', '-')}")
                if condition.get("level", 0) > 0:
                    condition_lines.append(f"레벨: {condition.get('level')} 이상")
                if condition.get("str", 0) > 0:
                    condition_lines.append(f"힘: {condition.get('str')}")
                if condition.get("dex", 0) > 0:
                    condition_lines.append(f"민첩: {condition.get('dex')}")
                if condition.get("int", 0) > 0:
                    condition_lines.append(f"지력: {condition.get('int')}")
                if condition_lines:
                    embed.add_field(name="착용 조건", value="\n".join(condition_lines), inline=False)

            misc = item.get("기타")
            if isinstance(misc, dict):
                embed.add_field(
                    name="기타 정보",
                    value=(
                        f"거래: {'O' if misc.get('tradable') else 'X'}\n"
                        f"수리: {'O' if misc.get('repairable') else 'X'}\n"
                        f"사망 시 보존: {'O' if misc.get('droppable') else 'X'}"
                    ),
                    inline=False
                )

            price = item.get("가격")
            if isinstance(price, int) and price > 0:
                embed.add_field(name="가격", value=f"{price:,}전", inline=False)

            if item.get("설명"):
                embed.add_field(name="설명", value=item["설명"], inline=False)

            await message.channel.send(embed=embed)

        except Exception as e:
            await message.channel.send(f"⚠️ 아이템 정보 처리 중 오류 발생: {e}")

    await bot.process_commands(message)


@bot.command()
@commands.is_owner()
async def 종료(ctx):
    await ctx.send("🛑 봇을 종료합니다.")
    print("🛑 봇이 종료되었습니다.")
    await bot.close()


@bot.command()
@commands.is_owner()
async def 재시작(ctx):
    await ctx.send("🔄 봇을 재시작합니다...")
    print("🔄 봇이 재시작됩니다.")
    await bot.close()
    import subprocess
    import sys
    subprocess.Popen([sys.executable, "main.py"])
    raise SystemExit


@bot.command()
@commands.is_owner()
async def 일일메시지테스트(ctx):
    """일일 메시지 기능을 즉시 테스트"""
    await ctx.send("📨 일일 메시지 테스트를 시작합니다...")
    try:
        await _post_daily_message()
        await ctx.send("✅ 일일 메시지 테스트 완료!")
    except Exception as e:
        await ctx.send(f"❌ 테스트 실패: {e}")


@bot.event
async def on_ready():
    global MAP_DATA

    MAP_DATA = await update_map_data()
    print(f"✅ 봇 로그인 완료: {bot.user}")
    print(f"🗺️ 지도 데이터 로딩 완료: {len(MAP_DATA) if MAP_DATA else 0}개")

    try:
        bot.load_extension('cogs.game_commands')
        print("✅ GameCommands cog 로드 완료 (# prefix 명령어 시스템)")
    except Exception as e:
        print(f"❌ GameCommands cog 로드 실패: {e}")
        try:
            from cogs.game_commands import GameCommands
            bot.add_cog(GameCommands(bot))
            print("✅ 수동 GameCommands cog 로드 완료 (# prefix 명령어 시스템)")
        except Exception as e2:
            print(f"❌ 수동 cog 로드도 실패: {e2}")

    if not daily_message.is_running():
        daily_message.start()
        print("📅 일일 메시지 스케줄러 시작됨")

    if not auto_update_maps.is_running():
        auto_update_maps.start()
        print("🗺️ 맵 데이터 자동 업데이트 스케줄러 시작됨")

    if not check_notice_updates.is_running():
        check_notice_updates.start()
        print("📢 메이플스토리 월드 공지사항 모니터링 시작됨")


keep_alive()

token = os.environ.get('DISCORD_BOT_TOKEN')
if not token:
    print("❌ DISCORD_BOT_TOKEN 환경 변수가 설정되지 않았습니다. 토큰을 설정한 후 다시 실행하세요.")
else:
    bot.run(token)