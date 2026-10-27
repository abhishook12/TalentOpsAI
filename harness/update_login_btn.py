with open(r'C:\TalentOpsAI\frontend\src\pages\auth\Login.jsx', 'r', encoding='utf-8') as f:
    c = f.read()

target = 'className="w-full h-11 border-none rounded-lg bg-white text-zinc-950 text-sm font-semibold cursor-pointer transition-all flex items-center justify-center hover:not-disabled:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"'
replacement = 'className="w-full h-11 border-none rounded-lg bg-[#e41937] text-white text-sm font-semibold cursor-pointer transition-all flex items-center justify-center hover:not-disabled:bg-[#fe063f] hover:not-disabled:shadow-[0_0_20px_rgba(228,25,55,0.45)] disabled:opacity-40 disabled:cursor-not-allowed shadow-md"'

if target in c:
    c = c.replace(target, replacement)
    c = c.replace('text-zinc-950', 'text-white')
    with open(r'C:\TalentOpsAI\frontend\src\pages\auth\Login.jsx', 'w', encoding='utf-8') as f:
        f.write(c)
    print('Updated Login.jsx button successfully!')
else:
    print('Target not found in Login.jsx')
