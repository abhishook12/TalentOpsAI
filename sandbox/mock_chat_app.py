"""
mock_chat_app.py — Standalone Desktop GUI Chat Application for Background Automation Practice
=============================================================================================
A native Windows Tkinter chat app replicating the exact layout, conversation switcher,
input field, and Send button mechanics of modern desktop messengers (Vitel, Teams, Slack).
Runs completely isolated to practice zero-disturbance background automation.
"""

import tkinter as tk
from tkinter import ttk
import json
import time
import os
import sys

STATE_FILE = r"c:\TalentOpsAI\sandbox\mock_chat_state.json"

class MockChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SandboxChatApp - Practice Environment")
        self.root.geometry("850x600+100+100")
        
        # 20 target contacts
        self.contacts = [
            "+1 (972) 419-1616",
            "+1 (972) 419-1607",
            "+1 (972) 419-1615",
            "+1 (516) 510-6582",
            "+1 (414) 217-6217",
            "+1 (262) 409-1002",
            "+1 (145) 674-5646",
            "+1 (801) 870-6007",
            "+1 (262) 567-8166",
            "+1 (414) 773-0679",
            "+1 (646) 421-2155",
            "+1 (717) 628-9614",
            "+1 (860) 331-9007",
            "+1 (860) 404-8883",
            "+1 (860) 678-1300",
            "+1 (860) 439-5069",
            "+1 (724) 584-3567",
            "+1 (817) 845-1837",
            "+1 (972) 419-1629",
            "+1 (774) 328-1700",
        ]
        
        self.active_chat_idx = 0
        self.chat_histories = {num: [] for num in self.contacts}
        self.received_logs = []
        
        self._build_ui()
        self._save_state()

    def _build_ui(self):
        # Main split container
        self.paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left pane: Chat List
        self.left_frame = tk.Frame(self.paned, width=280, bg="#1e1e2d")
        self.paned.add(self.left_frame)

        tk.Label(self.left_frame, text="Conversations (Top 20)", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#1e1e2d", pady=10).pack(fill=tk.X)

        self.chat_list_canvas = tk.Canvas(self.left_frame, bg="#1e1e2d", highlightthickness=0)
        self.chat_scroll = tk.Scrollbar(self.left_frame, orient=tk.VERTICAL, command=self.chat_list_canvas.yview)
        self.chat_items_frame = tk.Frame(self.chat_list_canvas, bg="#1e1e2d")

        self.chat_items_frame.bind("<Configure>", lambda e: self.chat_list_canvas.configure(scrollregion=self.chat_list_canvas.bbox("all")))
        self.chat_list_canvas.create_window((0, 0), window=self.chat_items_frame, anchor="nw")
        self.chat_list_canvas.configure(yscrollcommand=self.chat_scroll.set)

        self.chat_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.chat_buttons = []
        for idx, num in enumerate(self.contacts):
            btn = tk.Button(
                self.chat_items_frame,
                text=f"Chat {idx+1}: {num}",
                font=("Segoe UI", 10),
                fg="#e0e0e0",
                bg="#2a2a3e" if idx != 0 else "#3b82f6",
                activebackground="#60a5fa",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                anchor="w",
                padx=10,
                pady=6,
                command=lambda i=idx: self.select_chat(i)
            )
            btn.pack(fill=tk.X, padx=4, pady=2)
            self.chat_buttons.append(btn)

        # Right pane: Active Conversation & Input Box
        self.right_frame = tk.Frame(self.paned, bg="#111827")
        self.paned.add(self.right_frame)

        # Header
        self.header_label = tk.Label(
            self.right_frame,
            text=f"Active Chat: {self.contacts[0]}",
            font=("Segoe UI", 12, "bold"),
            fg="#60a5fa",
            bg="#1f2937",
            pady=10,
            padx=15,
            anchor="w"
        )
        self.header_label.pack(fill=tk.X)

        # Message History Display
        self.history_text = tk.Text(
            self.right_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg="#111827",
            fg="#f3f4f6",
            relief=tk.FLAT,
            state=tk.DISABLED,
            padx=15,
            pady=10
        )
        self.history_text.pack(fill=tk.BOTH, expand=True)

        # Input Area Container
        self.input_container = tk.Frame(self.right_frame, bg="#1f2937", padx=10, pady=10)
        self.input_container.pack(fill=tk.X, side=tk.BOTTOM)

        # Text Input Box (myInput)
        self.msg_input = tk.Entry(
            self.input_container,
            font=("Segoe UI", 11),
            bg="#374151",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT
        )
        self.msg_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 10))
        self.msg_input.bind("<Return>", lambda e: self.send_message())

        # Send Button
        self.send_btn = tk.Button(
            self.input_container,
            text="Send",
            font=("Segoe UI", 10, "bold"),
            bg="#3b82f6",
            fg="#ffffff",
            activebackground="#2563eb",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=6,
            command=self.send_message
        )
        self.send_btn.pack(side=tk.RIGHT)

    def select_chat(self, idx):
        self.active_chat_idx = idx
        current_num = self.contacts[idx]
        self.header_label.config(text=f"Active Chat: {current_num}")

        # Update button highlights
        for i, b in enumerate(self.chat_buttons):
            b.config(bg="#3b82f6" if i == idx else "#2a2a3e")

        # Refresh message history
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        for msg in self.chat_histories[current_num]:
            self.history_text.insert(tk.END, f"[{msg['time']}] Sent:\n{msg['text']}\n\n")
        self.history_text.config(state=tk.DISABLED)
        self._save_state()

    def send_message(self):
        text = self.msg_input.get()
        if not text:
            return
        
        current_num = self.contacts[self.active_chat_idx]
        timestamp = time.strftime("%H:%M:%S")
        entry = {
            "chat_index": self.active_chat_idx + 1,
            "target": current_num,
            "time": timestamp,
            "text": text,
            "length": len(text)
        }
        self.chat_histories[current_num].append(entry)
        self.received_logs.append(entry)

        # Clear input box
        self.msg_input.delete(0, tk.END)

        # Refresh display
        self.history_text.config(state=tk.NORMAL)
        self.history_text.insert(tk.END, f"[{timestamp}] Sent:\n{text}\n\n")
        self.history_text.see(tk.END)
        self.history_text.config(state=tk.DISABLED)

        self._save_state()

    def _save_state(self):
        data = {
            "window_title": "SandboxChatApp - Practice Environment",
            "active_chat_index": self.active_chat_idx + 1,
            "active_chat_target": self.contacts[self.active_chat_idx],
            "total_sent": len(self.received_logs),
            "chat_histories": self.chat_histories,
            "received_logs": self.received_logs,
            "last_updated": time.time()
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    sys.path.insert(0, r"c:\TalentOpsAI")
    from scout_desktop.core.window_tracker import ensure_interactive_desktop, user32
    ensure_interactive_desktop()
    
    root = tk.Tk()
    app = MockChatApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
