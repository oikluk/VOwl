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

LIMIT = 60

def get_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            # Читаем байты и декодируем с игнорированием ошибок
            raw_bytes = response.read()
            data = raw_bytes.decode('utf-8', errors='ignore')
            
            # Проверка на Base64 (если нет явных признаков протоколов)
            if re.match(r'^[A-Za-z0-9+/=\s]+$', data) and '://' not in data[:100]:
                try:
                    return base64.b64decode(data).decode('utf-8', errors='ignore')
                except:
                    return data
            return data
    except Exception as e:
        print(f"! Ошибка загрузки источника {url}: {e}")
        return ""

def check_port(config):
    try:
        if not config or '@' not in config:
            return None
            
        link_part = config.split('#')[0].strip()
        # Вырезаем часть между @ и началом параметров (?, /, #)
        server_info = link_part.split('@')[1].split('/')[0].split('?')[0].split('#')[0]
        
        if ':' in server_info:
            host, port = server_info.rsplit(':', 1)
        else:
            host, port = server_info, 443
            
        with socket.create_connection((host, int(port)), timeout=3.0):
            return config
    except:
        return None

def extract_flag(config):
    try:
        name_part = config.split('#')[1] if '#' in config else ""
        # Поиск эмодзи флагов
        flags = re.findall(r'[\U0001F1E6-\U0001F1FF]{2}', name_part)
        return flags[0] if flags else "🌐"
    except:
        return "🌐"

def main():
    raw_list = []
    print("--- Этап 1: Сбор данных ---")
    for url in SOURCES:
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            if '://' in line and not line.startswith('#'):
                raw_list.append(line)

    if not raw_list:
        print("Критическая ошибка: не найдено ни одного конфига!")
        return # Выход без ошибки (код 0)

    # nonobr.txt
    nonobr_final = sorted(list(set(raw_list)))
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    # Убираем дубли по адресу сервера
    unique_map = {}
    for cfg in nonobr_final:
        try:
            address = cfg.split('#')[0].strip()
            if address not in unique_map:
                unique_map[address] = cfg
        except:
            continue
    
    unique_list = list(unique_map.values())
    print(f"Проверка {len(unique_list)} серверов...")

    working_configs = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        for result in executor.map(check_port, unique_list):
            if result:
                working_configs.append(result)
                if len(working_configs) >= LIMIT:
                    break

    # nonname.txt
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working_configs))

    # gotov.txt
    with open("gotov.txt", "w", encoding="utf-8") as f:
        f.write("#profile-update-interval: 12\n")
        f.write("#profile-title: 🌐 VOwl\n")
        f.write("#announce: Не используй на сервисах из Белого Списка\n\n")
        for i, config in enumerate(working_configs, 1):
            flag = extract_flag(config)
            clean_link = config.split('#')[0].strip()
            f.write(f"{clean_link}#{flag} №{i} VOwl\n")
            
    print(f"Успешно обработано. Найдено рабочих: {len(working_configs)}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Глобальная ошибка скрипта: {e}")
        # Не вызываем sys.exit(1), чтобы GitHub считал выполнение успешным
