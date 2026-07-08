import { useRef, useState } from 'react'
import { ChevronLeft, LogIn } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import Brand from './Brand.jsx'
import { loginAdmin, salvarSessaoAdmin } from '../services/adminAuth.js'

function TopBar({ showBack = false, backTo = -1 }) {
  const navigate = useNavigate()
  const inputRef = useRef(null)
  const [adminSenha, setAdminSenha] = useState('')
  const [shake, setShake] = useState(false)
  const [erroLogin, setErroLogin] = useState(false)
  const [mensagemErro, setMensagemErro] = useState('')
  const [entrando, setEntrando] = useState(false)

  const handleBack = () => {
    if (typeof backTo === 'function') {
      backTo()
    } else {
      navigate(backTo)
    }
  }

  const handleAdminLogin = async (event) => {
    event.preventDefault()
    if (entrando) return

    const password = adminSenha.trim()
    if (!password) return

    setEntrando(true)
    setErroLogin(false)
    setMensagemErro('')

    try {
      const data = await loginAdmin(password)
      salvarSessaoAdmin(data.token)
      setAdminSenha('')
      navigate('/admin')
    } catch (err) {
      const msg =
        err?.response?.data?.erro ||
        (err?.message?.includes('Network') ? 'Não foi possível conectar à API.' : 'Senha inválida.')
      setMensagemErro(msg)
      setErroLogin(true)
      setShake(true)
      window.setTimeout(() => {
        setShake(false)
      }, 1200)
      inputRef.current?.focus()
    } finally {
      setEntrando(false)
    }
  }

  return (
    <div className="topbar">
      <Brand />

      {showBack ? (
        <button type="button" className="back-btn" onClick={handleBack}>
          <ChevronLeft size={18} />
          Voltar
        </button>
      ) : (
        <form
          className={`admin-login${shake ? ' admin-login--shake' : ''}${erroLogin ? ' admin-login--erro' : ''}`}
          onSubmit={handleAdminLogin}
        >
          <span className="admin-login-label">Login administrativo</span>
          <input
            ref={inputRef}
            type="password"
            value={adminSenha}
            onChange={(e) => setAdminSenha(e.target.value)}
            autoComplete="current-password"
            placeholder="Senha"
            aria-label="Senha administrativa"
            disabled={entrando}
            className="admin-login-input"
          />
          <button type="submit" className="admin-login-btn" disabled={entrando}>
            <LogIn size={15} />
            {entrando ? 'Entrando…' : 'Entrar'}
          </button>
          {mensagemErro && (
            <span className="admin-login-erro" role="alert">
              {mensagemErro}
            </span>
          )}
        </form>
      )}
    </div>
  )
}

export default TopBar
