// test_linkedin_dom.js — Pure DOM Scraper Verification
const fs = require('fs');

// Mock window and browser globals
global.window = {};
global.document = {
  title: "Judy Mackesy - Chief People Officer - Akkodis | LinkedIn",
  querySelector: () => null,
  querySelectorAll: () => [],
};
global.location = {
  hostname: "www.linkedin.com",
  pathname: "/in/judymackesy/",
  href: "https://www.linkedin.com/in/judymackesy/",
};

// Load patterns.js
const patternsCode = fs.readFileSync('talent-scout-extension/detector/patterns.js', 'utf8');
eval(patternsCode);

// Load linkedin.js
const linkedinCode = fs.readFileSync('talent-scout-extension/detector/linkedin.js', 'utf8');
eval(linkedinCode);

console.log("=== UNIT TEST 1: patterns.js normalizeName ===");
const testCases = [
  { input: "Judy Mackesy\n  1st\n  1st degree connection", expected: "Judy Mackesy" },
  { input: "Veronica Ramirez, MBA, 2nd", expected: "Veronica Ramirez" },
  { input: "Elizabeth Nuncio (she/her) • 1st", expected: "Elizabeth Nuncio" },
  { input: "John Doe - Senior Technical Recruiter", expected: "John Doe" },
  { input: "Sarah Jenkins, SHRM-CP, 3rd+", expected: "Sarah Jenkins" },
];

let allPassed = true;
testCases.forEach(tc => {
  const actual = window.TalentScout.normalizeName(tc.input);
  const pass = actual === tc.expected;
  if (!pass) allPassed = false;
  console.log(`[${pass ? 'PASS' : 'FAIL'}] Input: "${tc.input.replace(/\n/g, ' ')}" -> Output: "${actual}" (Expected: "${tc.expected}")`);
});

console.log("\n=== UNIT TEST 2: inferNameFromLinkedInSlug ===");
const slugCases = [
  { url: "https://www.linkedin.com/in/judymackesy/", expected: "Judymackesy" },
  { url: "https://www.linkedin.com/in/judy-mackesy/", expected: "Judy Mackesy" },
  { url: "https://www.linkedin.com/in/veronica-ramirez-8a901b/", expected: "Veronica Ramirez" },
  { url: "https://www.linkedin.com/in/elizabeth-nuncio-1234567890/", expected: "Elizabeth Nuncio" },
];

slugCases.forEach(sc => {
  const actual = window.TalentScout.inferNameFromLinkedInSlug(sc.url);
  const pass = actual === sc.expected;
  if (!pass) allPassed = false;
  console.log(`[${pass ? 'PASS' : 'FAIL'}] URL: "${sc.url}" -> Output: "${actual}" (Expected: "${sc.expected}")`);
});

if (allPassed) {
  console.log("\n>>> ALL DOM UNIT TESTS PASSED! <<<");
} else {
  console.log("\n>>> SOME DOM UNIT TESTS FAILED! <<<");
  process.exit(1);
}
