"""
OpenAInterface — локальный интерфейс для работы с нейросетью на Spark.
FastAPI сервер с SSH-туннелями, историей диалогов и профилями.
"""

import os
import sys
import json
import webbrowser
import platform
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from ssh_manager import SSHManager
from database import Database

# --- Пути ---

# Определяем, запущено ли из PyInstaller
if getattr(sys, "frozen", False):
    # Запущено как собранный exe
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

# Папка для данных пользователя
if platform.system() == "Windows":
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Local")) / "OpenAInterface"
elif platform.system() == "Darwin":
    DATA_DIR = Path.home() / "Library" / "Application Support" / "OpenAInterface"
else:
    DATA_DIR = Path.home() / ".openainterface"

CONFIG_DIR = DATA_DIR / "config"
DATA_SUBDIR = DATA_DIR / "data"
STATIC_DIR = APP_DIR / "static"

# Создаём директории
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_SUBDIR.mkdir(parents=True, exist_ok=True)

# Пути к файлам
SSH_PRESETS_PATH = CONFIG_DIR / "ssh_presets.json"
PROFILES_PATH = CONFIG_DIR / "profiles.json"
DB_PATH = DATA_SUBDIR / "conversations.db"

# Копируем дефолтные конфиги, если их нет
_default_configs = APP_DIR / "config"
if not SSH_PRESETS_PATH.exists() and (_default_configs / "ssh_presets.json").exists():
    SSH_PRESETS_PATH.write_bytes((_default_configs / "ssh_presets.json").read_bytes())
if not PROFILES_PATH.exists() and (_default_configs / "profiles.json").exists():
    PROFILES_PATH.write_bytes((_default_configs / "profiles.json").read_bytes())

# --- Инициализация ---

app = FastAPI(title="OpenAInterface")
ssh_manager = SSHManager(str(SSH_PRESETS_PATH))
db = Database(str(DB_PATH))


