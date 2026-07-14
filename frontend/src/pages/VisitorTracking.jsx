import React, { useState } from 'react'
import { useSessionState } from '../hooks/useSessionState'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { Activity, Globe, Monitor, Search, RefreshCw, UserCircle, MapPin } from 'lucide-react'
import api from '../services/api'

export default function VisitorTracking() {
  const [searchTerm, setSearchTerm] = useSessionState('vt_searchTerm', '')

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ['visitor-logs'],
    queryFn: async () => {
      const res = await api.get('/analytics/visitor-logs?limit=200')
      return res.data
    },
    refetchInterval: 30000 // Refresh every 30s automatically
  })

  const logs = data?.logs || []

  // Filter logs locally
  const filteredLogs = logs.filter(log => {
    if (!searchTerm) return true
    const search = searchTerm.toLowerCase()
    return (
      (log.page || '').toLowerCase().includes(search) ||
      (log.path || '').toLowerCase().includes(search) ||
      (log.user_email || '').toLowerCase().includes(search) ||
      (log.ip_address || '').toLowerCase().includes(search) ||
      (log.os || '').toLowerCase().includes(search) ||
      (log.browser || '').toLowerCase().includes(search)
    )
  })

  return (
    <>
      <div className="flex flex-col h-full space-y-6 animate-fade-in">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <Activity className="h-6 w-6 text-brand-400" />
              Visitor Tracking
            </h1>
            <p className="text-slate-400 mt-1 text-sm">
              Real-time monitoring of user sessions and page visits across the application.
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search logs..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-9 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-sm text-white placeholder-slate-400 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-colors w-64"
              />
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center justify-center h-9 w-9 bg-slate-800/80 border border-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh Data"
            >
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
            <p className="text-red-400 text-sm">Failed to load visitor logs. Please try again.</p>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex-1 min-h-0 bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden flex flex-col">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 p-4 border-b border-slate-700/50 bg-slate-800/50 text-xs font-semibold text-slate-400 uppercase tracking-wider sticky top-0 z-10">
            <div className="col-span-3">Timestamp & User</div>
            <div className="col-span-3">Page Visited</div>
            <div className="col-span-2">Device & OS</div>
            <div className="col-span-2">IP Address</div>
            <div className="col-span-2 text-right">Time Spent</div>
          </div>

          {/* Table Body */}
          <div className="flex-1 overflow-y-auto min-h-[400px]">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-500 p-8">
                <Activity className="h-12 w-12 mb-4 opacity-20" />
                <p>No visitor logs found.</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-700/30">
                {filteredLogs.map((log) => (
                  <div 
                    key={log.id} 
                    className="grid grid-cols-12 gap-4 p-4 items-center hover:bg-slate-700/20 transition-colors group text-sm"
                  >
                    <div className="col-span-3">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                          {log.user_email ? (
                            <span className="text-brand-300 font-medium text-xs">{log.user_email.charAt(0).toUpperCase()}</span>
                          ) : (
                            <UserCircle className="h-5 w-5 text-slate-500" />
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="text-white truncate font-medium">
                            {log.user_email || 'Anonymous Visitor'}
                          </p>
                          <p className="text-slate-400 text-xs truncate">
                            {log.timestamp ? format(new Date(log.timestamp), 'MMM d, h:mm:ss a') : 'Unknown Time'}
                          </p>
                        </div>
                      </div>
                    </div>
                    
                    <div className="col-span-3 flex flex-col justify-center min-w-0">
                      <span className="text-white font-medium truncate">{log.page || 'Unknown Page'}</span>
                      <span className="text-slate-400 text-xs truncate font-mono mt-0.5">{log.path}</span>
                    </div>
                    
                    <div className="col-span-2 flex items-center gap-2 min-w-0 text-slate-300">
                      <Monitor className="h-4 w-4 text-slate-500 flex-shrink-0" />
                      <span className="truncate">{log.os} • {log.browser}</span>
                    </div>

                    <div className="col-span-2 flex items-center gap-2 min-w-0 text-slate-300">
                      <Globe className="h-4 w-4 text-slate-500 flex-shrink-0" />
                      <span className="truncate font-mono text-xs">{log.ip_address}</span>
                    </div>

                    <div className="col-span-2 text-right">
                      <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${
                        log.time_on_page && log.time_on_page > 60 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : 'bg-slate-700/50 text-slate-300 border border-slate-600/50'
                      }`}>
                        {log.time_on_page ? `${Math.round(log.time_on_page)}s` : '—'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
