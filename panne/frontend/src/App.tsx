import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProviderTree } from "./auth/AuthContext";
import { RequireAuth, RequireOrganization, RequirePermission } from "./components/RequireAuth";
import { Shell } from "./components/Shell";
import { BoardPage } from "./pages/BoardPage";
import { CallbackPage } from "./pages/CallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { OrderDetailPage } from "./pages/OrderDetailPage";
import { OrdersPage } from "./pages/OrdersPage";
import { PlanDetailPage } from "./pages/PlanDetailPage";
import { PlansPage } from "./pages/PlansPage";
import { SelectOrgPage } from "./pages/SelectOrgPage";
import { SheetPage } from "./pages/SheetPage";
import { TraceabilityHubPage, TraceabilityPage } from "./pages/TraceabilityPage";
import { ExecutePage } from "./ops/ExecutePage";
import { CatalogsPage } from "./pages/CatalogsPage";
import { HomePage } from "./pages/HomePage";
import { IngredientEditorPage } from "./pages/IngredientEditorPage";
import { IngredientsPage } from "./pages/IngredientsPage";
import { RecipeAiDetailPage } from "./pages/RecipeAiDetailPage";
import { RecipeAiHistoryPage } from "./pages/RecipeAiHistoryPage";
import { RecipeAiHubPage } from "./pages/RecipeAiHubPage";
import { RecipeAiWizardPage } from "./pages/RecipeAiWizardPage";
import { RecipeEditorPage } from "./pages/RecipeEditorPage";
import { RecipeSheetPage } from "./pages/RecipeSheetPage";
import { RecipesPage } from "./pages/RecipesPage";
import { LabelingCreatePage } from "./pages/LabelingCreatePage";
import { LabelingDossierPage } from "./pages/LabelingDossierPage";
import { LabelingDossiersPage } from "./pages/LabelingDossiersPage";
import {
  LabelingAssessmentsPage,
  LabelingCandidatesPage,
  LabelingSourcesPage,
} from "./pages/LabelingListsPage";
import { LabelingOverviewPage } from "./pages/LabelingOverviewPage";
import { CostingOverviewPage } from "./pages/CostingOverviewPage";
import {
  ReportingOverviewPage,
  ReportingReportPage,
  ReportingSavedPage,
  ReportingSnapshotPage,
} from "./pages/ReportingPages";
import {
  CostingCalculationPage,
  CostingListPage,
  CostingPoliciesPage,
  CostingPricesPage,
  CostingSimulationsPage,
} from "./pages/CostingPages";
import { SuppliersPage } from "./pages/SuppliersPage";
import {
  InventoryCountsPage,
  InventoryLotsPage,
  InventoryMovementsPage,
  InventoryOverviewPage,
  InventoryPicksPage,
  InventoryPositionPage,
  InventoryReservationsPage,
  ProcurementListPage,
  ProcurementNeedsPage,
  ProcurementQuotesPage,
} from "./pages/InventoryPages";
import { AssistantProvider } from "./assistant/AssistantContext";
import { OrganizationProvider } from "./session/OrganizationContext";

