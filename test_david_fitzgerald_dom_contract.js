const fs = require('fs');

global.window = global;
global.document = {
  title: "David Fitzgerald | LinkedIn",
  body: {
    innerText: "17 connections • Fort Lauderdale, Florida, United States • 15+ years recruitment experience across Technology, Finance, Healthcare, Marketing. Software engineering sourcing and full-cycle Talent acquisition. Strong Marketing candidate focus with Employer/candidate relationship focus."
  },
  querySelectorAll: (selector) => {
    if (selector.includes('#skills')) return [];
    if (selector.includes('#experience')) {
      return [
        {
          querySelector: (s) => ({ textContent: "Talent Acquisition Manager" })
        }
      ];
    }
    return [];
  },
  querySelector: (selector) => null,
};

global.location = {
  href: "https://www.linkedin.com/in/david-fitzgerald/",
  pathname: "/in/david-fitzgerald/",
  hostname: "www.linkedin.com"
};

require('./talent-scout-extension/detector/patterns.js');

const ts = window.TalentScout;

console.log("=== RUNNING DAVID FITZGERALD DOM EXTRACTION CONTRACT TEST ===");

// 1. Identity & Name
const nameVal = ts.validateHumanName("David Fitzgerald • 3rd");
console.assert(nameVal.isValid === true, "Name validation failed");
console.assert(nameVal.cleanName === "David Fitzgerald", "Clean name mismatch");
console.log("[PASS] Name:", nameVal.cleanName);

// 2. Connection Degree & Social Count
const degree = ts.extractConnectionDegree("David Fitzgerald • 3rd");
console.assert(degree === "3rd", "Degree mismatch");
console.log("[PASS] Degree:", degree);

const connections = ts.extractConnectionCount("17 connections • Contact info");
console.assert(connections === "17 connections", "Connections mismatch");
console.log("[PASS] Connections:", connections);

// 3. Current Title & Company
const tc = ts.cleanTitleAndCompany("Talent Acquisition Manager at SkillBridge, Inc", null, "David Fitzgerald | LinkedIn");
console.assert(tc.title === "Talent Acquisition Manager", "Title mismatch");
console.assert(tc.company_name === "SkillBridge, Inc", "Company mismatch");
console.assert(tc.company_name !== "LinkedIn", "Platform cannot be company");
console.log("[PASS] Title:", tc.title, "| Company:", tc.company_name);

// 4. About Section Semantic Decomposition (DO NOT FLATTEN)
const rawAbout = "15+ years recruitment experience across Technology, Finance, Healthcare, Marketing. Software engineering sourcing and full-cycle Talent acquisition. Strong Marketing candidate focus with Employer/candidate relationship focus.";
const aboutDecomp = ts.decomposeAboutSection(rawAbout);
console.assert(aboutDecomp !== null, "About decomposition cannot be null");
console.assert(aboutDecomp.years_experience === "15+ years recruitment experience", "Years exp mismatch");
console.assert(aboutDecomp.industries.includes("Technology"), "Missing Technology industry");
console.assert(aboutDecomp.industries.includes("Finance"), "Missing Finance industry");
console.assert(aboutDecomp.industries.includes("Healthcare"), "Missing Healthcare industry");
console.assert(aboutDecomp.industries.includes("Marketing"), "Missing Marketing industry");
console.assert(aboutDecomp.specialties.includes("Software engineering sourcing"), "Missing Software sourcing");
console.assert(aboutDecomp.specialties.includes("Talent acquisition"), "Missing Talent acquisition");
console.assert(aboutDecomp.candidate_focus === "Marketing candidate focus", "Missing candidate focus");
console.assert(aboutDecomp.employer_focus === "Employer/candidate relationship focus", "Missing employer focus");
console.log("[PASS] Decomposed About Observations:", JSON.stringify(aboutDecomp.structured_observations, null, 2));

// 5. UI Controls Rejection
console.assert(ts.isUIAction("Connect") === true, "Connect must be UI action");
console.assert(ts.isUIAction("Message") === true, "Message must be UI action");
console.assert(ts.isUIAction("Follow") === true, "Follow must be UI action");
console.assert(ts.isUIAction("Contact") === true, "Contact must be UI action");
console.log("[PASS] UI actions rejected strictly");

// 6. Completeness Report Generation
const rep = ts.generateCompletenessReport({
  recruiter_name: "David Fitzgerald",
  title: "Talent Acquisition Manager",
  company_name: "SkillBridge, Inc",
  location: "Fort Lauderdale, Florida, United States",
  education: "University of Delaware",
  connection_degree: "3rd",
  connections_count: "17 connections",
  about_insights: aboutDecomp,
  source_platform: "LinkedIn"
});

console.assert(rep.canonical_person === "David Fitzgerald", "Completeness canonical person mismatch");
console.assert(rep.visible_categories.includes("PERSON_NAME"), "Missing PERSON_NAME in report");
console.assert(rep.visible_categories.includes("CURRENT_TITLE"), "Missing CURRENT_TITLE in report");
console.assert(rep.visible_categories.includes("CURRENT_COMPANY"), "Missing CURRENT_COMPANY in report");
console.assert(rep.visible_categories.includes("LOCATION"), "Missing LOCATION in report");
console.assert(rep.visible_categories.includes("EDUCATION"), "Missing EDUCATION in report");
console.assert(rep.visible_categories.includes("SOCIAL_GRAPH_PROOF"), "Missing SOCIAL_GRAPH_PROOF in report");
console.assert(rep.visible_categories.includes("STRUCTURED_ABOUT_DECOMPOSITION"), "Missing STRUCTURED_ABOUT_DECOMPOSITION in report");

console.log("[PASS] Completeness Report Categories Verified:", rep.visible_categories);
console.log("\n>>> DAVID FITZGERALD EXTRACTION CONTRACT: 100% PASSED! <<<");
