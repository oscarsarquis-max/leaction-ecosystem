import { Navigate } from 'react-router-dom'
import { isAdminLogado } from '../services/adminAuth.js'

function ProtectedAdmin({ children }) {
  if (!isAdminLogado()) {
    return <Navigate to="/" replace />
  }
  return children
}

export default ProtectedAdmin
