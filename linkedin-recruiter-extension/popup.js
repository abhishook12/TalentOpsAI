const els = {
  apiUrl: document.getElementById("apiUrl"),
  authToken: document.getElementById("authToken"),
  saveSettings: document.getElementById("saveSettings"),
  saveStatus: document.getElementById("saveStatus"),
  actionStatus: document.getElementById("actionStatus"),
  scrapeProfile: document.getElementById("scrapeProfile"),
  sendProfile: document.getElementById("sendProfile"),
  profilePreview: document.getElementById("profilePreview")
}

let latestProfile = null

function setPill(element, text, tone = "default") {
  element.textContent = text
  element.className = `pill${tone === "default" ? "" : ` ${tone}`}`
}

function renderProfile(profile) {
  latestProfile = profile || null
  if (!profile) {
    els.profilePreview.textContent = "Open a LinkedIn profile, then click scrape."
    els.profilePreview.classList.add("empty")
    return
  }

  els.profilePreview.classList.remove("empty")
  els.profilePreview.textContent = JSON.stringify(profile, null, 2)
}

function sendMessage(message) {
  return chrome.runtime.sendMessage(message)
}

async function loadSettings() {
  const response = await sendMessage({ type: "GET_SETTINGS" })
  if (!response?.ok) {
    throw new Error(response?.error || "Could not load settings.")
  }

  els.apiUrl.value = response.settings.apiUrl || ""
  els.authToken.value = response.settings.authToken || ""
  setPill(els.saveStatus, "Loaded", "muted")
}

async function loadLastProfile() {
  const response = await sendMessage({ type: "GET_LAST_PROFILE" })
  if (response?.ok && response.lastProfile) {
    renderProfile(response.lastProfile)
    setPill(els.actionStatus, "Last capture loaded", "muted")
  }
}

async function handleSaveSettings() {
  setPill(els.saveStatus, "Saving...", "warning")
  const response = await sendMessage({
    type: "SAVE_SETTINGS",
    settings: {
      apiUrl: els.apiUrl.value,
      authToken: els.authToken.value
    }
  })

  if (!response?.ok) {
    throw new Error(response?.error || "Could not save settings.")
  }

  setPill(els.saveStatus, "Saved", "default")
}

async function handleScrape() {
  setPill(els.actionStatus, "Scraping...", "warning")
  const response = await sendMessage({ type: "SCRAPE_ACTIVE_PROFILE" })
  if (!response?.ok) {
    throw new Error(response?.error || "Could not scrape profile.")
  }

  renderProfile(response.profile)
  setPill(els.actionStatus, "Profile scraped", "default")
}

async function handleSend() {
  setPill(els.actionStatus, "Sending...", "warning")
  const response = await sendMessage({
    type: "SEND_PROFILE_TO_API",
    profile: latestProfile
  })

  if (!response?.ok) {
    throw new Error(response?.error || "Could not send profile.")
  }

  renderProfile(response.profile)
  setPill(els.actionStatus, "Sent successfully", "default")
}

els.saveSettings.addEventListener("click", () => {
  handleSaveSettings().catch((error) => {
    setPill(els.saveStatus, "Save failed", "error")
    setPill(els.actionStatus, error.message || "Error", "error")
  })
})

els.scrapeProfile.addEventListener("click", () => {
  handleScrape().catch((error) => {
    setPill(els.actionStatus, error.message || "Scrape failed", "error")
  })
})

els.sendProfile.addEventListener("click", () => {
  handleSend().catch((error) => {
    setPill(els.actionStatus, error.message || "Send failed", "error")
  })
})

Promise.all([loadSettings(), loadLastProfile()]).catch((error) => {
  setPill(els.actionStatus, error.message || "Startup error", "error")
})
