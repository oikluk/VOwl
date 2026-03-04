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

def get_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read().decode('utf-8', errors='ignore')
            # Проверка на Base64
            if re.match(r'^[A-Za-z0-9+/=\s]+$', data) and '://' not in data[:50]:
                return base64.b64decode(data).decode('utf-8', errors='ignore')
            return data
    except Exception as e:
        print(f"Ошибка загрузки {url}: {e}")
        return ""

def check_port(config):
    try:
        # Убираем всё лишнее, оставляем только протокол://...
        link_part = config.split('#')[0].strip()
        # Извлекаем хост и порт
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
    
    print("--- Шаг 1: Сбор и очистка от мусора ---")
    for url in SOURCES:
        content = get_content(url)
        for line in content.splitlines():
            line = line.strip()
            # Пропускаем пустые строки и наши сервисные заголовки, если они попали в базу
            if '://' in line and not line.startswith('#'):
                raw_list.append(line)

    # 1. Файл nonobr.txt (Просто уникальные строки из всех источников)
    nonobr_final = sorted(list(set(raw_list)))
    with open("nonobr.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(nonobr_final))

    # --- Шаг 2: Удаление дубликатов по серверному адресу ---
    unique_map = {}
    for cfg in nonobr_final:
        address = cfg.split('#')[0].strip()
        if address not in unique_map:
            unique_map[address] = cfg
    
    unique_list = list(unique_map.values())

    print(f"Найдено {len(unique_list)} уникальных серверов. Проверка...")

    # --- Шаг 3: Проверка доступности (30 потоков) ---
    with ThreadPoolExecutor(max_workers=30) as executor:
        working_configs = [r for r in executor.map(check_port, unique_list) if r]

    # 2. Файл nonname.txt (Только живые, без переименования)
    with open("nonname.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(working_configs))

    # --- Шаг 4: Финальная сборка gotov.txt ---
    print(f"Сборка готового файла ({len(working_configs)} рабочих)...")
    
    with open("gotov.txt", "w", encoding="utf-8") as f:
        # Сначала пишем техническую часть
        f.write("#profile-update-interval: 12\n")
        f.write("#profile-title: 🌐 VOwl\n")
        f.write("#announce: Не используй на сервисах из Белого Списка\n\n")
        
        # Затем пишем обработанные конфиги
        for i, config in enumerate(working_configs, 1):
            flag = extract_flag(config)
            clean_link = config.split('#')[0].strip()
            f.write(f"{clean_link}#{flag} №{i} VOwl\n")

    print("Все файлы обновлены!")

if __name__ == "__main__":
    main()
