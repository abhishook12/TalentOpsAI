with open('frontend/src/pages/AdminTerminal.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()

imports = [
    "import StatCard from '../components/admin/StatCard'\n",
    "import Section from '../components/admin/Section'\n",
    "import Badge from '../components/admin/Badge'\n",
    "import AdminLock from '../components/admin/AdminLock'\n",
    "import SqlConsole from '../components/admin/SqlConsole'\n",
    "import SessionRow from '../components/admin/SessionRow'\n"
]

del lines[9:552]

lines = lines[:5] + imports + lines[5:]

with open('frontend/src/pages/AdminTerminal.jsx', 'w', encoding='utf-8') as f:
    f.writelines(lines)
