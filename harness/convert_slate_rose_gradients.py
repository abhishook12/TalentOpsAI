import os
import re

files_to_process = []
for root, dirs, files in os.walk('frontend/src'):
    for f in files:
        if f.endswith(('.jsx', '.js', '.tsx', '.ts')):
            files_to_process.append(os.path.join(root, f))

replacements = [
    # Slate backgrounds -> Black & Grey
    (r'\bbg-slate-950/80\b', 'bg-black/80'),
    (r'\bbg-slate-950/60\b', 'bg-black/60'),
    (r'\bbg-slate-950/40\b', 'bg-black/40'),
    (r'\bbg-slate-950/30\b', 'bg-black/30'),
    (r'\bbg-slate-950\b', 'bg-black'),
    (r'\bbg-slate-900\b', 'bg-[#121212]'),
    (r'\bbg-slate-800\b', 'bg-[#18181b]'),
    (r'\bbg-slate-700\b', 'bg-[#27272a]'),

    # Slate borders -> White / Grey borders
    (r'\bborder-slate-800\b', 'border-white/10'),
    (r'\bborder-slate-700\b', 'border-white/15'),
    (r'\bborder-slate-600\b', 'border-white/20'),

    # Slate text -> Zinc / White
    (r'\btext-slate-600\b', 'text-zinc-500'),
    (r'\btext-slate-500\b', 'text-zinc-500'),
    (r'\btext-slate-400\b', 'text-zinc-400'),
    (r'\btext-slate-300\b', 'text-zinc-300'),
    (r'\btext-slate-200\b', 'text-zinc-200'),

    # Rose -> Crimson Red #e41937
    (r'\btext-rose-400/80\b', 'text-[#fe063f]/80'),
    (r'\btext-rose-400\b', 'text-[#fe063f]'),
    (r'\btext-rose-300\b', 'text-[#fe063f]'),
    (r'\btext-rose-200\b', 'text-[#fe063f]'),
    (r'\bbg-rose-500/10\b', 'bg-[#e41937]/15'),
    (r'\bbg-rose-500/15\b', 'bg-[#e41937]/15'),
    (r'\bbg-rose-500/20\b', 'bg-[#e41937]/20'),
    (r'\bbg-rose-500/30\b', 'bg-[#e41937]/25'),
    (r'\bborder-rose-500/20\b', 'border-[#e41937]/30'),
    (r'\bborder-rose-500/25\b', 'border-[#e41937]/35'),
    (r'\bborder-rose-500/30\b', 'border-[#e41937]/40'),
    (r'\bborder-rose-500/40\b', 'border-[#e41937]/50'),
    (r'\bborder-rose-900/30\b', 'border-[#e41937]/30'),
    (r'\bring-rose-500/30\b', 'ring-[#e41937]/30'),

    # Gradients & Shadows
    (r'\bfrom-emerald-500\b', 'from-[#e41937]'),
    (r'\bto-teal-600\b', 'to-[#fe063f]'),
    (r'\bto-teal-400\b', 'to-white'),
    (r'\bto-rose-400\b', 'to-[#fe063f]'),
    (r'\bfrom-amber-400\b', 'from-[#e41937]'),
    (r'\bfrom-amber-500/10\b', 'from-[#e41937]/10'),
    (r'\bfrom-amber-500\b', 'from-[#e41937]'),
    (r'\bto-orange-500\b', 'to-[#fe063f]'),
    (r'\bto-orange-600/10\b', 'to-[#fe063f]/10'),
    (r'\bto-orange-600\b', 'to-[#fe063f]'),
    (r'\bfrom-purple-950/30\b', 'from-black/40'),
    (r'\bshadow-emerald-500/20\b', 'shadow-[#e41937]/20'),
    (r'\bshadow-emerald-600/20\b', 'shadow-[#e41937]/20'),
    (r'\bshadow-emerald-500/5\b', 'shadow-[#e41937]/5'),
    (r'\bshadow-amber-500/20\b', 'shadow-[#e41937]/20'),
    (r'\bshadow-emerald-950/40\b', 'shadow-black/60'),
    (r'\bshadow-purple-950/50\b', 'shadow-black/60'),
    (r'\bshadow-rose-950/40\b', 'shadow-black/60'),
]

modified = 0
for filepath in files_to_process:
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    new_content = content
    for pattern, repl in replacements:
        new_content = re.sub(pattern, repl, new_content)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        modified += 1
        print(f"Updated: {filepath}")

print(f"\nTotal files updated: {modified}")