def get_profiles() -> list:
    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("profiles", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# --- Модели данных ---

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    profile_id: Optional[str] = "default"


class PresetStatus(BaseModel):
    preset_id: str
    running: bool


class SSHStartRequest(BaseModel):
    preset_id: str


# --- API ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница — веб-интерфейс."""
    try:
        with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse("<h1>OpenAInterface</h1><p>Статические файлы не найдены.</p>", status_code=500)


@app.get("/api/presets")
async def get_presets():
    """Получить список SSH-пресетов."""
    return {"presets": ssh_manager.get_presets()}


@app.post("/api/ssh/start")
async def start_ssh(request: SSHStartRequest):
    """Запустить SSH-туннель."""
    success = ssh_manager.start_tunnel(request.preset_id)
    if not success:
        raise HTTPException(status_code=400, detail="Не удалось запустить туннель")
    return {"status": "started", "preset_id": request.preset_id}


@app.post("/api/ssh/stop")
async def stop_ssh():
    """Остановить SSH-туннель."""
    ssh_manager.stop_tunnel()
    return {"status": "stopped"}


@app.get("/api/ssh/status")
async def ssh_status():
    """Статус SSH-туннеля."""
    return {
        "running": ssh_manager.is_running(),
        "presets": ssh_manager.get_presets(),
        "active_preset": ssh_manager.get_active_preset_id(),
    }


# --- CRUD для SSH-пресетов ---

@app.get("/api/ssh/presets")
async def get_ssh_presets():
    """Получить все SSH-пресеты."""
    return {"presets": ssh_manager.get_presets()}


@app.post("/api/ssh/presets")
async def create_ssh_preset(preset: dict):
    """Создать новый SSH-пресет."""
    presets = ssh_manager.get_presets()

    # Проверка уникальности id
    if any(p["id"] == preset["id"] for p in presets):
        raise HTTPException(status_code=400, detail="Пресет с таким ID уже существует")

    # Генерация ID, если нет
    if not preset.get("id"):
        preset["id"] = "preset_" + str(int(__import__("time").time() * 1000))

    presets.append(preset)
    ssh_manager.save_presets(presets)
    return preset


@app.put("/api/ssh/presets/{preset_id}")
async def update_ssh_preset(preset_id: str, preset: dict):
    """Обновить SSH-пресет."""
    presets = ssh_manager.get_presets()
    preset["id"] = preset_id  # не меняем ID

    for i, p in enumerate(presets):
        if p["id"] == preset_id:
            presets[i] = preset
            ssh_manager.save_presets(presets)
            return preset

    raise HTTPException(status_code=404, detail="Пресет не найден")


@app.delete("/api/ssh/presets/{preset_id}")
async def delete_ssh_preset(preset_id: str):
    """Удалить SSH-пресет."""
    presets = ssh_manager.get_presets()
    presets = [p for p in presets if p["id"] != preset_id]
    ssh_manager.save_presets(presets)
    return {"status": "deleted"}


@app.get("/api/profiles")
async def get_api_profiles():
    """Получить список профилей."""
    return {"profiles": get_profiles()}


@app.post("/api/profiles")
async def save_profile(profile: dict):
    """Сохранить/обновить профиль."""
    profiles = get_profiles()
    existing = next((p for p in profiles if p["id"] == profile["id"]), None)
    if existing:
        profiles[profiles.index(existing)] = profile
    else:
        profiles.append(profile)
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump({"profiles": profiles}, f, ensure_ascii=False, indent=2)
    return profile


@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Удалить профиль."""
    profiles = get_profiles()
    profiles = [p for p in profiles if p["id"] != profile_id]
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump({"profiles": profiles}, f, ensure_ascii=False, indent=2)
    return {"status": "deleted"}


# --- Диалоги ---

@app.get("/api/conversations")
async def get_conversations():
    """Получить все диалоги."""
    return {"conversations": db.get_conversations()}


@app.post("/api/conversations")
async def create_conversation(profile_id: Optional[str] = None):
    """Создать новый диалог."""
    conv_id = db.create_conversation(profile_id=profile_id)
    return {"conversation_id": conv_id}


@app.get("/api/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """Получить диалог."""
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Диалог не найден")
    messages = db.get_messages(conv_id)
    return {"conversation": conv, "messages": messages}


@app.put("/api/conversations/{conv_id}/title")
async def update_title(conv_id: str, title: str):
    """Обновить название диалога."""
    db.update_conversation_title(conv_id, title)
    return {"status": "updated"}


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Удалить диалог."""
    db.delete_conversation(conv_id)
    return {"status": "deleted"}


# --- Чат ---

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Отправить сообщение и получить ответ от нейросети.
    Поддерживает SSE для потокового ответа.
    """
    # Получаем пресет для определения API-URL
    presets = ssh_manager.get_presets()
    if not presets:
        raise HTTPException(status_code=503, detail="Нет доступных SSH-пресетов")

    # Берём активный пресет (или первый)
    active_id = ssh_manager.get_active_preset_id()
    preset = next((p for p in presets if p["id"] == active_id), presets[0])
    api_url = preset.get("remote_api", "http://localhost:8080/v1/chat/completions")

    # Получаем профиль
    profiles = get_profiles()
    profile = next((p for p in profiles if p["id"] == request.profile_id), None)
    system_prompt = profile["system_prompt"] if profile else "Ты полезный ассистент."

    # Создаём диалог, если нет
    new_conversation = False
    if not request.conversation_id:
        request.conversation_id = db.create_conversation(
            title=request.message[:50],
            profile_id=request.profile_id,
        )
        new_conversation = True

    # Сохраняем сообщение пользователя
    db.add_message(request.conversation_id, "user", request.message)

    # Формируем историю сообщений
    history = db.get_messages(request.conversation_id)
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})

    # Добавляем системный промпт
    messages.insert(0, {"role": "system", "content": system_prompt})

    def event_generator():
        import urllib.request
        import urllib.error

        data = json.dumps({"messages": messages, "stream": True}).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        assistant_content = ""
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                assistant_content += content
                                yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError:
                            pass
            
            # Save the assistant's response to the database
            if assistant_content:
                db.add_message(request.conversation_id, "assistant", assistant_content)
                
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            yield f"data: {json.dumps({'error': error_msg})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


# --- Монтируем статические файлы ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Точка входа ---

def main():
    import uvicorn

    port = 8080
    print("=" * 50)
    print("  OpenAInterface")
    print("=" * 50)
    print(f"  Данные: {DATA_DIR}")
    print(f"  Сервер: http://localhost:{port}")
    print("=" * 50)
    print()

    # Открываем браузер
    webbrowser.open(f"http://localhost:{port}")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()