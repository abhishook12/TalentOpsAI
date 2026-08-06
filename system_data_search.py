import os
import glob

def find_data_files():
    base_dir = r"C:\TalentOpsAI"
    extensions = ('**/*.json', '**/*.xlsx', '**/*.db', '**/*.sqlite', '**/*.csv')
    files = []
    
    for ext in extensions:
        files.extend(glob.glob(os.path.join(base_dir, ext), recursive=True))

    results = []
    for f in files:
        if any(skip in f.lower() for skip in ['node_modules', '.git', '.venv', '__pycache__', 'package-lock.json', 'package.json']):
            continue
        try:
            size_mb = os.path.getsize(f) / (1024 * 1024)
            if size_mb > 0.01: # Skip tiny files under 10KB
                results.append((f, size_mb))
        except Exception:
            pass

    results.sort(key=lambda x: x[1], reverse=True)
    
    print("Found potential data files:")
    for f, size in results[:40]:
        print(f"{size:8.2f} MB | {f}")

if __name__ == '__main__':
    find_data_files()
