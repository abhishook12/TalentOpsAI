/**
 * Automated Regression Test for SynergyGrid IT Screen (DOM Detector & Classifier)
 */
const fs = require('fs');
const path = require('path');

// Helper to create mock DOM elements
function createMockElement(tag, className, textContent, attributes = {}, children = []) {
  const elem = {
    tagName: tag.toUpperCase(),
    className: className || '',
    textContent: textContent || '',
    attributes: attributes,
    href: attributes.href || null,
    children: children,
    querySelector: (sel) => {
      // Class match
      if (sel.startsWith('.')) {
        const cls = sel.slice(1);
        if (elem.className.includes(cls)) return elem;
        for (const child of elem.children) {
          const res = child.querySelector(sel);
          if (res) return res;
        }
      }
      // Tag match
      if (sel.toLowerCase() === tag.toLowerCase()) return elem;
      // Attr match e.g. a[href*="/in/"]
      if (sel.includes('href*="/in/"')) {
        if (elem.attributes.href && elem.attributes.href.includes('/in/')) return elem;
        for (const child of elem.children) {
          const res = child.querySelector(sel);
          if (res) return res;
        }
      }
      for (const child of elem.children) {
        const res = child.querySelector(sel);
        if (res) return res;
      }
      return null;
    },
    querySelectorAll: (sel) => {
      const list = [];
      if (sel.startsWith('.')) {
        const cls = sel.slice(1);
        if (elem.className.includes(cls)) list.push(elem);
      }
      for (const child of elem.children) {
        list.push(...child.querySelectorAll(sel));
      }
      return list;
    }
  };
  return elem;
}

// Build Card 1: Mihir Roy
const card1Title = createMockElement('a', 'org-people-profile-card__profile-title', 'Mihir Roy · 2nd', { href: 'https://www.linkedin.com/in/mihir-roy-12345/' });
const card1Pos = createMockElement('div', 'org-people-profile-card__profile-position', 'Recruiting Manager at SynergyGrid IT');
const card1Btn = createMockElement('button', 'artdeco-button', 'Connect');
const card1 = createMockElement('div', 'org-people-profile-card artdeco-card', '', {}, [card1Title, card1Pos, card1Btn]);

// Build Card 2: Kenny Shaw
const card2Title = createMockElement('a', 'org-people-profile-card__profile-title', 'Kenny Shaw · 2nd', { href: 'https://www.linkedin.com/in/kenny-shaw-67890/' });
const card2Pos = createMockElement('div', 'org-people-profile-card__profile-position', 'Vice President at SynergyGrid IT');
const card2Btn = createMockElement('button', 'artdeco-button', 'Connect');
const card2 = createMockElement('div', 'org-people-profile-card artdeco-card', '', {}, [card2Title, card2Pos, card2Btn]);

// Build Card 3: Apurva C.
const card3Title = createMockElement('a', 'org-people-profile-card__profile-title', 'Apurva C. · 3rd', { href: 'https://www.linkedin.com/in/apurva-c-54321/' });
const card3Pos = createMockElement('div', 'org-people-profile-card__profile-position', 'Senior Recruiter');
const card3Btn = createMockElement('button', 'artdeco-button', 'Message');
const card3 = createMockElement('div', 'org-people-profile-card artdeco-card', '', {}, [card3Title, card3Pos, card3Btn]);

// Build Page Header
const headerTitle = createMockElement('h1', 'org-top-card-summary__title', 'SynergyGrid IT');

// Root Document
const rootDoc = createMockElement('body', '', '', {}, [headerTitle, card1, card2, card3]);

// Mock global window & document
global.window = {};
global.document = {
  title: "SynergyGrid IT: People | LinkedIn",
  querySelector: (sel) => rootDoc.querySelector(sel),
  querySelectorAll: (sel) => {
    if (sel.includes('.org-people-profile-card') || sel.includes('.artdeco-card')) {
      return [card1, card2, card3];
    }
    return rootDoc.querySelectorAll(sel);
  },
};

global.location = {
  hostname: "www.linkedin.com",
  pathname: "/company/synergygrid-it/people/",
  href: "https://www.linkedin.com/company/synergygrid-it/people/",
};

// Load patterns.js
const patternsCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'detector', 'patterns.js'), 'utf8');
eval(patternsCode);

