import os

# 1. Update App.jsx
with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    app_c = f.read()

app_c = app_c.replace(
    "backgroundColor: dbConnected ? '#22c55e' : '#ef4444'",
    "backgroundColor: dbConnected ? '#ffffff' : '#e41937'"
)
app_c = app_c.replace(
    "boxShadow: dbConnected ? '0 0 6px rgba(34, 197, 94, 0.7)' : '0 0 6px rgba(239, 68, 68, 0.7)'",
    "boxShadow: dbConnected ? '0 0 6px rgba(255, 255, 255, 0.8)' : '0 0 6px rgba(228, 25, 55, 0.8)'"
)

with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
    f.write(app_c)
print('Updated App.jsx')

# 2. Update Dashboard.jsx to replace 🌐 emoji with Lucide Globe icon
with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    dash_c = f.read()

# Add Globe import if not present
if "import { Globe }" not in dash_c and "Globe," not in dash_c and ", Globe" not in dash_c:
    dash_c = "import { Globe } from 'lucide-react'\n" + dash_c

dash_c = dash_c.replace(
    "<span style={{ fontSize: 22 }}>🌐</span>",
    '<Globe size={22} className="text-white/80" />'
)

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(dash_c)
print('Updated Dashboard.jsx')
