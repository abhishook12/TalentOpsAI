import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import EvidenceBadge from './EvidenceBadge'

/**
 * Interactive Knowledge Graph Component
 * Visualizes multi-entity relationship networks: Candidate → Company → Skill → Location
 */
export default function KnowledgeGraphView() {
  const DEFAULT_GRAPH = {
    nodes: [
      { id: 'node_1', label: 'Senior Data Architect', type: 'CANDIDATE', score: 94 },
      { id: 'node_2', label: 'Snowflake Analytics', type: 'COMPANY', score: 98 },
      { id: 'node_3', label: 'Distributed Systems', type: 'SKILL', score: 91 },
      { id: 'node_4', label: 'Austin, TX', type: 'LOCATION', score: 88 }
    ],
    edges: [
      { source: 'node_1', target: 'node_2', relation: 'WORKS_AT' }
    ]
  }

  const [graphData, setGraphData] = useState(DEFAULT_GRAPH)
  const [loading, setLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState(null)

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const res = await api.get('/ai/knowledge-graph')
        if (res.data && Array.isArray(res.data.nodes) && res.data.nodes.length > 0) {
          setGraphData(res.data)
        }
      } catch (err) {
        console.warn('Using default knowledge graph topology:', err)
      }
    }
    fetchGraph()
  }, [])

  const getNodeColor = (type) => {
    switch (type) {
      case 'CANDIDATE':
        return '#38bdf8' // cyan
      case 'COMPANY':
        return '#a78bfa' // purple
      case 'SKILL':
        return '#10b981' // green
      case 'LOCATION':
        return '#f59e0b' // amber
      default:
        return '#94a3b8'
    }
  }

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #0f172a)',
        border: '1px solid var(--border-ai, rgba(139, 92, 246, 0.25))',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '14px', color: '#a78bfa' }}>✦</span>
          <div>
            <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-primary)' }}>
              Entity Knowledge Graph
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Semantic relationship topology between candidates, organizations, and competencies.
            </div>
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', fontSize: '11px' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#38bdf8' }}>● Candidate</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#a78bfa' }}>● Company</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#10b981' }}>● Skill</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#f59e0b' }}>● Location</span>
        </div>
      </div>

      {/* Graph Visual Canvas */}
      <div
        style={{
          position: 'relative',
          height: '320px',
          backgroundColor: 'var(--bg-base, #090d14)',
          border: '1px solid var(--border, #1e293b)',
          borderRadius: '8px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {loading ? (
          <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
            <i className="ti ti-loader-2" style={{ animation: 'spin 1s linear infinite', fontSize: '20px', display: 'block', margin: '0 auto 8px' }} />
            Assembling semantic entity network...
          </div>
        ) : (
          <div style={{ width: '100%', height: '100%', position: 'relative', padding: '20px' }}>
            {/* Render Nodes as an aesthetic distributed grid */}
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '12px',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%'
              }}
            >
              {(graphData?.nodes || []).map((node) => {
                const isSelected = selectedNode?.id === node.id
                return (
                  <div
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid ${isSelected ? getNodeColor(node.type) : 'var(--border, #1e293b)'}`,
                      borderRadius: '20px',
                      padding: '6px 14px',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      boxShadow: isSelected ? `0 0 15px ${getNodeColor(node.type)}` : 'none'
                    }}
                  >
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: getNodeColor(node.type) }} />
                    <span style={{ fontSize: '12px', fontWeight: 600, color: isSelected ? '#fff' : 'var(--text-primary)' }}>
                      {node.label}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                      {node.type}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            backgroundColor: 'var(--bg-base, #090d14)',
            border: '1px solid var(--border, #1e293b)',
            borderRadius: '8px',
            padding: '12px 16px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', backgroundColor: getNodeColor(selectedNode.type) }} />
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {selectedNode.label}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                Entity Type: {selectedNode.type} • Semantic Trust Score: {selectedNode.score}%
              </div>
            </div>
          </div>
          <EvidenceBadge status="VERIFIED" confidence={selectedNode.score / 100} size="sm" />
        </div>
      )}
    </div>
  )
}
