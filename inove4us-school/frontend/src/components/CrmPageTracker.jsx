import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { trackPageview } from '../lib/tracking'

/** Dispara pageview CRM a cada mudança de rota. */
export default function CrmPageTracker() {
  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    const path = `${location.pathname}${location.search}`
    void trackPageview(path, user?.id ?? null)
  }, [location.pathname, location.search, user?.id])

  return null
}
