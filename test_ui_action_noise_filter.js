const fs = require('fs');
const path = require('path');

global.window = global;
global.chrome = { storage: { local: {} } };

const patternsCode = fs.readFileSync(path.join(__dirname, 'talent-scout-extension', 'detector', 'patterns.js'), 'utf8');
eval(patternsCode);

const tests = [
  // Garbage UI buttons & accordion expanders from screenshot
  { name: 'Show All Volunteer Experience', expectedValid: false },
  { name: 'Search chat', expectedValid: false },
  { name: 'Show all 5 experiences', expectedValid: false },
  { name: 'View all recommendations', expectedValid: false },
  { name: 'Open messaging', expectedValid: false },
  { name: 'Recruiting Technical Recruiter', expectedValid: false },
  { name: 'Volunteer Experience', expectedValid: false },
  { name: 'Recent Activity', expectedValid: false },

  // Legitimate Human Names
  { name: 'Meagan Garnett', expectedValid: true },
  { name: 'Alexandra Fotos', expectedValid: true },
  { name: 'Kelsei Martinez', expectedValid: true },
  { name: 'Judy Mackesy', expectedValid: true },
  { name: 'Ronit Ron', expectedValid: true },
  { name: 'Jessica Eisenberg', expectedValid: true },
];

console.log('================================================================================');
console.log('RUNNING UI ACTION & NOISE FILTER REGRESSION TEST');
console.log('================================================================================');

let passed = 0;
tests.forEach(({ name, expectedValid }) => {
  const res = window.TalentScout.validateHumanName(name);
  const isValid = res.isValid;
  if (isValid === expectedValid) {
    console.log(`[PASS] "${name}" -> Valid: ${isValid} (Expected: ${expectedValid})`);
    passed++;
  } else {
    console.error(`[FAIL] "${name}" -> Valid: ${isValid} (Expected: ${expectedValid}, Reason: ${res.reason})`);
  }
});

if (passed === tests.length) {
  console.log('\n>>> UI ACTION & NOISE FILTER: 100% PASSED! <<<');
  process.exit(0);
} else {
  console.error(`\nFAILED: ${tests.length - passed} test(s) failed`);
  process.exit(1);
}
