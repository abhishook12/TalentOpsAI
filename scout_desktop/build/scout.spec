# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

root_dir = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(root_dir, 'assets'), 'scout_desktop/assets'),
    (os.path.join(root_dir, 'core', 'ocr_helper.ps1'), 'scout_desktop/core'),
    (os.path.join(root_dir, 'config.json'), 'scout_desktop'),
]

hiddenimports = [
    'scout_desktop',
    'scout_desktop.app',
    'scout_desktop.core',
    'scout_desktop.core.window_tracker',
    'scout_desktop.core.browser_tracker',
    'scout_desktop.core.visual_sampler',
    'scout_desktop.core.evidence_store',
    'scout_desktop.core.ocr_engine',
    'scout_desktop.core.intelligence_levels',
    'scout_desktop.core.context_memory',
    'scout_desktop.extractor',
    'scout_desktop.extractor.entity_extractor',
    'scout_desktop.extractor.models',
    'scout_desktop.extractor.patterns',
    'scout_desktop.extractor.grounding_gate',
    'scout_desktop.extractor.identity_resolver',
    'scout_desktop.extractor.timeline_parser',
    'scout_desktop.extractor.semantic_factorizer',
    'scout_desktop.sync',
    'scout_desktop.sync.local_queue',
    'scout_desktop.sync.backend_client',
    'scout_desktop.sync.batch_processor',
    'scout_desktop.ui',
    'scout_desktop.ui.tray',
    'scout_desktop.ui.main_window',
    'scout_desktop.ui.edge_handle',
    'scout_desktop.ui.diagnostics_window',
    'scout_desktop.ui.settings_window',
    'scout_desktop.ui.activation_window',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'comtypes',
    'comtypes.client',
    'PIL',
    'PIL.Image',
    'PIL.ImageGrab',
    'requests',
    'sqlite3',
    'urllib.parse',
    'gzip',
]

a = Analysis(
    [os.path.join(root_dir, 'entry.py')],
    pathex=[os.path.dirname(root_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TalentOpsScout',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # CRITICAL: Suppresses the black terminal/console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root_dir, 'assets', 'logo.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TalentOpsScout',
)
