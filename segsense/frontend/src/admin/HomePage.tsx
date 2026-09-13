import HumanStatus from '../components/HumanStatus';
import { AUTH_NOT_CONFIGURED } from '../i18n/human';

export default function HomePage() {
  return (
    <article className="page-block">
      <p className="breadcrumb">Início</p>
      <h1>Ambiente editorial</h1>
      <p>
        Esta área organiza o catálogo e as oportunidades contextuais do SegSense. Não é uma
        jornada de cotação, recomendação ou contratação.
      </p>
      <HumanStatus kind="info" title="Acesso administrativo" headingLevel="h2">
        <p>{AUTH_NOT_CONFIGURED} Não há tela de entrada nesta etapa.</p>
      </HumanStatus>
    </article>
  );
}
