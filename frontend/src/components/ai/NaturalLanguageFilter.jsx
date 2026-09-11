import React, { useState } from 'react'
import { toast } from 'react-hot-toast'
import api from '../../services/api'

/**
 * Natural Language Semantic Filter Builder
 * Converts plain English into structured, visible filter chips and applies them
 * to the surrounding directory/search page.
 */
export default function NaturalLanguageFilter({ onApplyFilters }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeChips, setActiveChips] = useState([])

  const handleParse = async (e) => {
    if (e) e.preventDefault()
    if (!input.trim()) return

    try {
      setLoading(true)
      const res = await api.post('/ai/search-filter', { query: input })
      const data = res.data

      const chips = []
      if (data.company) chips.push({ key: 'company', label: `Company: ${data.company}`, value: data.company })
      if (data.state) chips.push({ key: 'state', label: `State: ${data.state}`, value: data.state })
      if (data.title) chips.push({ key: 'title', label: `Role: ${data.title}`, value: data.title })
      if (data.has_phone) chips.push({ key: 'has_phone', label: 'Has Phone', value: true })
      if (data.missing_email) chips.push({ key: 'missing_email', label: 'Missing Email', value: true })

      setActiveChips(chips)
      if (onApplyFilters) {
        onApplyFilters(data)
      }
      toast.success(`Parsed ${chips.length} filter tags!`)
    } catch (err) {
      console.error('Filter parse error:', err)
      toast.error('Failed to parse query.')
    } finally {
      setLoading(false)
    }
  }

  const handleRemoveChip = (key) => {
    const updated = activeChips.filter((c) => c.key !== key)
    setActiveChips(updated)
    const newFilters = {}
    updated.forEach((c) => {
      newFilters[c.key] = c.value
    })
    if (onApplyFilters) {
      onApplyFilters(newFilters)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        backgroundColor: 'var(--bg-card, #121214)',
        border: '1px solid var(--border-ai, rgba(161, 161, 170, 0.25))',
        borderRadius: '8px',
        padding: '12px 16px'
      }}
    >
      <form onSubmit={handleParse} style={{ display: 'flex', gap: '8px' }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Conversational filter... (e.g. 'Engineers in Texas with phone numbers')"
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-base, #0b0b0c)',
              border: '1px solid var(--border, #232326)',
              borderRadius: '6px',
              padding: '8px 12px',
              fontSize: '12px',
              color: 'var(--text-primary)',
              outline: 'none',
              boxSizing: 'border-box'
            }}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            background: 'linear-gradient(135deg, #a1a1aa, #e4e4e7)',
            border: 'none',
            borderRadius: '6px',
            padding: '0 14px',
            color: '#fff',
            fontSize: '12px',
            fontWeight: 700,
            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
            opacity: loading || !input.trim() ? 0.6 : 1
          }}
        >
          {loading ? 'Parsing...' : 'Apply Filter'}
        </button>
      </form>

      {/* Active Filter Chips */}
      {activeChips.length > 0 && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>Active Filters:</span>
          {activeChips.map((chip) => (
            <span
              key={chip.key}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'rgba(228, 228, 231, 0.1)',
                border: '1px solid rgba(228, 228, 231, 0.3)',
                borderRadius: '4px',
                padding: '2px 8px',
                fontSize: '11px',
                color: '#e4e4e7',
                fontWeight: 600
              }}
            >
              <span>{chip.label}</span>
              <button
                onClick={() => handleRemoveChip(chip.key)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#e4e4e7',
                  cursor: 'pointer',
                  padding: 0,
                  fontSize: '11px',
                  lineHeight: 1
                }}
              >
                ✕
              </button>
            </span>
          ))}
          <button
            onClick={() => {
              setActiveChips([])
              if (onApplyFilters) onApplyFilters({})
            }}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '11px',
              cursor: 'pointer',
              textDecoration: 'underline'
            }}
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  )
}
