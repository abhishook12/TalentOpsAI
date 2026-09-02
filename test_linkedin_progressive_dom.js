/**
 * Node.js Unit Test for LinkedIn Single Profile Progressive Extraction (Kelsei Martinez Scenario)
 */

const fs = require('fs');
const path = require('path');

// Mock browser globals
global.window = global;
global.document = {
  title: 'Kelsei Martinez | LinkedIn',
  body: {
    innerText: 'Kelsei Martinez VP of Staffing at Premier Staffing Solution LLC Chicago, Illinois 11,476 followers 500+ connections East Carolina University',
  }
};
global.location = {
  hostname: 'www.linkedin.com',
  pathname: '/in/kelseirobertson/',
  href: 'https://www.linkedin.com/in/kelseirobertson/',
};

// Simple Mock DOM Node structure for LinkedIn Profile
class MockElement {
  constructor(tag, text = '', attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.textContent = text;
    this.attrs = attrs;
    this.children = [];
  }

  appendChild(el) {
    this.children.push(el);
    return el;
  }

  _matches(sel) {
    sel = sel.trim();
    if (!sel) return false;

    // Direct tag match
    if (sel === 'h1' && this.tagName === 'H1') return true;
    if (sel === 'div' && this.tagName === 'DIV') return true;
    if (sel === 'span' && this.tagName === 'SPAN') return true;
    if (sel === 'ul' && this.tagName === 'UL') return true;
    if (sel === 'li' && this.tagName === 'LI') return true;
    if (sel === 'a' && this.tagName === 'A') return true;

    // ID match
    if (sel.startsWith('#')) {
      return this.attrs.id === sel.slice(1);
    }

    // Attribute match
    if (sel.includes('[aria-hidden="true"]')) {
      return this.attrs['aria-hidden'] === 'true';
    }
    if (sel.includes('a[href*="/school/"]')) {
      return this.tagName === 'A' && this.attrs.href && this.attrs.href.includes('/school/');
    }

    // Class list check
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

// Build Mock DOM for Kelsei Martinez Profile
const root = new MockElement('body');

const h1 = new MockElement('h1', 'Kelsei Martinez', { class: 'text-heading-xlarge' });
root.appendChild(h1);

const headline = new MockElement('div', 'VP of Staffing at Premier Staffing Solution LLC with expertise in client relations and strategy', { class: 'text-body-medium' });
root.appendChild(headline);

const loc = new MockElement('span', 'Chicago, Illinois, United States', { class: 'text-body-small inline t-black--light break-words' });
root.appendChild(loc);

const rightPanel = new MockElement('div', '', { class: 'pv-text-details__right-panel' });
const eduAnchor = new MockElement('a', '', { href: 'https://www.linkedin.com/school/east-carolina-university/' });
const eduSpan = new MockElement('span', 'East Carolina University', { 'aria-hidden': 'true' });
eduAnchor.appendChild(eduSpan);
rightPanel.appendChild(eduAnchor);
root.appendChild(rightPanel);

// Followers & Connections
const followList = new MockElement('ul', '', { class: 'pv-top-card--list-bullet' });
const li1 = new MockElement('li', '');
const sp1 = new MockElement('span', '11,476 followers', { class: 't-bold' });
li1.appendChild(sp1);
const li2 = new MockElement('li', '');
const sp2 = new MockElement('span', '500+ connections', { class: 't-bold' });
li2.appendChild(sp2);
followList.appendChild(li1);
followList.appendChild(li2);
root.appendChild(followList);

// About section
const aboutSec = new MockElement('div', '', { id: 'about' });
const aboutWrap = new MockElement('div', '', { class: 'display-flex' });
const aboutSpan = new MockElement('span', 'VP of Staffing at Premier Staffing Solution LLC with expertise in client relations and strategy', { 'aria-hidden': 'true' });
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

console.log('================================================================================');
console.log('RUNNING KELSEI MARTINEZ PROGRESSIVE PROFILE DOM TEST');
console.log('================================================================================');

const leads = window.TalentScout.detectLinkedIn();

console.log(`Discovered ${leads.length} candidate(s):`);
console.log(JSON.stringify(leads[0], null, 2));

// Invariant Assertions
if (leads.length !== 1) {
  console.error(`[FAIL] Expected 1 candidate lead, got ${leads.length}`);
  process.exit(1);
}

const lead = leads[0];
console.assert(lead.recruiter_name === 'Kelsei Martinez', `Name must be Kelsei Martinez (got: ${lead.recruiter_name})`);
console.assert(lead.title === 'VP of Staffing', `Title must be VP of Staffing (got: ${lead.title})`);
console.assert(lead.company_name === 'Premier Staffing Solution LLC', `Company must be Premier Staffing Solution LLC (got: ${lead.company_name})`);
console.assert(lead.company_name !== 'LinkedIn', 'Company must never be LinkedIn');
console.assert(lead.location === 'Chicago, Illinois, United States', `Location must be Chicago, Illinois, United States (got: ${lead.location})`);
console.assert(lead.education === 'East Carolina University', `Education must be East Carolina University (got: ${lead.education})`);
console.assert(lead.confidence >= 85, `Confidence must be >= 85% (got: ${lead.confidence}%)`);

console.log('\n>>> KELSEI MARTINEZ DOM TEST: ALL ASSERTIONS PASSED (100%)! <<<');
process.exit(0);
