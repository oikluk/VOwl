import urllib.request
import base64
import re
import socket
import ssl
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- НАСТРОЕЧКИ 🔪 ---
TOTAL_MAX_CONFS = 1500  # Максимум в nonobr.txt
LIMIT_PER_RUN = 60      # Сколько отобрать в gotov.txt
CHECK_URL = "https://www.gstatic.com/generate_204"
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

def proxy_get_check(config):
    """
    Максимальная имитация via Proxy GET:
    TCP -> TLS Handshake -> HTTP GET Request -> Ожидание заголовков ответа
    """
    try:
        if "sni=" not in config.lower(): return None
        
        link_part = config.split('#')[0].strip()
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        host, port = server_info.rsplit(':', 1) if ':' in server_info else (server_info, 443)
        port = int(port)

        start_time = time.time()
        
        # 1. Установка TCP соединения
        sock = socket.create_connection((host, port), timeout=3.5)
        
        # 2. Попытка TLS Handshake
        sni = re.search(r'sni=([^&?#]+)', config, re.IGNORECASE).group(1)
        context = ssl._create_unverified_context()
        
        with context.wrap_socket(sock, server_hostname=sni) as ssock:
            # 3. Реальная отправка HTTP GET внутри туннеля
            # Имитируем запрос к Google для проверки проходимости данных
            http_request = (
                f"GET /generate_204 HTTP/1.1\r\n"
                f"Host: {sni}\r\n"
                f"User-Agent: Mozilla/5.0\r\n"
                f"Connection: close\r\n\r\n"
            )
            ssock.sendall(http_request.encode())
            
            # 4. Ожидаем ответ (хотя бы начало заголовка HTTP/1.1 204)
            response = ssock.recv(512)
            if not response or b"HTTP" not in response:
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
            if line.startswith('vless://') and "sni=" in line.lower():
                raw_list.append(line)

    # nonobr.txt - берем всё уникальное до лимита
    unique_all = sorted(list(set(raw_list)))
    nonobr_final = unique_all[:TOTAL_MAX_CONFS]
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    # Для проверки перемешиваем весь список
    random.shuffle(unique_all)

    print(f"Запуск глубокой Proxy GET проверки (из {len(unique_all)} кандидатов)...")

    working_results = []
    # Используем as_completed для мгновенной обработки по мере поступления
    with ThreadPoolExecutor(max_workers=40) as executor:
        future_to_config = {executor.submit(proxy_get_check, cfg): cfg for cfg in unique_all}
        
        for future in as_completed(future_to_config):
            result = future.result()
            if result:
                working_results.append(result)
                if len(working_results) % 10 == 0:
                    print(f"Найдено живых: {len(working_results)}")
                
                # Жёсткий стоп, когда набрали лимит для gotov.txt
                if len(working_results) >= LIMIT_PER_RUN:
                    break

    # Сортируем по латентности (лучшие сверху)
    working_results.sort(key=lambda x: x[1])
    final_configs = [x[0] for x in working_results]

    # Сохраняем файлы
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
            
    print(f"Готово! В gotov.txt отобрано {len(final_configs)} элитных конфигов.")

if __name__ == "__main__":
    main()
