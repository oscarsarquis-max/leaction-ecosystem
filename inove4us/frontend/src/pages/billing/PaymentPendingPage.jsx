import { Link } from 'react-router-dom'
import BrandLogo from '../../components/BrandLogo'

export default function PaymentPendingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <BrandLogo
        variant="internal"
        className="mb-8 h-20 w-auto max-w-[280px] object-contain"
      />
      <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-8 text-center shadow-soft">
        <h1 className="font-display text-2xl font-bold text-bordo-deep">
          Pagamento em análise
        </h1>
        <p className="mt-3 text-sm text-bordo-soft">
          Assim que o Mercado Pago confirmar, seus créditos serão liberados automaticamente.
        </p>
        <Link to="/desafio" className="btn-primary mt-8 inline-flex !px-5 !py-3 text-sm">
          Voltar para Meus Planejamentos
        </Link>
      </div>
    </div>
  )
}
