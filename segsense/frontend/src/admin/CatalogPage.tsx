import { useNavigate } from 'react-router-dom';
import CatalogAdmin from '../catalog/CatalogAdmin';
import { useCatalogSelection } from './CatalogSelectionContext';

export default function CatalogPage() {
  const navigate = useNavigate();
  const { setSelection } = useCatalogSelection();

  return (
    <CatalogAdmin
      onReadyForOpportunities={(selection) => {
        setSelection(selection);
        void navigate('/admin/oportunidades');
      }}
    />
  );
}
