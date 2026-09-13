import { Navigate, Route, Routes } from 'react-router-dom';
import { CatalogSelectionProvider } from './admin/CatalogSelectionContext';
import HomePage from './admin/HomePage';
import CatalogPage from './admin/CatalogPage';
import OpportunitiesPage from './admin/OpportunitiesPage';
import OpportunityDetailPage from './admin/OpportunityDetailPage';
import DemonstrationsPage from './admin/DemonstrationsPage';
import DemonstrationDetailPage from './admin/DemonstrationDetailPage';
import AdminShell from './components/AdminShell';
import PublicInvitePage from './public/PublicInvitePage';
import SegSenseHomePage from './public/SegSenseHomePage';
import IcatuDemonstrationPage from './demonstration/IcatuDemonstrationPage';
import IntegratedMvpPage from './demonstration/IntegratedMvpPage';

export default function App() {
  return (
    <CatalogSelectionProvider>
      <Routes>
        <Route path="/" element={<SegSenseHomePage />} />
        <Route path="/admin" element={<AdminShell />}>
          <Route index element={<HomePage />} />
          <Route path="catalogo" element={<CatalogPage />} />
          <Route path="oportunidades" element={<OpportunitiesPage />} />
          <Route path="oportunidades/:opportunityId" element={<OpportunityDetailPage />} />
          <Route path="demonstracoes" element={<DemonstrationsPage />} />
          <Route path="demonstracoes/:storyKey" element={<DemonstrationDetailPage />} />
        </Route>
        <Route path="/c/:token" element={<PublicInvitePage />} />
        <Route path="/demonstracao/icatu" element={<IcatuDemonstrationPage />} />
        <Route path="/demonstracao/mvp-integrado" element={<IntegratedMvpPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </CatalogSelectionProvider>
  );
}
