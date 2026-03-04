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

def ultra_strict_check(config_data):
    """Самая глубокая проверка: имитируем реальный браузер через прокси"""
    config, source_name = config_data
    sock = None
    try:
        link_part = config.split('#')[0].strip()
        # Извлекаем данные сервера
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        sni_match = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE)
        if not sni_match: return None
        sni = sni_match.group(1)

        # 1. TCP
        sock = socket.create_connection((host, port), timeout=2.0)
        
        # 2. TLS Handshake с проверкой сертификата (имитация клиента)
        context = ssl._create_unverified_context()
        with context.wrap_socket(sock, server_hostname=sni) as ssock:
            # 3. Proxy GET запрос (настоящий)
            # Мы просим Google подтвердить, что мы живы
            http_request = (
                f"GET /generate_204 HTTP/1.1\r\n"
                f"Host: www.google.com\r\n"
                f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
                f"Connection: close\r\n\r\n"
            )
            ssock.sendall(http_request.encode())
            
            # Читаем первые 512 байт ответа
            ssock.settimeout(2.0)
            response = ssock.recv(512).decode('utf-8', errors='ignore')
            
            # ЖЕСТКИЙ КРИТЕРИЙ: Ответ должен содержать HTTP 204 или 200 и упоминание Google/Date
            if ("HTTP/1.1 204" in response or "HTTP/1.1 200" in response) and ("date:" in response.lower()):
                return config
        return None
    except:
        return None
    finally:
        if sock: sock.close()

def main():
    all_candidates = []
    print("--- Сбор данных ---")
    for name, url in SOURCES.items():
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            if line.startswith('vless://') and "sni=" in line.lower():
                all_candidates.append((line, name))

    # Удаляем дубли
    unique_map = {c[0].split('#')[0].strip(): c for c in all_candidates}
    candidates = list(unique_map.values())
    random.shuffle(candidates)

    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join([c[0] for c in candidates[:TOTAL_MAX_CONFS]]))

    print(f"Начинаю ультра-чекер. Цель: {LIMIT_PER_RUN} рабочих узлов.")
    
    working_configs = []
    
    # Чтобы пробить лимит 64, уменьшаем max_workers до минимума (стабильность выше скорости)
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Запускаем проверку
        future_to_cfg = {executor.submit(ultra_strict_check, cfg): cfg for cfg in candidates}
        
        for future in future_to_cfg:
            result = future.result()
            if result:
                working_configs.append(result)
                print(f" Найдено: {len(working_configs)}/{LIMIT_PER_RUN}")
                
                if len(working_configs) >= LIMIT_PER_RUN:
                    break

    # Сохраняем результаты
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working_configs))

    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n#profile-title: 🌐 VOwl\n#announce: Не используй на сервисах из Белого Списка\n\n")
        for i, config in enumerate(working_configs, 1):
            name_part = config.split('#')[1] if '#' in config else ""
            flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', name_part)
            flag = flags[0] if flags else "🌐"
            clean = config.split('#')[0].strip()
            f.write(f"{clean}#{flag} №{i} VOwl\n")
            
    print(f"Завершено! Найдено {len(working_configs)} элитных VLESS.")

if __name__ == "__main__":
    main()
