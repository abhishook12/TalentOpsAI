#!/usr/bin/env python
"""Codebase Search for ETL Component References - TalentOpsAI"""
import os, glob

def search_terms():
    terms = ['etl', 'bulk_enhancer', 'ingest', 'pipeline']
    print("SEARCHING FOR ETL REFERENCES...")
    for root_dir in ['c:/TalentOpsAI/backend', 'c:/TalentOpsAI/frontend/src', 'c:/TalentOpsAI/background_workers']:
        for path, dirs, files in os.walk(root_dir):
            if '__pycache__' in path or 'node_modules' in path or '.git' in path:
                continue
            for f in files:
                if not f.endswith(('.py', '.jsx', '.js', '.html')):
                    continue
                full_p = os.path.join(path, f)
                try:
                    with open(full_p, 'r', encoding='utf-8', errors='ignore') as fp:
                        lines = fp.readlines()
                        for idx, line in enumerate(lines, 1):
                            if any(t in line.lower() for t in ['etl', 'extract', 'transform', 'ingest']):
                                if 'select' in line.lower() or 'update' in line.lower() or 'import os' in line:
                                    continue
                                print(f"{full_p}:{idx} -> {line.strip()[:100]}")
                except Exception:
                    pass

if __name__ == "__main__":
    search_terms()
