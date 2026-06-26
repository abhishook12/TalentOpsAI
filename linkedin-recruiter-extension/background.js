const DEFAULT_SETTINGS = {
  apiUrl: "http://localhost:8000/recruiters/extension",
  authToken: ""
}

async function getSettings() {
  const stored = await chrome.storage.sync.get(DEFAULT_SETTINGS)
  return { ...DEFAULT_SETTINGS, ...stored }
}

async function getActiveLinkedInTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
  if (!tab?.id) {
    throw new Error("No active tab found.")
  }
  if (!tab.url?.includes("linkedin.com/")) {
    throw new Error("Open a LinkedIn profile tab first.")
  }
  return tab
}

async function scrapeActiveProfile() {
  const tab = await getActiveLinkedInTab()
  const response = await chrome.tabs.sendMessage(tab.id, { type: "SCRAPE_LINKEDIN_PROFILE" })
  if (!response?.ok) {
    throw new Error(response?.error || "Could not scrape the current LinkedIn profile.")
  }
  return response.profile
}

async function saveLastProfile(profile) {
  await chrome.storage.local.set({
    lastProfile: profile,
    lastScrapedAt: new Date().toISOString()
  })
}

async function postProfileToApi(profile) {
  const settings = await getSettings()
  const headers = {
    "Content-Type": "application/json"
  }

  if (settings.authToken?.trim()) {
    headers.Authorization = `Bearer ${settings.authToken.trim()}`
  }

  const response = await fetch(settings.apiUrl, {
    method: "POST",
    headers,
    body: JSON.stringify(profile)
  })

  const rawText = await response.text()
  let payload = rawText

  try {
    payload = rawText ? JSON.parse(rawText) : null
  } catch {
    payload = rawText
  }

  if (!response.ok) {
    const message =
      typeof payload === "string" && payload
        ? payload
        : payload?.detail || `Request failed with status ${response.status}`
    throw new Error(message)
  }

  await chrome.storage.local.set({
    lastSubmittedProfile: profile,
    lastSubmissionAt: new Date().toISOString(),
    lastSubmissionResponse: payload
  })

  return payload
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  ;(async () => {
    try {
      if (message?.type === "GET_SETTINGS") {
        sendResponse({ ok: true, settings: await getSettings() })
        return
      }

      if (message?.type === "SAVE_SETTINGS") {
        const nextSettings = {
          apiUrl: message.settings?.apiUrl?.trim() || DEFAULT_SETTINGS.apiUrl,
          authToken: message.settings?.authToken || ""
        }
        await chrome.storage.sync.set(nextSettings)
        sendResponse({ ok: true, settings: nextSettings })
        return
      }

      if (message?.type === "SCRAPE_ACTIVE_PROFILE") {
        const profile = await scrapeActiveProfile()
        await saveLastProfile(profile)
        sendResponse({ ok: true, profile })
        return
      }

      if (message?.type === "SEND_PROFILE_TO_API") {
        const profile = message.profile || (await scrapeActiveProfile())
        await saveLastProfile(profile)
        const result = await postProfileToApi(profile)
        sendResponse({ ok: true, result, profile })
        return
      }

      if (message?.type === "GET_LAST_PROFILE") {
        const data = await chrome.storage.local.get([
          "lastProfile",
          "lastScrapedAt",
          "lastSubmittedProfile",
          "lastSubmissionAt",
          "lastSubmissionResponse"
        ])
        sendResponse({ ok: true, ...data })
        return
      }

      sendResponse({ ok: false, error: "Unknown message type." })
    } catch (error) {
      sendResponse({ ok: false, error: error.message || "Unexpected error." })
    }
  })()

  return true
})
