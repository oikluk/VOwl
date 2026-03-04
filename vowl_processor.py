import urllib.request
import base64
import re
import socket
from concurrent.futures import ThreadPoolExecutor

SOURCES = [
    "https://raw.githubusercontent.com/tankist939-afk/Obhod-WL/refs/heads/main/Obhod%20WL",
    "https://raw.githubusercontent.com/vsevjik/OBWL/refs/heads/main/wwh",
    "https://wlrus.lol/confs/selected.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/whitelist"
]

LIMIT = 60 # Максимальное количество конфигов

def get_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read().decode('utf-8', errors='ignore')
            if re.match(r'^[A-Za-z0-9+/=\s]+$', data) and '://' not in data[:50]:
                return base64.b64decode(data).decode('utf-8', errors='ignore')
            return data
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return ""

def check_port(config):
    try:
        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0]
        host, port = server_info.split(':') if ':' in server_info else (server_info, 443)
        with socket.create_connection((host, int(port)), timeout=2.0):
            return config
    except:
        return None

def extract_flag(config):
    name_part = config.split('#')[1] if '#' in config else ""
    flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', name_part)
    return flags[0] if flags else "🌐"

def main():
    raw_list = []
    
    print("--- Сбор данных ---")
    for url in SOURCES:
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            if '://' in line and not line.startswith('#'):
                raw_list.append(line)

    # 1. nonobr.txt (Все уникальные, без лимита)
    nonobr_final = sorted(list(set(raw_list)))
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    # Удаление дублей по адресу сервера
    unique_map = {}
    for cfg in nonobr_final:
        address = cfg.split('#')[0].strip()
        if address not in unique_map:
            unique_map[address] = cfg
    
    unique_list = list(unique_map.values())

    print(f"Проверка {len(unique_list)} серверов...")

    # 2. Проверка и ограничение до LIMIT
    working_configs = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        for result in executor.map(check_port, unique_list):
            if result:
                working_configs.append(result)
                if len(working_configs) >= LIMIT: # Останавливаемся, если на
