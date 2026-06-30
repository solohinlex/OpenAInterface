# OpenAInterface

Локальный интерфейс для работы с нейросетью на кластере.

## Для пользователей

### Быстрый старт

1. Скачайте последнюю версию с [Releases](https://github.com/solohinlex/OpenAInterface/releases)
2. Запустите `OpenAInterface.exe` (Windows) или `OpenAInterface` (Linux/macOS)
3. Браузер откроется автоматически

### Настройка подключения

1. В боковой панели выберите нужный SSH-пресет
2. Нажмите **Подключить**
3. Индикатор станет зелёным — можно работать

### Возможности

- **Чат с нейросетью** — отправляйте сообщения и получайте ответы в реальном времени
- **История диалогов** — все разговоры сохраняются локально
- **Профили** — создавайте собственные системные промпты для разных задач
- **SSH-туннели** — безопасное подключение к кластеру в один клик

### Где хранятся данные

| ОС | Путь |
|----|------|
| Windows | `C:\Users\<Имя>\AppData\Local\OpenAInterface\` |
| macOS | `~/Library/Application Support/OpenAInterface/` |
| Linux | `~/.openainterface/` |

---

## Для разработчиков

### Требования

- Python 3.10+
- OpenSSH (встроен в Windows 10+, macOS, Linux)

### Установка

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### Запуск

```bash
python app.py
```

Сервер запустится на `http://localhost:8080` и откроет браузер.

### Настройка SSH-пресетов

Редактируйте `config/ssh_presets.json`:

```json
{
  "presets": [
    {
      "id": "main",
      "name": "Кластер (основной)",
      "command": "ssh -L 8080:localhost:8080 user@main-host -p 22",
      "remote_api": "http://localhost:8080/v1/chat/completions",
      "tunnel_port": 8080
    }
  ]
}
```

### Сборка standalone-приложения

```bash
pip install pyinstaller
python build.py
```

Результат: `dist/OpenAInterface` — исполняемый файл без необходимости установки Python.

### Структура проекта

```
OpenAInterface/
├── app.py                  # FastAPI сервер
├── ssh_manager.py          # Управление SSH-туннелями
├── database.py             # SQLite база данных
├── build.py                # Скрипт сборки
├── requirements.txt
├── config/
│   ├── ssh_presets.json    # SSH пресеты
│   └── profiles.json       # Профили/промпты
├── static/
│   └── index.html          # Веб-интерфейс (Vue.js)
└── README.md
```

## Лицензия

MIT