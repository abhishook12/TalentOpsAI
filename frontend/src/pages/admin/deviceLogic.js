/**
 * deviceLogic.js
 * Risk engine + time/CSV/forensics helpers for Trusted Devices
 */

// Format relative time (e.g., "3h ago")
export function formatRelativeTime(dateString) {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffSec = Math.floor(diffMs / 1000)
  
  if (diffSec < 60) return 'Just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  return `${Math.floor(diffSec / 86400)}d ago`
}

// Format exact datetime for hover
export function formatExactDate(dateString) {
  if (!dateString) return 'Unknown'
  return new Date(dateString).toLocaleString()
}

// Generate CSV from devices array
export function exportToCSV(devices) {
  const headers = ['ID', 'Device Name', 'User', 'Email', 'Type', 'Status', 'IP', 'Location', 'Last Seen', 'Risk Score']
  const rows = devices.map(d => [
    d.id,
    d.device_name || 'Unknown Device',
    d.user_name || 'Unknown',
    d.user_email || 'Unknown',
    d.device_type || 'generic',
    d.status || 'Pending',
    d.ip_address || 'Unknown',
    d.location || 'Unknown',
    d.last_seen || 'Unknown',
    computeRisk(d).score
  ])
  
  let csvContent = 'data:text/csv;charset=utf-8,' 
    + headers.join(',') + '\n' 
    + rows.map(e => e.map(cell => `"${(cell||'').toString().replace(/"/g, '""')}"`).join(',')).join('\n')
  
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')
  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `trusted_devices_export_${new Date().toISOString().split('T')[0]}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

// Generate Forensics Dump
export function copyForensics(device) {
  const risk = computeRisk(device)
  const text = `
DEVICE FORENSICS DUMP
---------------------
ID: ${device.id}
User: ${device.user_name} (${device.user_email})
Device: ${device.device_name} [${device.device_type}]
Status: ${device.status}

Risk Score: ${risk.score}/100
Signals:
${risk.signals.map(s => ` - [${s.weight > 0 ? '+' : ''}${s.weight}] ${s.reason}`).join('\n') || ' - None'}

Network:
 - IP: ${device.ip_address}
 - Location: ${device.location}
 - Tags: ${(device.tags || []).join(', ')}

Activity:
 - First Seen: ${device.first_seen}
 - Last Seen: ${device.last_seen}
 - Active Sessions: ${device.active_sessions || 0}

User Agent:
 ${device.user_agent || 'Unknown'}
---------------------
Generated at: ${new Date().toISOString()}
  `.trim()

  navigator.clipboard.writeText(text)
  return true
}

// SLA Logic
export function getSLA(firstSeen) {
  if (!firstSeen) return { text: 'waiting ?', overThreshold: false }
  
  const date = new Date(firstSeen)
  const now = new Date()
  const diffMs = now - date
  const hours = Math.floor(diffMs / 3600000)
  
  const overThreshold = hours > 12 // e.g. 12 hour SLA
  return { 
    text: `waiting ${hours}h`, 
    overThreshold,
    hours
  }
}

// Risk Engine
export function computeRisk(device) {
  let score = 0
  const signals = []
  
  // Example heuristics. In reality, a backend does this.
  // We'll mock some signals based on device data properties
  
  if (device.tags && device.tags.includes('vpn')) {
    score += 15
    signals.push({ weight: 15, reason: 'VPN/Proxy detected' })
  }
  
  if (device.location && !device.location.includes('US') && !device.location.includes('UK')) {
    score += 20
    signals.push({ weight: 20, reason: 'Unusual geography' })
  }
  
  // Fake impossible travel for demo (just randomizer based on ID to remain stable)
  const hash = (device.id || '').split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
  if (hash % 7 === 0) {
    score += 40
    signals.push({ weight: 40, reason: 'Impossible travel detected' })
  }
  
  if (hash % 5 === 0) {
    score += 30
    signals.push({ weight: 30, reason: 'Unknown/New IP range' })
  }
  
  // Cap at 100
  if (score > 100) score = 100
  
  let level = 'LOW'
  if (score >= 40) level = 'MED'
  if (score >= 75) level = 'HIGH'
  
  return { score, signals, level }
}
