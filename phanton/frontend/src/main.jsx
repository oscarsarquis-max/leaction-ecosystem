import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { AuthProvider } from './auth/AuthContext.jsx'
import AppGate from './auth/AppGate.jsx'
import { resolveApiBase } from './lib/apiBase.js'

const API_BASE = resolveApiBase()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider apiBase={API_BASE}>
      <AppGate apiBase={API_BASE}>
        <App />
      </AppGate>
    </AuthProvider>
  </StrictMode>,
)
