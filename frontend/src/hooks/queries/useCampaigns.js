import { useQuery } from '@tanstack/react-query'
import api from '../../services/api'

export function useCampaigns(page = 1, search = '', status = 'all') {
  return useQuery({
    queryKey: ['campaigns', page, search, status],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', page)
      params.append('limit', '50')
      if (search) params.append('search', search)
      if (status) params.append('status', status)
      
      const { data } = await api.get(`/campaigns/?${params.toString()}`)
      return data
    },
    keepPreviousData: true,
  })
}
