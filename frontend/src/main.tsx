import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Ensure consistent multi-tenant session isolation across all API calls
const getSessionId = (): string => {
  let sid = localStorage.getItem('ada_session_id')
  if (!sid) {
    sid = 'usr_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36)
    localStorage.setItem('ada_session_id', sid)
  }
  return sid
}

// Global fetch wrapper to attach X-Session-ID and credentials to all /api calls
const originalFetch = window.fetch
window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as Request).url
  if (typeof url === 'string' && url.includes('/api')) {
    const headers = new Headers(init?.headers || (typeof input === 'object' && 'headers' in input ? (input as Request).headers : {}))
    if (!headers.has('X-Session-ID')) {
      headers.set('X-Session-ID', getSessionId())
    }
    const modifiedInit: RequestInit = {
      ...init,
      headers,
      credentials: 'include',
    }
    return originalFetch(input, modifiedInit)
  }
  return originalFetch(input, init)
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