export function AppRoutes() {
  return (
          <Routes>
            <Route path="/entrar" element={<LoginPage />} />
            <Route path="/callback" element={<CallbackPage />} />
            <Route
              element={
                <RequireAuth>
                  <RequireOrganization>
                    <Shell />
                  </RequireOrganization>
                </RequireAuth>
              }
            >
              <Route path="/organizacao" element={<SelectOrgPage />} />
              <Route path="/inicio" element={<HomePage />} />
              <Route
                path="/componentes/ingredientes"
                element={
                  <RequirePermission code="ingredient.read">
                    <IngredientsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/ingredientes/novo"
                element={
                  <RequirePermission code="ingredient.create">
                    <IngredientEditorPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/ingredientes/:ingredientId"
                element={
                  <RequirePermission code="ingredient.read">
                    <IngredientEditorPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/estoque"
                element={
                  <RequirePermission code="inventory.read">
                    <InventoryOverviewPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/estoque/posicao"
                element={
                  <RequirePermission code="inventory.read">
                    <InventoryPositionPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/estoque/reservas"
                element={
                  <RequirePermission code="inventory.read">
                    <InventoryReservationsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/estoque/movimentacoes"
                element={
                  <RequirePermission code="inventory.read">
                    <InventoryMovementsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/estoque/separacao"
                element={
                  <RequirePermission code="inventory.separate">
                    <InventoryPicksPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/lotes"
                element={
                  <RequirePermission code="inventory.read">
                    <InventoryLotsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/fornecedores"
                element={
                  <RequirePermission code="supplier.read">
                    <SuppliersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/componentes/catalogos"
                element={
                  <RequirePermission code="ingredient.read">
                    <CatalogsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas"
                element={
                  <RequirePermission code="recipe.read">
                    <RecipesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/assistente"
                element={
                  <RequirePermission code="recipe.read">
                    <RecipeAiHubPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/assistente/criar"
                element={
                  <RequirePermission code="recipe.ai.propose">
                    <RecipeAiWizardPage mode="create" />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/assistente/adaptar"
                element={
                  <RequirePermission code="recipe.ai.propose">
                    <RecipeAiWizardPage mode="adapt" />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/assistente/historico"
                element={
                  <RequirePermission code="recipe.read">
                    <RecipeAiHistoryPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/assistente/:proposalId"
                element={
                  <RequirePermission code="recipe.read">
                    <RecipeAiDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/novo"
                element={
                  <RequirePermission code="recipe.create">
                    <RecipeEditorPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/:recipeId"
                element={
                  <RequirePermission code="recipe.read">
                    <RecipeEditorPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/receitas/:recipeId/versoes/:versionId/ficha"
                element={
                  <RequirePermission code="recipe.technical_sheet.read">
                    <RecipeSheetPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/producao"
                element={
                  <RequirePermission code="production.board.read">
                    <BoardPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/planejamento"
                element={
                  <RequirePermission code="production.plan.read">
                    <PlansPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/planejamento/:planId"
                element={
                  <RequirePermission code="production.plan.read">
                    <PlanDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens"
                element={
                  <RequirePermission code="production.order.read">
                    <OrdersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens/:orderId"
                element={
                  <RequirePermission code="production.order.read">
                    <OrderDetailPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/producao/ordens/:orderId/executar"
                element={
                  <RequirePermission code="production.order.read">
                    <ExecutePage />
                  </RequirePermission>
                }
              />
              <Route
                path="/ordens/:orderId/fichas/:issueId"
                element={
                  <RequirePermission code="production.order.read">
                    <SheetPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/rastreabilidade"
                element={
                  <RequirePermission code="production.traceability.read">
                    <TraceabilityHubPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/rastreabilidade/:orderId"
                element={<TraceabilityPage />}
              />
              <Route
                path="/conformidade"
                element={
                  <RequirePermission code="labeling.read">
                    <LabelingOverviewPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/dossies"
                element={
                  <RequirePermission code="labeling.read">
                    <LabelingDossiersPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/dossies/novo"
                element={
                  <RequirePermission code="labeling.dossier.create">
                    <LabelingCreatePage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/dossies/:dossierId"
                element={
                  <RequirePermission code="labeling.read">
                    <LabelingDossierPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/dossies/:dossierId/imprimir"
                element={
                  <RequirePermission code="labeling.render">
                    <LabelingDossierPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/avaliacoes"
                element={
                  <RequirePermission code="labeling.read">
                    <LabelingAssessmentsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/rotulos"
                element={
                  <RequirePermission code="labeling.read">
                    <LabelingCandidatesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/conformidade/fontes"
                element={
                  <RequirePermission code="regulatory.source.read">
                    <LabelingSourcesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos"
                element={
                  <RequirePermission code="costing.read">
                    <CostingOverviewPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/politicas"
                element={
                  <RequirePermission code="costing.read">
                    <CostingPoliciesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/previstos"
                element={
                  <RequirePermission code="costing.read">
                    <CostingListPage kind="planned" title="Custos previstos" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/realizados"
                element={
                  <RequirePermission code="costing.read">
                    <CostingListPage kind="actual" title="Custos realizados" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/calculos/:calcId"
                element={
                  <RequirePermission code="costing.read">
                    <CostingCalculationPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/simulacoes"
                element={
                  <RequirePermission code="pricing.simulation.manage">
                    <CostingSimulationsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/custos/precos"
                element={
                  <RequirePermission code="pricing.review">
                    <CostingPricesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/necessidades"
                element={
                  <RequirePermission code="procurement.read">
                    <ProcurementNeedsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/requisicoes"
                element={
                  <RequirePermission code="procurement.read">
                    <ProcurementListPage title="Requisições" path="/procurement/requisitions" lede="Requisição manual ou derivada da sugestão. Aprovação humana." />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/cotacoes"
                element={
                  <RequirePermission code="procurement.read">
                    <ProcurementQuotesPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/pedidos"
                element={
                  <RequirePermission code="procurement.read">
                    <ProcurementListPage title="Pedidos" path="/procurement/orders" lede="Pedido interno versionado. Emitido não é enviado ao fornecedor." />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/recebimentos"
                element={
                  <RequirePermission code="procurement.receive">
                    <ProcurementListPage title="Recebimentos" path="/procurement/receipts" lede="Recebimento parcial ou total cria lote interno." />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/compras/devolucoes"
                element={
                  <RequirePermission code="procurement.return">
                    <ProcurementListPage title="Devoluções" path="/procurement/returns" lede="Devolução gera saída vinculada ao lote. Sem crédito financeiro." />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/inventarios"
                element={
                  <RequirePermission code="inventory.count">
                    <InventoryCountsPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios"
                element={<ReportingOverviewPage />}
              />
              <Route
                path="/gestao/relatorios/executivo"
                element={
                  <RequirePermission code="reporting.dashboard.read">
                    <ReportingReportPage code="executive" title="Visão executiva" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/producao"
                element={
                  <RequirePermission code="reporting.production.read">
                    <ReportingReportPage code="production" title="Produção" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/componentes"
                element={
                  <RequirePermission code="reporting.production.read">
                    <ReportingReportPage code="consumption" title="Componentes e perdas" extraCodes={["yield_losses"]} />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/custos"
                element={
                  <RequirePermission code="reporting.costing.read">
                    <ReportingReportPage code="costing" title="Custos e preços" extraCodes={["pricing"]} />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/conformidade"
                element={
                  <RequirePermission code="reporting.compliance.read">
                    <ReportingReportPage code="compliance" title="Conformidade" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/rastreabilidade"
                element={
                  <RequirePermission code="reporting.traceability.read">
                    <ReportingReportPage code="traceability" title="Rastreabilidade" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/estoque"
                element={
                  <RequirePermission code="reporting.inventory.read">
                    <ReportingReportPage code="inventory" title="Estoque e compras" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/qualidade"
                element={
                  <RequirePermission code="reporting.data_quality.read">
                    <ReportingReportPage code="data_quality" title="Qualidade dos dados" />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/salvos"
                element={
                  <RequirePermission code="reporting.saved_view.manage">
                    <ReportingSavedPage />
                  </RequirePermission>
                }
              />
              <Route
                path="/gestao/relatorios/snapshots/:snapshotId"
                element={
                  <RequirePermission code="reporting.snapshot.create">
                    <ReportingSnapshotPage />
                  </RequirePermission>
                }
              />
              <Route path="/" element={<Navigate to="/producao" replace />} />
            </Route>
          </Routes>
  );
}

export function App() {
  return (
    <AuthProviderTree>
      <OrganizationProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AssistantProvider>
            <AppRoutes />
          </AssistantProvider>
        </BrowserRouter>
      </OrganizationProvider>
    </AuthProviderTree>
  );
}
