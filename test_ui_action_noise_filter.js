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
  { name: 'Harsh Kumar accepted your invitation to connect.', expectedValid: false },

  // Trailing Role/Title cleanup
  { name: 'Aditi Chauhan SAP SuccessFactors', expectedValid: true, expectedClean: 'Aditi Chauhan' },
  { name: 'Jitendra Tripathi Founder', expectedValid: true, expectedClean: 'Jitendra Tripathi' },

  // Legitimate Human Names
  { name: 'Meagan Garnett', expectedValid: true, expectedClean: 'Meagan Garnett' },
  { name: 'Alexandra Fotos', expectedValid: true, expectedClean: 'Alexandra Fotos' },
  { name: 'Kelsei Martinez', expectedValid: true, expectedClean: 'Kelsei Martinez' },
  { name: 'Judy Mackesy', expectedValid: true, expectedClean: 'Judy Mackesy' },
  { name: 'Harsh Kumar', expectedValid: true, expectedClean: 'Harsh Kumar' },
  { name: 'Mughis Siddiqui', expectedValid: true, expectedClean: 'Mughis Siddiqui' },
  { name: 'Ravinder Prakash', expectedValid: true, expectedClean: 'Ravinder Prakash' },
];

console.log('================================================================================');
console.log('RUNNING UI ACTION & NOISE FILTER REGRESSION TEST');
console.log('================================================================================');

let passed = 0;
tests.forEach(({ name, expectedValid, expectedClean }) => {
  const res = window.TalentScout.validateHumanName(name);
  const isValid = res.isValid;
  const matchesClean = expectedClean ? (res.cleanName === expectedClean) : true;
  if (isValid === expectedValid && matchesClean) {
    console.log(`[PASS] "${name}" -> Valid: ${isValid}, Clean: "${res.cleanName || 'N/A'}" (Expected: ${expectedValid}, "${expectedClean || 'N/A'}")`);
    passed++;
  } else {
    console.error(`[FAIL] "${name}" -> Valid: ${isValid}, Clean: "${res.cleanName || 'N/A'}" (Expected: ${expectedValid}, "${expectedClean || 'N/A'}", Reason: ${res.reason})`);
  }
});

if (passed === tests.length) {
  console.log('\n>>> UI ACTION & NOISE FILTER: 100% PASSED! <<<');
  process.exit(0);
} else {
  console.error(`\nFAILED: ${tests.length - passed} test(s) failed`);
  process.exit(1);
}
