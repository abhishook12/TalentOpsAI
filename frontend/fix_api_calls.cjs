const fs = require('fs');

const fixFile = (file) => {
    let text = fs.readFileSync(file, 'utf8');
    text = text.replace(/import axios from ['"]axios['"]/g, 'import api from "../services/api"');
    text = text.replace(/axios\.get\(\s*["'`]\/analytics\/global-activity/g, 'api.get("/analytics/global-activity');
    text = text.replace(/axios\.get\(\s*["'`]\/analytics\/visitor-logs/g, 'api.get("/analytics/visitor-logs');
    text = text.replace(/axios\.get\(\s*["'`]\/admin\/workers\/status/g, 'api.get("/admin/workers/status');
    text = text.replace(/axios\.get\(\s*[`"']\/admin\/workers\/logs/g, 'api.get(`/admin/workers/logs');
    text = text.replace(/axios\.post\(\s*[`"']\/admin\/workers\//g, 'api.post(`/admin/workers/');
    
    // Remove `{ withCredentials: true }` which isn't needed with `api`
    text = text.replace(/, \{ withCredentials: true \}/g, '');
    text = text.replace(/, \{\s*\}/g, ''); // cleanup empty object if trailing comma
    
    fs.writeFileSync(file, text);
};

['src/components/WorkerDashboard.jsx', 'src/pages/ActivityLog.jsx'].forEach(f => {
    fixFile('C:/TalentOpsAI/frontend/' + f);
});

// For Dashboard.jsx
let dText = fs.readFileSync('C:/TalentOpsAI/frontend/src/pages/Dashboard.jsx', 'utf8');
dText = dText.replace(/window\.open\('\/analytics\/executive-report'/g, "window.open(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/analytics/executive-report`");
fs.writeFileSync('C:/TalentOpsAI/frontend/src/pages/Dashboard.jsx', dText);
