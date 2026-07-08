import sys
import os
import subprocess

def check_setup():
    print("Checking Teams Extractor Setup...\n")
    
    # 1. Check Python
    print(f"[OK] Python installed: {sys.version.split(' ')[0]}")
    
    # 2. Check Virtual Env
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("[OK] Virtual environment active.")
    else:
        print("[WARNING] Not running inside a virtual environment. It is recommended to use venv.")

    # 3. Check Required Packages
    required_packages = ["pyautogui", "pytesseract", "PIL", "PySide6", "pyperclip", "imagehash", "cv2", "numpy", "keyboard"]
    missing = []
    for pkg in required_packages:
        try:
            if pkg == "PIL":
                import PIL
            else:
                __import__(pkg)
            print(f"[OK] {pkg} is installed.")
        except ImportError:
            print(f"[ERROR] {pkg} is missing!")
            missing.append(pkg)
            
    if missing:
        print(f"\nPlease run: pip install {' '.join(['Pillow' if m=='PIL' else m for m in missing])}")
        
    # 4. Check Tesseract
    try:
        import pytesseract
        # Default tesseract installation path on Windows
        tesseract_cmd_global = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        tesseract_cmd_local = r'C:\Users\User\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
        
        if os.path.exists(tesseract_cmd_global):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_global
        elif os.path.exists(tesseract_cmd_local):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_local
        version = pytesseract.get_tesseract_version()
        print(f"[OK] Tesseract OCR installed: v{version}")
    except Exception as e:
        print("[ERROR] Tesseract OCR is not installed or not found in PATH/default location.")
        print("Please download and install from: https://github.com/UB-Mannheim/tesseract/wiki")
        
    # 5. Check Output Folder
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"[OK] Created output folder: {output_dir}")
        except Exception as e:
            print(f"[ERROR] Could not create output folder: {e}")
    else:
        if os.access(output_dir, os.W_OK):
            print(f"[OK] Output folder exists and is writable: {output_dir}")
        else:
            print(f"[ERROR] Output folder is not writable: {output_dir}")

if __name__ == "__main__":
    check_setup()
    input("\nPress Enter to exit...")
