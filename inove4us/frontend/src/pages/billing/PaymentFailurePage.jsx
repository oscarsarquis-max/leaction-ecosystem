import { Link } from 'react-router-dom'
import BrandLogo from '../../components/BrandLogo'

export default function PaymentFailurePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <BrandLogo
        variant="internal"
        className="mb-8 h-20 w-auto max-w-[280px] object-contain"
      />
      <div className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-8 text-center shadow-soft">
        <h1 className="font-display text-2xl font-bold text-bordo-deep">
          Pagamento não concluído
        </h1>
        <p className="mt-3 text-sm text-bordo-soft">
          Não foi possível confirmar o pagamento. Você pode tentar novamente quando quiser.
        </p>
        <div className="mt-8 flex flex-col gap-2 sm:flex-row sm:justify-center">
          <Link to="/mesa-do-inovador" className="btn-ghost !px-5 !py-3 text-sm">
            Voltar ao início
          </Link>
          <Link to="/mesa-do-inovador" className="btn-primary !px-5 !py-3 text-sm">
            Tentar de novo
          </Link>
        </div>
      </div>
    </div>
  )
}
