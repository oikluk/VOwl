import urllib.request
import base64
import re
import socket
import ssl
import time
import random
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- НАСТРОЙКИ ---
TOTAL_MAX_CONFS = 1500  
LIMIT_PER_RUN = 60      
# ----------------------------

SOURCES = {
    "Obhod-WL": "https://raw.githubusercontent.com/tankist939-afk/Obhod-WL/refs/heads/main/Obhod%20WL",
    "OBWL": "https://raw.githubusercontent.com/vsevjik/OBWL/refs/heads/main/wwh",
    "wlrus": "https://wlrus.lol/confs/selected.txt",
    "zieng2": "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "EtoNeYa": "https://raw.githubusercontent.com/EtoNeYaProject/etoneyaproject.github.io/refs/heads/main/whitelist"
}

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

def proxy_get_check(config_data):
    """
    Proxy GET: TCP -> TLS -> HTTP GET
    config_data: кортеж (link, source_name)
    """
    config, source_name = config_data
    sock = None
    try:
        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        sni_match = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE)
        sni = sni_match.group(1) if sni_match else host

        start_time = time.time()
        sock = socket.create_connection((host, port), timeout=3.0)
        
        context = ssl._create_unverified_context()
        with context.wrap_socket(sock, server_hostname=sni) as ssock:
            # Чистый Proxy GET
            http_request = f"GET /generate_204 HTTP/1.1\r\nHost: {sni}\r\nConnection: close\r\n\r\n"
            ssock.sendall(http_request.encode())
            ssock.settimeout(2.0)
            response = ssock.recv(256)
            if not response or b"HTTP" not in response:
                return None
        
        latency = int((time.time() - start_time) * 1000)
        return {"config": config, "ping": latency, "source": source_name}
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
    # Лимиты для GitHub Actions
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_NOFILE, (4096, 4096))
    except: pass

    all_candidates = []
    source_stats = {name: 0 for name in SOURCES.keys()}

    print("--- Сбор данных по источникам ---")
    for name, url in SOURCES.items():
        content = get_content(url)
        count = 0
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('vless://') and "sni=" in line.lower():
                all_candidates.append((line, name))
                count += 1
        print(f"[{name}]: найдено {count} потенциальных VLESS")

    # Убираем дубликаты, сохраняя привязку к источнику
    unique_candidates = {}
    for cfg, name in all_candidates:
        addr = cfg.split('#')[0].strip()
        if addr not in unique_candidates:
            unique_candidates[addr] = (cfg, name)
    
    candidates_list = list(unique_candidates.values())
    random.shuffle(candidates_list)
    
    # Ограничиваем базу для nonobr
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([c[0] for c in candidates_list[:TOTAL_MAX_CONFS]]))

    print(f"\nЗапуск Proxy GET чекера (цель: {LIMIT_PER_RUN} шт)...")

    working_results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(proxy_get_check, item): item for item in candidates_list}
        
        for future in as_completed(futures):
            res = future.result()
            if res:
                working_results.append(res)
                source_stats[res['source']] += 1
                if len(working_results) % 5 == 0:
                    print(f"Найдено живых: {len(working_results)}/{LIMIT_PER_RUN}")
                
                if len(working_results) >= LIMIT_PER_RUN:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

    # Сортировка по пингу
    working_results.sort(key=lambda x: x['ping'])
    
    print("\n--- ИТОГОВАЯ СТАТИСТИКА (в gotov.txt попали) ---")
    for name, count in source_stats.items():
        if count > 0:
            print(f"  > {name}: {count} шт.")

    # Сохранение файлов
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([r['config'] for r in working_results]))

    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n#profile-title: 🌐 VOwl\n#announce: Не используй на сервисах из Белого Списка\n\n")
        for i, res in enumerate(working_results, 1):
            config = res['config']
            flag = extract_flag(config)
            f.write(f"{config.split('#')[0].strip()}#{flag} №{i} VOwl\n")
            
    print(f"\nВсе файлы обновлены успешно. Всего в подписке: {len(working_results)}")

if __name__ == "__main__":
    main()
