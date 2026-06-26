function pickFirstText(selectors, root = document) {
  for (const selector of selectors) {
    const element = root.querySelector(selector)
    const text = element?.textContent?.trim()
    if (text) {
      return text.replace(/\s+/g, " ")
    }
  }
  return ""
}

function pickCompany() {
  const topCardText = pickFirstText([
    ".pv-text-details__right-panel .inline-show-more-text",
    ".pv-text-details__right-panel a",
    ".top-card-layout__card .topcard__org-name-link",
    ".top-card-layout__first-subline a"
  ])

  if (topCardText) {
    return topCardText
  }

  const experienceSection = document.querySelector("#experience, section[id*='experience']")
  return pickFirstText([
    "li .display-flex.align-items-center .t-bold span[aria-hidden='true']",
    "li .t-bold span[aria-hidden='true']",
    "li .hoverable-link-text span[aria-hidden='true']"
  ], experienceSection || document)
}

function scrapeLinkedInProfile() {
  const pathname = window.location.pathname || ""
  const isProfilePage = /^\/(in|pub)\//.test(pathname)

  if (!isProfilePage) {
    throw new Error("This page is not a LinkedIn profile.")
  }

  const name = pickFirstText([
    "h1",
    ".text-heading-xlarge",
    ".top-card-layout__title"
  ])

  const title = pickFirstText([
    ".text-body-medium.break-words",
    ".top-card-layout__headline",
    ".pv-text-details__left-panel .text-body-medium"
  ])

  const location = pickFirstText([
    ".text-body-small.inline.t-black--light.break-words",
    ".top-card__subline-item",
    ".pv-text-details__left-panel .text-body-small"
  ])

  const company = pickCompany()

  if (!name && !title && !location && !company) {
    throw new Error("No profile data could be extracted from this page.")
  }

  return {
    recruiter_name: name || null,
    title: title || null,
    location: location || null,
    company_name: company || null,
    linkedin_url: window.location.href,
    source: "linkedin_chrome_extension",
    scraped_at: new Date().toISOString()
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "SCRAPE_LINKEDIN_PROFILE") {
    return
  }

  try {
    sendResponse({
      ok: true,
      profile: scrapeLinkedInProfile()
    })
  } catch (error) {
    sendResponse({
      ok: false,
      error: error.message || "Scrape failed."
    })
  }
})
