"""
Скрипт для сборки проекта в standalone-исполняемый файл через PyInstaller.

Использование:
    python build.py

Требования:
    pip install pyinstaller
"""

import subprocess
import sys
import platform
from pathlib import Path


def build():
    spec_content = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan.on',
        'fastapi',
        'fastapi.staticfiles',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenAInterface',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

    spec_path = Path("OpenAInterface.spec")
    spec_path.write_text(spec_content, encoding="utf-8")

    print("Сборка проекта...")
    print(f"Платформа: {platform.system()}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "OpenAInterface.spec",
        "--clean",
        "--noconfirm",
    ]

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print("\n✅ Сборка завершена успешно!")
        print(f"Исполняемый файл: dist/OpenAInterface")
    else:
        print("\n❌ Ошибка сборки")
        sys.exit(1)


if __name__ == "__main__":
    build()