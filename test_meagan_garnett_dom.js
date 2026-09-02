const fs = require('fs');
const path = require('path');

// Mock browser globals
global.window = global;
global.document = {
  title: 'Meagan Garnett - Professional Recruiter - Brooksource | LinkedIn',
  body: {
    innerText: 'Meagan Garnett Professional Recruiter at Brooksource Greater Birmingham, Alabama Area 500+ connections The University of Alabama Brooksource',
  }
};
global.location = {
  hostname: 'www.linkedin.com',
  pathname: '/in/meagangarnett/',
  href: 'https://www.linkedin.com/in/meagangarnett/',
};
global.chrome = {
  storage: {
    local: { set: () => {}, get: () => {} }
  }
};

class MockElement {
  constructor(tag, text = '', attrs = {}) {
    this.tagName = tag.toUpperCase();
    this._text = text;
    this.attrs = attrs;
    this.children = [];
  }

  get textContent() {
    if (this._text) return this._text;
    return this.children.map(c => c.textContent).join(' ').trim();
  }

  set textContent(v) {
    this._text = v;
  }

  appendChild(el) {
    this.children.push(el);
    return el;
  }

  _matches(sel) {
    sel = sel.trim();
    if (!sel) return false;

    // Check specific tag / attribute matches
    if (sel === 'a[href*="/school/"]' || sel.startsWith('a[href*="/school/"]')) {
      if (this.tagName === 'A' && this.attrs.href && this.attrs.href.includes('/school/')) return true;
    }
    if (sel === 'a[href*="/company/"]' || sel.startsWith('a[href*="/company/"]')) {
      if (this.tagName === 'A' && this.attrs.href && this.attrs.href.includes('/company/')) return true;
    }
    if (sel === 'h1' && this.tagName === 'H1') return true;
    if (sel === 'div' && this.tagName === 'DIV') return true;
    if (sel === 'span' && this.tagName === 'SPAN') return true;
    if (sel === 'ul' && this.tagName === 'UL') return true;
    if (sel === 'li' && this.tagName === 'LI') return true;
    if (sel === 'a' && this.tagName === 'A') return true;

    if (sel.startsWith('#')) {
      return this.attrs.id === sel.slice(1);
    }

    if (sel === 'span[aria-hidden="true"]' || sel === '[aria-hidden="true"]') {
      return this.attrs['aria-hidden'] === 'true';
    }

    const classes = (this.attrs.class || '').split(/\s+/);
    const selClasses = sel.replace(/^[a-z0-9]+/i, '').split('.').filter(Boolean);
    if (selClasses.length > 0) {
      const matchAll = selClasses.every(c => classes.includes(c));
      const tagPart = sel.match(/^[a-z0-9]+/i);
      if (matchAll && (!tagPart || this.tagName === tagPart[0].toUpperCase())) {
        return true;
      }
    }

    return false;
  }

  querySelector(sel) {
    const all = this.querySelectorAll(sel);
    return all.length > 0 ? all[0] : null;
  }

  querySelectorAll(sel) {
    const results = [];
    const check = (node) => {
      if (node !== this) {
        if (node._matches(sel)) results.push(node);
      }
      node.children.forEach(c => check(c));
    };
    check(this);
    return results;
  }
}

// Build Mock DOM for Meagan Garnett Profile
const root = new MockElement('body');

const h1 = new MockElement('h1', 'Meagan Garnett', { class: 'text-heading-xlarge' });
root.appendChild(h1);

const headline = new MockElement('div', 'Professional Recruiter at Brooksource', { class: 'text-body-medium break-words' });
root.appendChild(headline);

const loc = new MockElement('span', 'Greater Birmingham, Alabama Area', { class: 'text-body-small inline t-black--light break-words' });
root.appendChild(loc);

const rightPanel = new MockElement('div', '', { class: 'pv-text-details__right-panel' });
const compAnchor = new MockElement('a', '', { href: 'https://www.linkedin.com/company/brooksource/' });
const compSpan = new MockElement('span', 'Brooksource', { 'aria-hidden': 'true' });
compAnchor.appendChild(compSpan);
rightPanel.appendChild(compAnchor);

const eduAnchor = new MockElement('a', '', { href: 'https://www.linkedin.com/school/university-of-alabama/' });
const eduSpan = new MockElement('span', 'The University of Alabama', { 'aria-hidden': 'true' });
eduAnchor.appendChild(eduSpan);
rightPanel.appendChild(eduAnchor);
root.appendChild(rightPanel);

// Followers & Connections
const followList = new MockElement('ul', '', { class: 'pv-top-card--list-bullet' });
const li1 = new MockElement('li', '');
const sp1 = new MockElement('span', '500+ connections', { class: 't-bold' });
li1.appendChild(sp1);
followList.appendChild(li1);
root.appendChild(followList);

// About section
const aboutSec = new MockElement('div', '', { id: 'about' });
const aboutWrap = new MockElement('div', '', { class: 'display-flex' });
const aboutSpan = new MockElement('span', 'Passionate about building strong relationships and helping people find opportunities that align with their goals. As a recruiter, I enjoy getting to know peoples stories...', { 'aria-hidden': 'true' });
aboutWrap.appendChild(aboutSpan);
root.appendChild(aboutSec);
root.appendChild(aboutWrap);

global.document.querySelector = (s) => root.querySelector(s);
global.document.querySelectorAll = (s) => root.querySelectorAll(s);

// Load patterns.js and linkedin.js
const patternsCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'detector', 'patterns.js'), 'utf8');
eval(patternsCode);

const linkedinCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'detector', 'linkedin.js'), 'utf8');
eval(linkedinCode);

const results = window.TalentScout.detectLinkedIn();
console.log('Discovered leads:', JSON.stringify(results, null, 2));

if (results.length === 0) {
  console.error('FAILED: No leads discovered!');
  process.exit(1);
}

const lead = results[0];
if (lead.recruiter_name !== 'Meagan Garnett') {
  console.error(`FAILED: Expected name "Meagan Garnett", got "${lead.recruiter_name}"`);
  process.exit(1);
}

if (lead.title !== 'Professional Recruiter') {
  console.error(`FAILED: Expected title "Professional Recruiter", got "${lead.title}"`);
  process.exit(1);
}

if (lead.company_name !== 'Brooksource') {
  console.error(`FAILED: Expected company "Brooksource", got "${lead.company_name}"`);
  process.exit(1);
}

if (!lead.location || !lead.location.includes('Birmingham, Alabama')) {
  console.error(`FAILED: Expected location to contain "Birmingham, Alabama", got "${lead.location}"`);
  process.exit(1);
}

if (!lead.education || !lead.education.includes('University of Alabama')) {
  console.error(`FAILED: Expected education to contain "University of Alabama", got "${lead.education}"`);
  process.exit(1);
}

console.log('\n>>> MEAGAN GARNETT DOM TEST: 100% PASSED! <<<');
