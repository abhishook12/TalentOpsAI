import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../services/api'

export function useRecruiters(page = 1, search = '', filters = {}) {
  return useQuery({
    queryKey: ['recruiters', page, search, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', page)
      params.append('limit', '50')
      
      if (search) params.append('search', search)
      if (filters.state) params.append('state', filters.state)
      if (filters.metro_hub) params.append('metro_hub', filters.metro_hub)
      if (filters.company_id) params.append('company_id', filters.company_id)
      if (filters.specialization_sector) params.append('specialization_sector', filters.specialization_sector)
      if (filters.seniority_level) params.append('seniority_level', filters.seniority_level)
      if (filters.timezone_code) params.append('timezone_code', filters.timezone_code)
      if (filters.company_scale) params.append('company_scale', filters.company_scale)
      if (filters.is_deliverable === 'yes') params.append('is_deliverable', 'true')
      if (filters.is_deliverable === 'no') params.append('is_deliverable', 'false')
      if (filters.has_phone === 'yes') params.append('has_phone', 'true')
      if (filters.has_phone === 'no') params.append('has_phone', 'false')
      if (filters.missing_email === 'yes') params.append('missing_email', 'true')
      if (filters.missing_email === 'no') params.append('missing_email', 'false')
      if (filters.status === 'active') params.append('is_active', 'true')
      if (filters.status === 'inactive') params.append('is_active', 'false')
      if (filters.needs_review === 'yes') params.append('needs_review', 'true')
      if (filters.state_status) params.append('state_status', filters.state_status)
      if (filters.email_inference_status) params.append('email_inference_status', filters.email_inference_status)
      if (filters.sort_by) params.append('sort_by', filters.sort_by)
      if (filters.sort_desc) params.append('sort_desc', filters.sort_desc === 'true' ? 'true' : 'false')

      const { data } = await api.get(`/recruiters/?${params.toString()}`)
      return data
    },
    keepPreviousData: true,
  })
}

export function usePrefetchRecruiters(page, search, filters) {
  const queryClient = useQueryClient()
  
  return () => {
    const params = new URLSearchParams()
    params.append('page', page + 1)
    params.append('limit', '50')
    if (search) params.append('search', search)
    queryClient.prefetchQuery({
      queryKey: ['recruiters', page + 1, search, filters],
      queryFn: async () => {
        const { data } = await api.get(`/recruiters/?${params.toString()}`)
        return data
      },
    })
  }
}
