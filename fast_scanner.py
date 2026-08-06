import os

def scan_dir(path):
    results = []
    skip_dirs = {'node_modules', '.git', '.venv', '__pycache__', 'dist', 'build'}
    try:
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_dir():
                    if entry.name not in skip_dirs:
                        results.extend(scan_dir(entry.path))
                elif entry.is_file():
                    ext = os.path.splitext(entry.name)[1].lower()
                    if ext in {'.json', '.xlsx', '.db', '.sqlite'}:
                        try:
                            size_mb = entry.stat().st_size / (1024 * 1024)
                            if size_mb > 0.1: # > 100KB
                                results.append((entry.path, size_mb))
                        except Exception:
                            pass
    except PermissionError:
        pass
    return results

files = scan_dir(r'C:\TalentOpsAI')
files.sort(key=lambda x: x[1], reverse=True)
for f, size in files[:40]:
    print(f"{size:8.2f} MB | {f}")
