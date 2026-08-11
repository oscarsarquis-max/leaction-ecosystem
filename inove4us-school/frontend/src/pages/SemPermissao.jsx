import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { firstAccessiblePath } from '../lib/rbac'

/**
 * Tela dedicada quando o gestor está autenticado mas sem a zona da rota.
 * Mesmo espírito do MarketBlocked — usada em qualquer rota do painel.
 */
export default function SemPermissao({ zonasRequired = [] }) {
  const { user } = useAuth()
  const zonas = user?.zonas || []
  const fallback = firstAccessiblePath(zonas)
  const req = Array.isArray(zonasRequired) ? zonasRequired.filter(Boolean) : []

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-lg flex-col justify-center px-4 py-16 text-center">
      <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-school-600">
        inove4us · school
      </p>
      <h1 className="mt-3 font-display text-2xl font-bold text-ink sm:text-3xl">
        Sem permissão para esta área
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-muted">
        Sua sessão está autenticada, mas não tem a zona necessária
        {req.length ? ` (${req.join(', ')})` : ''}. Peça ao administrador da escola para
        liberar o perfil correspondente em Gestão de Gestores.
      </p>
      {zonas.length === 0 ? (
        <p className="mt-2 text-sm text-amber-800">
          Nenhuma zona ativa na sua conta. Não é possível abrir o painel até haver ao menos
          um perfil ativo.
        </p>
      ) : null}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        {fallback && fallback !== '/acesso' && fallback !== '/sem-permissao' ? (
          <Link to={fallback} className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white">
            Voltar ao painel
          </Link>
        ) : (
          <Link to="/acesso" className="rounded-xl bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white">
            Ir para o acesso
          </Link>
        )}
      </div>
    </div>
  )
}
