const fs = require('fs');
const path = require('path');

const replaceInFile = (file) => {
    let content = fs.readFileSync(file, 'utf8');
    
    // Replace broken double-quote template literals from previous replacement
    content = content.replace(/"\$\{import\.meta\.env\.VITE_API_URL \|\| 'http:\/\/127\.0\.0\.1:8000'\}/g, '`${import.meta.env.VITE_API_URL || \'http://127.0.0.1:8000\'}');
    content = content.replace(/"\$\{import\.meta\.env\.VITE_API_URL \|\| 'http:\/\/localhost:8000'\}/g, '`${import.meta.env.VITE_API_URL || \'http://127.0.0.1:8000\'}');
    
    // Also replace single quotes if any
    content = content.replace(/'\$\{import\.meta\.env\.VITE_API_URL \|\| 'http:\/\/127\.0\.0\.1:8000'\}/g, '`${import.meta.env.VITE_API_URL || \'http://127.0.0.1:8000\'}');
    
    fs.writeFileSync(file, content);
};

const files = [
    'src/components/EnrichmentLiveFeed.jsx', 
    'src/components/WorkerDashboard.jsx', 
    'src/pages/ActivityLog.jsx', 
    'src/pages/Dashboard.jsx'
];

files.forEach(f => replaceInFile(path.join('C:/TalentOpsAI/frontend', f)));
console.log('Fixed quotes.');