// Load linkedin.js
const linkedinCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'detector', 'linkedin.js'), 'utf8');
eval(linkedinCode);

console.log('='.repeat(80));
console.log('RUNNING SYNERGYGRID IT SCREEN REGRESSION TEST');
console.log('='.repeat(80));

const results = window.TalentScout.detectLinkedIn();

console.log(`\nDiscovered ${results.length} candidate entities (Expected: 3):`);
results.forEach((r, idx) => {
  console.log(`\n[Person #${idx + 1}]`);
  console.log(`  Name:             "${r.recruiter_name}"`);
  console.log(`  Title:            "${r.title}"`);
  console.log(`  Employer Company: "${r.company_name}"`);
  console.log(`  Source Platform:  "${r.source_platform}"`);
  console.log(`  LinkedIn URL:     "${r.linkedin_url}"`);
  console.log(`  Confidence:       ${r.confidence}%`);
});

// Assertions
let passed = 0;
let total = 0;

function assert(condition, desc) {
  total++;
  if (condition) {
    console.log(`[PASS] ${desc}`);
    passed++;
  } else {
    console.error(`[FAIL] ${desc}`);
  }
}

console.log('\n--- VERIFYING HARD-RULE CONSTRAINTS ---');

// 1. Enumerate all 3 people
assert(results.length === 3, 'Must extract all 3 visible people from grid (Mihir Roy, Kenny Shaw, Apurva C.)');

const mihir = results.find(r => r.recruiter_name === 'Mihir Roy');
const kenny = results.find(r => r.recruiter_name === 'Kenny Shaw');
const apurva = results.find(r => r.recruiter_name === 'Apurva C.');

// 2. Mihir Roy checks
assert(Boolean(mihir), 'Mihir Roy entity must exist');
if (mihir) {
  assert(mihir.title === 'Recruiting Manager', `Mihir title must be "Recruiting Manager" (got: "${mihir.title}")`);
  assert(mihir.company_name === 'SynergyGrid IT', `Mihir company must be "SynergyGrid IT" (got: "${mihir.company_name}")`);
  assert(mihir.company_name !== 'LinkedIn', 'Mihir company must NEVER be "LinkedIn"');
  assert(mihir.title !== 'Contact', 'Mihir title must NEVER be "Contact"');
  assert(mihir.source_platform === 'LinkedIn', 'Mihir source platform must be "LinkedIn"');
  assert(mihir.confidence >= 80, `Confidence must be >= 80% (got: ${mihir.confidence}%)`);
}

// 3. Kenny Shaw checks
assert(Boolean(kenny), 'Kenny Shaw entity must exist');
if (kenny) {
  assert(kenny.title === 'Vice President', `Kenny title must be "Vice President" (got: "${kenny.title}")`);
  assert(kenny.company_name === 'SynergyGrid IT', `Kenny company must be "SynergyGrid IT" (got: "${kenny.company_name}")`);
  assert(kenny.company_name !== 'LinkedIn', 'Kenny company must NEVER be "LinkedIn"');
}

// 4. Apurva C. checks (Company inherited from page context)
assert(Boolean(apurva), 'Apurva C. entity must exist');
if (apurva) {
  assert(apurva.title === 'Senior Recruiter', `Apurva title must be "Senior Recruiter" (got: "${apurva.title}")`);
  assert(apurva.company_name === 'SynergyGrid IT', `Apurva company must inherit "SynergyGrid IT" from page context (got: "${apurva.company_name}")`);
  assert(apurva.title !== 'Message', 'Apurva title must NEVER be UI button "Message"');
}

// 5. UI Actions rejection check
const allTitles = results.map(r => r.title.toLowerCase());
assert(!allTitles.includes('connect'), 'UI Action "Connect" must not be used as title');
assert(!allTitles.includes('message'), 'UI Action "Message" must not be used as title');
assert(!allTitles.includes('contact'), 'UI Action "Contact" must not be used as title');

console.log('\n' + '='.repeat(80));
console.log(`TEST RESULTS: ${passed}/${total} assertions passed (${Math.round((passed / total) * 100)}%)`);
console.log('='.repeat(80));

if (passed === total) {
  process.exit(0);
} else {
  process.exit(1);
}
