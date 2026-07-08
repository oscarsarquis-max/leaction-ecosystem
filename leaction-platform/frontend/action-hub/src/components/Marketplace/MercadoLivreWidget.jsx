'use client';

/**
 * @deprecated Prefer MultivendorGrid ou MultivendorSearchBox.
 * Wrapper fino para compatibilidade com integrações legadas.
 */
import { MultivendorGrid } from './MultivendorGrid';

export function MercadoLivreWidget({
  title = 'Ofertas recomendadas',
  subtitle = 'Conteúdos e ferramentas selecionados para acelerar sua maturidade digital.',
  searchQuery = '',
  category = '',
  limit = 8,
  className = '',
}) {
  return (
    <MultivendorGrid
      title={title}
      subtitle={subtitle}
      query={searchQuery}
      category={category}
      limit={limit}
      className={className}
    />
  );
}

export default MercadoLivreWidget;
