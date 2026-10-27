import os
import re

files_to_process = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.jsx', '.js', '.tsx', '.ts')):
            files_to_process.append(os.path.join(root, f))

# 1. Tailwind class replacements
tailwind_replacements = [
    # Emerald / Green text
    (r'\btext-emerald-400/90\b', 'text-white/90'),
    (r'\btext-emerald-400\b', 'text-white'),
    (r'\btext-emerald-300\b', 'text-white'),
    (r'\btext-emerald-500\b', 'text-white'),
    (r'\btext-green-400\b', 'text-white'),
    (r'\btext-green-500\b', 'text-white'),
    
    # Emerald / Green backgrounds
    (r'\bbg-emerald-500/10\b', 'bg-white/10'),
    (r'\bbg-emerald-500/15\b', 'bg-white/10'),
    (r'\bbg-emerald-500/20\b', 'bg-white/15'),
    (r'\bbg-green-500/10\b', 'bg-white/10'),
    (r'\bbg-green-500/20\b', 'bg-white/15'),
    (r'\bbg-green-400/10\b', 'bg-white/10'),
    (r'\bbg-emerald-600\b', 'bg-[#e41937] text-white'),
    (r'\bbg-emerald-500\b', 'bg-[#e41937] text-white'),
    (r'\bbg-emerald-400\b', 'bg-white text-black'),
    
    # Emerald / Green borders & rings
    (r'\bborder-emerald-500/20\b', 'border-white/20'),
    (r'\bborder-emerald-500/25\b', 'border-white/25'),
    (r'\bborder-emerald-500/30\b', 'border-white/30'),
    (r'\bborder-emerald-500/40\b', 'border-white/40'),
    (r'\bborder-emerald-500\b', 'border-white/30'),
    (r'\bborder-green-500/30\b', 'border-white/30'),
    (r'\bborder-emerald-900/30\b', 'border-zinc-800'),
    (r'\bring-emerald-500/30\b', 'ring-white/30'),
    (r'\bring-emerald-500\b', 'ring-white'),

    # Amber / Yellow text
    (r'\btext-amber-400\b', 'text-[#e41937]'),
    (r'\btext-amber-300\b', 'text-zinc-300'),
    (r'\btext-amber-500\b', 'text-[#e41937]'),
    (r'\btext-amber-200/80\b', 'text-zinc-300'),
    (r'\btext-yellow-400/90\b', 'text-zinc-300'),
    (r'\btext-yellow-400\b', 'text-zinc-300'),
    (r'\btext-yellow-500\b', 'text-[#e41937]'),

    # Amber / Yellow backgrounds
    (r'\bbg-amber-500/5\b', 'bg-white/5'),
    (r'\bbg-amber-500/10\b', 'bg-white/5'),
    (r'\bbg-amber-500/15\b', 'bg-white/10'),
    (r'\bbg-amber-500/20\b', 'bg-white/10'),
    (r'\bbg-amber-500/30\b', 'bg-white/15'),
    (r'\bbg-yellow-500/10\b', 'bg-white/5'),
    (r'\bbg-amber-400\b', 'bg-[#e41937]'),

    # Amber / Yellow borders & rings
    (r'\bborder-amber-500/20\b', 'border-white/15'),
    (r'\bborder-amber-500/25\b', 'border-white/20'),
    (r'\bborder-amber-500/30\b', 'border-white/25'),
    (r'\bborder-amber-500/40\b', 'border-white/30'),
    (r'\bborder-amber-500\b', 'border-white/20'),
    (r'\bborder-amber-900/30\b', 'border-zinc-800'),
    (r'\bring-amber-500/30\b', 'ring-white/20'),

    # Purple / Violet text
    (r'\btext-purple-400\b', 'text-[#fe063f]'),
    (r'\btext-purple-300\b', 'text-[#fe063f]'),
    (r'\btext-purple-500\b', 'text-[#e41937]'),

    # Purple / Violet backgrounds
    (r'\bbg-purple-600\b', 'bg-[#e41937]'),
    (r'\bbg-purple-500/10\b', 'bg-[#e41937]/15'),
    (r'\bbg-purple-500/15\b', 'bg-[#e41937]/15'),
    (r'\bbg-purple-500/20\b', 'bg-[#e41937]/20'),
    (r'\bbg-purple-500\b', 'bg-[#e41937]'),

    # Purple / Violet borders
    (r'\bborder-purple-500/20\b', 'border-[#e41937]/30'),
    (r'\bborder-purple-500/25\b', 'border-[#e41937]/35'),
    (r'\bborder-purple-500/30\b', 'border-[#e41937]/40'),
]

