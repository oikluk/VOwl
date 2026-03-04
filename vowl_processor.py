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
# ----------------------------

SOURCES = {
    "Obhod-WL": "https://raw.githubusercontent.com/tankist939-afk/Obhod-WL/refs/heads/main/Obhod%20WL",
    "vsevjik": "https://raw.githubusercontent.com/vsevjik/OBWL/refs/heads/main/wwh",
    "wlrus": "https://wlrus.lol/confs/selected.txt",
    "zieng2": "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "EtoNeYa": "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/whitelist"
}

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

def strict_proxy_get(config_data):
    """Максимально жесткая проверка via Proxy GET"""
    config, source_name = config_data
    sock = None
    try:
        # Парсинг хоста и порта
        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        # Парсинг SNI (без него в утиль)
        sni_match = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE)
        if not sni_match: return None
        sni = sni_match.group(1)

        start_time = time.time()
        
        # 1. TCP Connect
        sock = socket.create_connection((host, port), timeout=2.5)
        
        # 2. TLS Handshake
        context = ssl._create_unverified_context()
        with context.wrap_socket(sock, server_hostname=sni) as ssock:
            # 3. Реальный HTTP запрос к Google
            # Если прокси рабочий, он вернет заголовки Google
            http_request = (
                f"GET /generate_204 HTTP/1.1\r\n"
                f"Host: www.google.com\r\n"
                f"User-Agent: Mozilla/5.0\r\n"
                f"Connection: close\r\n\r\n"
            )
            ssock.sendall(http_request.encode())
            
            # Читаем ответ. Нам нужно увидеть HTTP/1.1 204 No Content
            response = ssock.recv(1024).decode('utf-8', errors='ignore')
            
            if "HTTP/1.1 204" in response or "HTTP/1.1 200" in response:
                latency = int((time.time() - start_time) * 1000)
                return {"config": config, "ping": latency, "source": source_name}
        
        return None
    except:
        return None
    finally:
        if sock: sock.close()

def extract_flag(config):
    try:
        name_part = config.split('#')[1] if '#' in config else ""
        flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', name_part)
        return flags[0] if flags else "🌐"
    except: return "🌐"

def main():
    all_candidates = []
    print("--- Сбор данных ---")
    for name, url in SOURCES.items():
        content = get_content(url)
        c = 0
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('vless://') and "sni=" in line.lower():
                all_candidates.append((line, name))
                c += 1
        print(f"[{name}]: найдено {c}")

    # Уникальность
    unique_map = {}
    for cfg, name in all_candidates:
        addr = cfg.split('#')[0].strip()
        if addr not in unique_map: unique_map[addr] = (cfg, name)
    
    candidates = list(unique_map.values())
    random.shuffle(candidates)

    # nonobr.txt
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([c[0] for c in candidates[:TOTAL_MAX_CONFS]]))

    print(f"\nЗапуск жесткой проверки пачками (Всего кандидатов: {len(candidates)})")
    
    working_results = []
    
    # Решение проблемы 64: Идем мелкими пачками (chunks)
    chunk_size = 20 
    for i in range(0, len(candidates), chunk_size):
        if len(working_results) >= LIMIT_PER_RUN: break
        
        chunk = candidates[i:i+chunk_size]
        print(f"Проверка пачки {i//chunk_size + 1}...")
        
        with ThreadPoolExecutor(max_workers=chunk_size) as executor:
            results = list(executor.map(strict_proxy_get, chunk))
            for r in results:
                if r:
                    working_results.append(r)
                    if len(working_results) >= LIMIT_PER_RUN: break
        
        # Небольшая пауза между пачками, чтобы ОС успела закрыть сокеты
        time.sleep(0.5)

    working_results.sort(key=lambda x: x['ping'])

    # Сохранение
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([r['config'] for r in working_results]))

    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n#profile-title: 🌐 VOwl\n#announce: Не используй на сервисах из Белого Списка\n\n")
        for i, res in enumerate(working_results, 1):
            flag = extract_flag(res['config'])
            clean = res['config'].split('#')[0].strip()
            f.write(f"{clean}#{flag} №{i} VOwl\n")
            
    print(f"\nГОТОВО. В файле {len(working_results)} элитных конфигов.")

if __name__ == "__main__":
    main()
