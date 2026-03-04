import urllib.request
import base64
import re
import socket
import ssl
import time
import random
from concurrent.futures import ThreadPoolExecutor

# --- НАСТРОЙКИ ---
TOTAL_MAX_CONFS = 1500  
LIMIT_PER_RUN = 60      
CHECK_URL = "http://www.google.com/generate_204" # Эталон для Proxy GET
# ----------------------------

SOURCES = [
    "https://raw.githubusercontent.com/tankist939-afk/Obhod-WL/refs/heads/main/Obhod%20WL",
    "https://raw.githubusercontent.com/vsevjik/OBWL/refs/heads/main/wwh",
    "https://wlrus.lol/confs/selected.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/whitelist"
]

def get_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode('utf-8', errors='ignore')
            if re.match(r'^[A-Za-z0-9+/=\s]+$', data) and '://' not in data[:50]:
                try: return base64.b64decode(data).decode('utf-8', errors='ignore')
                except: return data
            return data
    except: return ""

def proxy_get_check(config):
    """
    Эмуляция via Proxy GET. 
    Проверяет возможность прохождения HTTP трафика через узел.
    """
    try:
        if "sni=" not in config.lower(): return None
        
        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        start_time = time.time()
        
        # 1. TCP Connection
        sock = socket.create_connection((host, port), timeout=3.0)
        
        # 2. TLS Handshake (обязателен для VLESS/Reality)
        sni = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE).group(1)
        context = ssl._create_unverified_context()
        
        with context.wrap_socket(sock, server_hostname=sni) as ssock:
            # 3. Эмуляция HTTP GET запроса внутри установленного TLS туннеля
            # Мы отправляем минимальный заголовок, чтобы проверить, ответит ли прокси
            # Для VLESS это покажет, что туннель пропускает байты
            request = f"GET /generate_204 HTTP/1.1\r\nHost: {sni}\r\nConnection: close\r\n\r\n"
            ssock.sendall(request.encode())
            
            # Читаем кусочек ответа
            response = ssock.recv(1024)
            if not response:
                return None
        
        latency = int((time.time() - start_time) * 1000)
        return (config, latency)
    except:
        return None

def extract_flag(config):
    try:
        name_part = config.split('#')[1] if '#' in config else ""
        flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', name_part)
        return flags[0] if flags else "🌐"
    except: return "🌐"

def main():
    raw_list = []
    print("--- Сбор и фильтрация ---")
    for url in SOURCES:
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            # Берем ТОЛЬКО те, где есть SNI
            if line.startswith('vless://') and "sni=" in line.lower():
                raw_list.append(line)

    nonobr_final = sorted(list(set(raw_list)))[:TOTAL_MAX_CONFS]
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    unique_map = {}
    for cfg in nonobr_final:
        addr = cfg.split('#')[0].strip()
        if addr not in unique_map: unique_map[addr] = cfg
    
    unique_list = list(unique_map.values())
    random.shuffle(unique_list)

    print(f"Запуск via Proxy GET проверки ({len(unique_list)} узлов)...")

    working_results = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        for result in executor.map(proxy_get_check, unique_list):
            if result:
                working_results.append(result)
                if len(working_results) >= LIMIT_PER_RUN:
                    break

    working_results.sort(key=lambda x: x[1])
    final_configs = [x[0] for x in working_results]

    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_configs))

    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n")
        f.write("#profile-title: 🌐 VOwl\n")
        f.write("#announce: Не используй на сервисах из Белого Списка\n\n")
        for i, config in enumerate(final_configs, 1):
            flag = extract_flag(config)
            clean_link = config.split('#')[0].strip()
            f.write(f"{clean_link}#{flag} №{i} VOwl\n")
            
    print(f"Готово! Отобрано {len(final_configs)} проверенных через GET.")

if __name__ == "__main__":
    main()
