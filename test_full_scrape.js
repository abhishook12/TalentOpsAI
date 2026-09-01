// test_full_scrape.js — Standalone DOM Scraper Pipeline Simulation
const fs = require('fs');

// Minimal DOM mock
class MockElement {
  constructor(tag, text = '', attrs = {}, children = []) {
    this.tagName = tag.toUpperCase();
    this.textContent = text;
    this.innerText = text;
    this.innerHTML = text;
    this.attributes = attrs;
    this.children = children;
    this.parentElement = null;
    children.forEach(c => c.parentElement = this);
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  closest(selector) {
    let curr = this;
    while (curr) {
      if (curr._matches(selector)) return curr;
      curr = curr.parentElement;
    }
    return null;
  }

  _matches(selector) {
    const parts = selector.split(',').map(s => s.trim());
    return parts.some(p => {
      if (p.startsWith('.')) return (this.attributes['class'] || '').includes(p.slice(1));
      if (p.startsWith('#')) return this.attributes['id'] === p.slice(1);
      if (p.startsWith('[data-field=')) return this.attributes['data-field'] === p.slice(12, -2);
      if (p.toLowerCase() === this.tagName.toLowerCase()) return true;
      return false;
    });
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] || null;
  }

  querySelectorAll(selector) {
    const results = [];
    const check = (el) => {
      if (el !== this && el._matches(selector)) results.push(el);
      (el.children || []).forEach(check);
    };
    check(this);
    return results;
  }
}

// Build Mock LinkedIn Profile Page DOM
const doc = new MockElement('html', '', {}, [
  new MockElement('head', '', {}, [
    new MockElement('title', 'Judy Mackesy - Chief People Officer - Akkodis | LinkedIn')
  ]),
  new MockElement('body', '', {}, [
    new MockElement('div', '', { class: 'ph5' }, [
      new MockElement('h1', 'Judy Mackesy\n1st degree connection', { class: 'text-heading-xlarge inline' }),
      new MockElement('div', 'Chief People Officer at Akkodis', { class: 'text-body-medium break-words' }),
      new MockElement('div', 'Jacksonville, Florida, United States', { class: 'text-body-small inline' })
    ]),
    new MockElement('aside', '', {}, [
      new MockElement('div', '', { class: 'artdeco-entity-lockup' }, [
        new MockElement('a', 'Veronica Ramirez', { href: 'https://www.linkedin.com/in/veronica-ramirez-8a901b/' }),
        new MockElement('div', 'Senior Talent Acquisition Partner at Microsoft', { class: 'artdeco-entity-lockup__subtitle' })
      ]),
      new MockElement('div', '', { class: 'artdeco-entity-lockup' }, [
        new MockElement('a', 'Elizabeth Nuncio 2nd', { href: 'https://www.linkedin.com/in/elizabeth-nuncio/' }),
        new MockElement('div', 'Recruiting Lead at Google', { class: 'artdeco-entity-lockup__subtitle' })
      ])
    ])
  ])
]);

global.location = {
  hostname: 'www.linkedin.com',
  pathname: '/in/judymackesy/',
  href: 'https://www.linkedin.com/in/judymackesy/',
};
global.window = {
  location: global.location,
};
global.document = {
  title: 'Judy Mackesy - Chief People Officer - Akkodis | LinkedIn',
  body: doc.children[1],
  querySelector: sel => doc.querySelector(sel),
  querySelectorAll: sel => doc.querySelectorAll(sel),
};

// Load patterns and linkedin
eval(fs.readFileSync('talent-scout-extension/detector/patterns.js', 'utf8'));
eval(fs.readFileSync('talent-scout-extension/detector/linkedin.js', 'utf8'));

console.log("=== RUNNING FULL DOM SCRAPE SIMULATION ===");
const results = window.TalentScout.detectLinkedIn();
console.log(`Discovered ${results.length} leads:`);
results.forEach((r, i) => {
  console.log(`[Lead #${i+1}] Name: "${r.recruiter_name}" | Title: "${r.title}" | Company: "${r.company_name}" | LinkedIn: "${r.linkedin_url}"`);
});

if (results.length >= 1 && results[0].recruiter_name === "Judy Mackesy") {
  console.log("\n>>> FULL DOM SCRAPER SIMULATION 100% SUCCESSFUL! <<<");
} else {
  console.log("\n>>> FULL DOM SCRAPER SIMULATION FAILED! <<<");
  process.exit(1);
}
