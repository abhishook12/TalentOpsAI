# -*- mode: python ; coding: utf-8 -*-
"""
scout.spec — PyInstaller Specification for TalentOps Scout Dual-Binary Distribution.

Produces:
1. TalentOpsScout.exe: Main windowless GUI companion (IMAGE_SUBSYSTEM_WINDOWS_GUI, console=False).
2. TalentOpsScoutUpdater.exe: Detached out-of-process updater helper binary (console=False).

Both binaries are collected into the distribution folder without black console windows.
"""

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
    'scout_desktop.core.paths',
    'scout_desktop.core.security',
    'scout_desktop.core.updater',
    'scout_desktop.core.updater_state',
    'scout_desktop.core.migrations',
    'scout_desktop.core.autostart',
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
    'cryptography',
    'cryptography.hazmat.primitives.asymmetric.ed25519',
]

# ── 1. Main Scout Companion Binary ───────────────────────────────────────────
a_scout = Analysis(
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

pyz_scout = PYZ(a_scout.pure, a_scout.zipped_data, cipher=block_cipher)

exe_scout = EXE(
    pyz_scout,
    a_scout.scripts,
    [],
    exclude_binaries=True,
    name='TalentOpsScout',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Suppresses black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root_dir, 'assets', 'logo.ico'),
)

# ── 2. Standalone Updater Helper Binary ──────────────────────────────────────
a_updater = Analysis(
    [os.path.join(root_dir, 'updater', 'updater_helper.py')],
    pathex=[os.path.dirname(root_dir)],
    binaries=[],
    datas=[],
    hiddenimports=['requests', 'json', 'shutil', 'subprocess', 'argparse', 'hashlib', 'sqlite3'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'PySide6'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_updater = PYZ(a_updater.pure, a_updater.zipped_data, cipher=block_cipher)

exe_updater = EXE(
    pyz_updater,
    a_updater.scripts,
    [],
    exclude_binaries=True,
    name='TalentOpsScoutUpdater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Silent background helper
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(root_dir, 'assets', 'logo.ico'),
)

# ── 3. Combined Distribution Collector ───────────────────────────────────────
coll = COLLECT(
    exe_scout,
    a_scout.binaries,
    a_scout.zipfiles,
    a_scout.datas,
    exe_updater,
    a_updater.binaries,
    a_updater.zipfiles,
    a_updater.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TalentOpsScout',
)
