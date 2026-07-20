import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

export function useAnalytics(companyId = null, filterState = 'All') {
  return useQuery({
    queryKey: ['analytics', companyId, filterState],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (companyId) params.append('company_id', companyId)
      if (filterState && filterState !== 'All') params.append('state', filterState)
      
      const [dbRes, qualityRes, companyRes, activityRes] = await Promise.all([
        api.get(`/analytics/dashboard?${params.toString()}`),
        api.get(`/analytics/data-quality?${params.toString()}`),
        api.get(`/analytics/company-breakdown?${params.toString()}`),
        api.get('/analytics/global-activity?limit=50')
      ])
      
      return {
        dashboard: dbRes.data,
        quality: qualityRes.data,
        companies: companyRes.data,
        activity: activityRes.data
      }
    },
    staleTime: 1000 * 60 * 5, // 5 min cache for analytics is crucial for speed
  })
}

export function useExecutiveReport() {
  return useQuery({
    queryKey: ['executive-report'],
    queryFn: async () => {
      const res = await api.get('/analytics/executive-report-json')
      return res.data
    },
    staleTime: 1000 * 60 * 60, // 1 hour cache
  })
}
