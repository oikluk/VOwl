import urllib.request
import base64
import re
import socket
import ssl
import time
import random
from concurrent.futures import ThreadPoolExecutor

# --- НАСТРОЕЧКИ 🔪 ---
TOTAL_MAX_CONFS = 1500  # Максимальное количество в nonobr.txt
LIMIT_PER_RUN = 60      # Сколько рабочих конфигов отобрать в gotov.txt
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
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read().decode('utf-8', errors='ignore')
            if re.match(r'^[A-Za-z0-9+/=\s]+$', data) and '://' not in data[:50]:
                try: return base64.b64decode(data).decode('utf-8', errors='ignore')
                except: return data
            return data
    except: return ""

def hard_check_vless(config):
    """Жёсткая проверка: TCP + TLS Handshake + Проверка на SNI + Пинг"""
    try:
        # 1. Удаляем мусор по названию
        if any(x in config.lower() for x in ["n/a", "н/д", "offline"]):
            return None
        
        # 2. Считаем мусором конфиги без SNI
        if "sni=" not in config.lower():
            return None

        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        start_time = time.time()
        # L4 Check
        sock = socket.create_connection((host, port), timeout=3.0)
        
        # L7 Check (Попытка TLS Handshake)
        # Извлекаем SNI из ссылки для корректного рукопожатия
        sni_match = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE)
        server_hostname = sni_match.group(1) if sni_match else host

        context = ssl._create_unverified_context()
        with context.wrap_socket(sock, server_hostname=server_hostname) as ssock:
            pass
        
        ping = int((time.time() - start_time) * 1000)
        sock.close()
        return (config, ping)
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
    print(f"--- Сбор VLESS (Лимит базы: {TOTAL_MAX_CONFS}) ---")
    for url in SOURCES:
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            # Берем только VLESS, где есть SNI и нет меток нерабочести
            if line.startswith('vless://') and "sni=" in line.lower() and not any(x in line.lower() for x in ["n/a", "н/д"]):
                raw_list.append(line)

    # 1. nonobr.txt (Уникальные VLESS со SNI, ограничено TOTAL_MAX_CONFS)
    nonobr_final = sorted(list(set(raw_list)))[:TOTAL_MAX_CONFS]
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    # Уникальность по адресу для проверки
    unique_map = {}
    for cfg in nonobr_final:
        try:
            addr = cfg.split('#')[0].strip()
            if addr not in unique_map: unique_map[addr] = cfg
        except: continue
    
    unique_list = list(unique_map.values())
    random.shuffle(unique_list)

    print(f"Поиск {LIMIT_PER_RUN} лучших рабочих узлов...")

    working_results = []
    with ThreadPoolExecutor(max_workers=25) as executor:
        for result in executor.map(hard_check_vless, unique_list):
            if result:
                working_results.append(result)
                if len(working_results) >= LIMIT_PER_RUN:
                    break

    # Сортировка по пингу
    working_results.sort(key=lambda x: x[1])
    final_configs = [x[0] for x in working_results]

    # 2. nonname.txt
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(final_configs))

    # 3. gotov.txt
    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n")
        f.write("#profile-title: 🌐 VOwl\n")
        f.write("#announce: Не используй на сервисах из Белого Списка\n\n")
        
        for i, config in enumerate(final_configs, 1):
            flag = extract_flag(config)
            clean_link = config.split('#')[0].strip()
            f.write(f"{clean_link}#{flag} №{i} VOwl\n")
            
    print(f"Успех. База: {len(nonobr_final)}, Отобрано рабочих: {len(final_configs)}")

if __name__ == "__main__":
    main()
