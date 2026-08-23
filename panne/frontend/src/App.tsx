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
import { SuppliersPage } from "./pages/SuppliersPage";
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
          <AppRoutes />
        </BrowserRouter>
      </OrganizationProvider>
    </AuthProviderTree>
  );
}
