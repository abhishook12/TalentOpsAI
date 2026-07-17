const fs = require('fs');
const path = require('path');

const srcDir = path.join(__dirname, 'frontend', 'src');

function walkSync(dir, filelist = []) {
  fs.readdirSync(dir).forEach(file => {
    const dirFile = path.join(dir, file);
    if (fs.statSync(dirFile).isDirectory()) {
      filelist = walkSync(dirFile, filelist);
    } else {
      if (dirFile.endsWith('.jsx')) {
        filelist.push(dirFile);
      }
    }
  });
  return filelist;
}

const files = walkSync(srcDir);

let changedFiles = 0;

files.forEach(file => {
  let content = fs.readFileSync(file, 'utf8');
  let originalContent = content;

  // Replace hardcoded #fff or #ffffff text color with var(--text-primary) except in specific contexts
  // Usually color: '#fff' or color: '#ffffff'
  content = content.replace(/color:\s*['"]#(?:fff|ffffff)['"]/gi, "color: 'var(--text-inverse)'");

  // Replace rgba(255,255,255,0.02) to 0.08 with var(--bg-surface) or var(--accent-bg) or var(--muted-grid)
  content = content.replace(/background:\s*['"]rgba\(255,\s*255,\s*255,\s*0\.0[2-6]\)['"]/gi, "background: 'var(--bg-surface)'");
  content = content.replace(/background:\s*['"]rgba\(255,\s*255,\s*255,\s*0\.0[7-9]\)['"]/gi, "background: 'var(--accent-bg)'");
  content = content.replace(/background:\s*['"]rgba\(255,\s*255,\s*255,\s*0\.1[0-9]?\)['"]/gi, "background: 'var(--accent-bg)'");
  
  content = content.replace(/backgroundColor:\s*['"]rgba\(255,\s*255,\s*255,\s*0\.0[0-9]\)['"]/gi, "backgroundColor: 'var(--bg-surface)'");
  
  // Replace border: '1px solid rgba(255,255,255,0.06)' etc with var(--card-border)
  content = content.replace(/border:\s*['"]1px solid rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "border: '1px solid var(--card-border)'");
  content = content.replace(/borderBottom:\s*['"]1px solid rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "borderBottom: '1px solid var(--card-border)'");
  content = content.replace(/borderTop:\s*['"]1px solid rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "borderTop: '1px solid var(--card-border)'");
  content = content.replace(/borderRight:\s*['"]1px solid rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "borderRight: '1px solid var(--card-border)'");
  content = content.replace(/borderLeft:\s*['"]1px solid rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "borderLeft: '1px solid var(--card-border)'");
  
  content = content.replace(/borderColor:\s*['"]rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)['"]/gi, "borderColor: 'var(--card-border)'");

  // Fix UserManagement dropdown styling specifically
  if (file.includes('UserManagement.jsx')) {
    // We already replaced the background to var(--bg-surface). 
    // And color to var(--text-inverse). Wait! Text should be primary for dropdowns.
    content = content.replace(/color: 'var\(--text-inverse\)'/g, "color: 'var(--text-primary)'");
    
    // Fix specific hardcoded backgrounds in UserManagement
    content = content.replace(/background: 'var\(--panel-bg\)', color: 'var\(--text-primary\)',/g, "background: 'var(--bg-surface)', color: 'var(--text-primary)',");
  }

  // Same for AdminTerminal
  if (file.includes('AdminTerminal.jsx')) {
    content = content.replace(/color: 'var\(--text-inverse\)'/g, "color: 'var(--text-primary)'");
  }

  if (content !== originalContent) {
    fs.writeFileSync(file, content);
    changedFiles++;
    console.log(`Updated ${file}`);
  }
});

console.log(`\nUpdated ${changedFiles} files.`);
