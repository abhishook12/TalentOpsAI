import os
import winshell
from win32com.client import Dispatch

def create_desktop_shortcut():
    desktop = winshell.desktop()
    path = os.path.join(desktop, "Teams Extractor.lnk")
    
    target = os.path.abspath(os.path.join(os.path.dirname(__file__), "run_extractor.bat"))
    wDir = os.path.abspath(os.path.dirname(__file__))
    icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe"))
    
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = wDir
    shortcut.IconLocation = icon
    shortcut.save()
    print(f"Created shortcut at: {path}")

if __name__ == "__main__":
    create_desktop_shortcut()
