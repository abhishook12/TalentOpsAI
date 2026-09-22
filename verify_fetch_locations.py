import os
import sys
import requests

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=== VERIFICATION: WHERE TO FETCH DESKTOP SCOUT UPDATES ===")

# CHECK 1: Direct Supabase Cloud Installer URL
installer_url = "https://qpetzpxmuofuepvrqedk.supabase.co/storage/v1/object/public/data-assets/TalentOpsScoutSetup.exe"
print("\n[CHECK 1] Remote CDN Installer Endpoint:")
print(f"URL: {installer_url}")
res = requests.head(installer_url, timeout=10)
print(f"Status: {res.status_code}")
content_len = int(res.headers.get("Content-Length", 0))
print(f"Size: {content_len:,} bytes (Expected: 50,084,798)")
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert content_len == 50084798, f"Unexpected installer size: {content_len}"

# Verify MZ executable header
res_chunk = requests.get(installer_url, headers={"Range": "bytes=0-512"}, timeout=10)
assert res_chunk.content.startswith(b"MZ"), "Missing Windows PE MZ header"
print("✓ Windows Portable Executable (PE/MZ) binary header verified.")
print(">>> CHECK 1 PASSED: Remote CDN installer is ready and directly downloadable.")

# CHECK 2: Live Web Download Hub
portal_url = "https://talent-ops-ai.vercel.app/download-scout"
print(f"\n[CHECK 2] Web Scout Download Portal:")
print(f"URL: {portal_url}")
res_portal = requests.get(portal_url, timeout=10)
print(f"Status: {res_portal.status_code}")
assert res_portal.status_code == 200, f"Expected 200, got {res_portal.status_code}"
assert '<div id="root">' in res_portal.text, "Missing SPA root container in portal HTML"

# Check Vercel API Manifest
manifest_res = requests.get("https://talent-ops-ai.vercel.app/api/scout/updates/manifest?channel=stable", timeout=10)
assert manifest_res.status_code == 200, f"Manifest API returned {manifest_res.status_code}"
m_data = manifest_res.json()
assert "TalentOpsScoutSetup.exe" in m_data.get("download_url", "")
print(f"✓ Vercel Gateway manifest served: Version {m_data.get('version')}")
print(f"✓ Installer download URL confirmed: {m_data.get('download_url')}")
print("✓ Web download portal returned HTTP 200 and serves Scout setup.")
print(">>> CHECK 2 PASSED: Web portal is live and accessible to users.")

# CHECK 3: Local Disk Binaries & Source Launcher
local_installer = "c:/TalentOpsAI/scout_desktop/dist/TalentOpsScoutSetup.exe"
print(f"\n[CHECK 3] Local Windows File System Path:")
print(f"File: {local_installer}")
assert os.path.exists(local_installer), "Local installer binary missing"
local_size = os.path.getsize(local_installer)
print(f"Local Size: {local_size:,} bytes")
assert local_size == 50084798, f"Local size mismatch: {local_size}"

from scout_desktop.version import __version__
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
from scout_desktop.ui.components import TopBar
top_bar = TopBar()
assert hasattr(top_bar, "btn_version_chip"), "TopBar missing btn_version_chip"
assert hasattr(top_bar, "btn_notifications"), "TopBar missing btn_notifications"
print(f"✓ Source version: v{__version__}")
print(f"✓ TopBar version button: '{top_bar.btn_version_chip.text()}'")
print(f"✓ TopBar notification bell: '{top_bar.btn_notifications.text()}'")
print(">>> CHECK 3 PASSED: Local files & desktop UI components verified.")

print("\n========================================================")
print("ALL 3 FETCH VERIFICATION CHECKS PASSED SUCCESSFULLY!")
print("========================================================")
