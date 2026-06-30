"""
SSH-менеджер для управления туннелями.
Использует системный OpenSSH (есть в Windows 10+, macOS, Linux).
"""

import subprocess
import os
import json
import sys
import shlex
import platform
from pathlib import Path
from typing import Optional


class SSHManager:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        self._process: Optional[subprocess.Popen] = None
        self._active_preset_id: Optional[str] = None
        self._presets = self._load_presets()

    def _load_presets(self) -> list:
        """Загрузить пресеты из JSON-файла."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("presets", [])
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def get_presets(self) -> list:
        """Возвратить список доступных пресетов."""
        return self._presets

    def save_presets(self, presets: list):
        """Сохранить список пресетов в JSON-файл."""
        self._presets = presets
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"presets": presets}, f, ensure_ascii=False, indent=2)

    def get_ssh_command(self) -> str:
        """Определить путь к ssh в зависимости от ОС."""
        if platform.system() == "Windows":
            # OpenSSH есть в Windows 10+ по умолчанию
            ssh_paths = [
                "ssh",
                "C:\\Windows\\System32\\OpenSSH\\ssh.exe",
                "C:\\Program Files\\OpenSSH\\ssh.exe",
            ]
            for path in ssh_paths:
                if self._command_exists(path):
                    return path
            return "ssh"
        return "ssh"

    def start_tunnel(self, preset_id: str) -> bool:
        """
        Запустить SSH-туннель по пресету.
        Возвращает True при успехе, False при ошибке.
        """
        preset = self._find_preset(preset_id)
        if not preset:
            print(f"Пресет '{preset_id}' не найден")
            return False

        # Если туннель уже запущен — перезапустить
        if self._process is not None:
            self.stop_tunnel()

        ssh_cmd = self.get_ssh_command()
        command = preset["command"]

        # Автоматически добавляем -N (только форвардинг, без удалённой команды)
        args = shlex.split(command)
        if "-N" not in args:
            args.insert(1, "-N")
        command = " ".join(args)

        print(f"Запуск туннеля: {preset['name']}")
        print(f"Команда: {command}")

        try:
            # Разбираем строку команды на аргументы (безопасно, обрабатывает кавычки)
            cmd_args = shlex.split(command)

            self._process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
            )

            # Проверяем, что процесс запущен
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                print(f"Ошибка запуска SSH: {stderr}")
                self._process = None
                return False

            self._active_preset_id = preset_id
            print(f"Туннель запущен (PID: {self._process.pid})")
            return True

        except Exception as e:
            print(f"Ошибка при запуске туннеля: {e}")
            self._process = None
            return False

    def stop_tunnel(self):
        """Остановить запущенный SSH-туннель."""
        if self._process is not None:
            print(f"Остановка туннеля (PID: {self._process.pid})...")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
            except Exception as e:
                print(f"Ошибка при остановке: {e}")
            finally:
                self._process = None
                self._active_preset_id = None
                print("Туннель остановлен")

    def is_running(self) -> bool:
        """Проверить, запущен ли туннель."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def get_active_preset_id(self) -> Optional[str]:
        """Возвратить ID активного пресета."""
        return self._active_preset_id

    def _find_preset(self, preset_id: str) -> Optional[dict]:
        """Найти пресет по ID."""
        for preset in self._presets:
            if preset["id"] == preset_id:
                return preset
        return None

    def _command_exists(self, command: str) -> bool:
        """Проверить, существует ли команда."""
        if platform.system() == "Windows":
            return os.path.isfile(command)
        return subprocess.run(
            ["which", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0

    def cleanup(self):
        """Очистить ресурсы."""
        self.stop_tunnel()