# 2. Raw string replacements for inline styles
inline_replacements = [
    # Green inline rgba and hex
    ("rgba(34, 197, 94, 0.14)", "rgba(255, 255, 255, 0.08)"),
    ("rgba(34, 197, 94, 0.35)", "rgba(255, 255, 255, 0.2)"),
    ("rgba(34, 197, 94, 0.3)", "rgba(255, 255, 255, 0.2)"),
    ("rgba(34, 197, 94, 0.7)", "rgba(255, 255, 255, 0.8)"),
    ("rgba(16, 185, 129, 0.14)", "rgba(255, 255, 255, 0.08)"),
    ("rgba(16, 185, 129, 0.35)", "rgba(255, 255, 255, 0.2)"),
    ("rgba(16, 185, 129, 0.3)", "rgba(255, 255, 255, 0.2)"),
    ("rgba(245, 158, 11, 0.14)", "rgba(255, 255, 255, 0.05)"),
    ("rgba(245, 158, 11, 0.3)", "rgba(255, 255, 255, 0.15)"),
    ("rgba(245, 158, 11, 0.35)", "rgba(255, 255, 255, 0.15)"),
    ("rgba(239, 68, 68, 0.14)", "rgba(228, 25, 55, 0.14)"),
    ("rgba(239, 68, 68, 0.35)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(239, 68, 68, 0.3)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(239, 68, 68, 0.7)", "rgba(228, 25, 55, 0.8)"),
    ("rgba(59, 130, 246, 0.14)", "rgba(228, 25, 55, 0.14)"),
    ("rgba(59, 130, 246, 0.3)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(59, 130, 246, 0.35)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(14, 165, 233, 0.14)", "rgba(228, 25, 55, 0.14)"),
    ("rgba(14, 165, 233, 0.35)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(6, 182, 212, 0.14)", "rgba(228, 25, 55, 0.14)"),
    ("rgba(6, 182, 212, 0.35)", "rgba(228, 25, 55, 0.35)"),
    ("rgba(139, 92, 246, 0.14)", "rgba(228, 25, 55, 0.14)"),
    ("rgba(139, 92, 246, 0.35)", "rgba(228, 25, 55, 0.35)"),

    # Hex replacements
    ("color: '#4ade80'", "color: '#ffffff'"),
    ("color: '#22c55e'", "color: '#ffffff'"),
    ("color: '#10b981'", "color: '#ffffff'"),
    ("color: '#fbbf24'", "color: '#a1a1aa'"),
    ("color: '#f59e0b'", "color: '#a1a1aa'"),
    ("color: '#f87171'", "color: '#e41937'"),
    ("color: '#ef4444'", "color: '#e41937'"),
    ("color: '#38bdf8'", "color: '#e41937'"),
    ("color: '#0ea5e9'", "color: '#e41937'"),
    ("color: '#60a5fa'", "color: '#e41937'"),
    ("color: '#3b82f6'", "color: '#e41937'"),
    ("color: '#a855f7'", "color: '#e41937'"),
    ("color: '#8b5cf6'", "color: '#e41937'"),
    ("color: '#22d3ee'", "color: '#e41937'"),
    ("color: '#06b6d4'", "color: '#e41937'"),
]

modified_count = 0
for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    new_content = content
    # Apply tailwind regex replacements
    for pattern, repl in tailwind_replacements:
        new_content = re.sub(pattern, repl, new_content)

    # Apply inline replacements
    for target, repl in inline_replacements:
        new_content = new_content.replace(target, repl)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        modified_count += 1
        print(f"Updated: {filepath}")

print(f"\nTotal files updated: {modified_count}")
