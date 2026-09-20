import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import MonitorDocumentation from './MonitorDocumentation';
import { COMPONENTS, PROTOCOLS, TABLES } from './documentation/index.js';

afterEach(() => cleanup());

function renderDocs() {
  return render(<MonitorDocumentation />);
}

describe('Documentação da Spider', () => {
  it('expõe as cinco áreas na mesma aba', () => {
    renderDocs();
    expect(screen.getByRole('heading', { name: 'Documentação da Spider' })).toBeInTheDocument();
    const index = screen.getByRole('navigation', { name: 'Índice da documentação' });
    expect(within(index).getAllByRole('button').map((b) => b.textContent)).toEqual([
      'Arquitetura', 'Componentes', 'Protocolos', 'PostgreSQL', 'Ambiente e versões',
    ]);
    fireEvent.click(within(index).getByRole('button', { name: 'Componentes' }));
    expect(screen.getByTestId('component-catalog')).toBeInTheDocument();
    fireEvent.click(within(index).getByRole('button', { name: 'Protocolos' }));
    expect(screen.getByTestId('protocol-matrix')).toBeInTheDocument();
    fireEvent.click(within(index).getByRole('button', { name: 'PostgreSQL' }));
    expect(screen.getByTestId('schema-diagram')).toBeInTheDocument();
    fireEvent.click(within(index).getByRole('button', { name: 'Ambiente e versões' }));
    expect(screen.getByTestId('environment-versions')).toBeInTheDocument();
    fireEvent.click(within(index).getByRole('button', { name: 'Arquitetura' }));
    expect(screen.getByTestId('architecture-diagram')).toBeInTheDocument();
  });

  it('abre o primeiro resultado da busca com Enter', () => {
    renderDocs();
    const search = screen.getByLabelText(/Buscar componente, protocolo, tabela ou versão/);
    fireEvent.change(search, { target: { value: 'tb_execution_control' } });
    fireEvent.keyDown(search, { key: 'Enter' });
    expect(screen.getByTestId('schema-diagram')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'tb_execution_control' })).toBeInTheDocument();
  });

  it('seleciona componente, métodos e evidências', () => {
    renderDocs();
    fireEvent.click(screen.getByRole('button', { name: 'Componentes' }));
    fireEvent.click(screen.getByRole('option', { name: COMPONENTS.find((c) => c.id === 'canonical-engine').name }));
    expect(screen.getByText(/Valida, resolve rota/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'execute(request)' })).toBeInTheDocument();
    expect(screen.getAllByText('DefaultCanonicalExecutionEngine').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/DefaultCanonicalExecutionEngine.java/).length).toBeGreaterThan(0);
  });

  it('navega do diagrama ao componente e da relação ao protocolo', () => {
    renderDocs();
    fireEvent.click(within(screen.getByTestId('architecture-diagram')).getAllByRole('button', { name: /Entrada canônica HTTP/ })[0]);
    expect(screen.getByTestId('component-catalog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Entrada canônica HTTP' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Arquitetura' }));
    fireEvent.click(within(screen.getByTestId('architecture-diagram')).getByRole('button', { name: /POST \/v1\/canonical\/executions/ }));
    expect(screen.getByTestId('protocol-matrix')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: PROTOCOLS[0].name })).toBeInTheDocument();
  });

  it('seleciona tabela do esquema real', () => {
    renderDocs();
    fireEvent.click(screen.getByRole('button', { name: 'PostgreSQL' }));
    fireEvent.click(screen.getAllByRole('button', { name: 'tb_callback_outbox' })[0]);
    expect(screen.getByRole('heading', { name: 'tb_callback_outbox' })).toBeInTheDocument();
    expect(screen.getByText(/V20260821e__tb_callback_outbox.sql/)).toBeInTheDocument();
    expect(TABLES.some((t) => t.id === 'tb_callback_outbox')).toBe(true);
  });

  it('mostra versões com fonte e limitações de perfil', () => {
    renderDocs();
    fireEvent.click(screen.getByRole('button', { name: 'Ambiente e versões' }));
    expect(screen.getByText('Spring Boot')).toBeInTheDocument();
    expect(screen.getAllByText('3.4.2').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PowerShell 5.1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/local-demo/).length).toBeGreaterThan(0);
  });

  it('não apresenta roadmap, workbench, agente ou composer como implementados', () => {
    renderDocs();
    expect(screen.queryByText(/Roadmap após/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Como ler uma transação/)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Cockpit de Implementação/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Componentes' }));
    fireEvent.click(screen.getByRole('option', { name: 'Reconciliação operacional de callback' }));
    expect(screen.getByText(/Não é o Reconciliation Workbench/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('option', { name: 'ContextInterpretationProvider' }));
    expect(screen.getByText(/Não é composer de resposta nem agente/)).toBeInTheDocument();
    expect(screen.getAllByText(/Default-off/i).length).toBeGreaterThan(0);
  });

  it('mantém busca e índice utilizáveis por teclado e com cabeçalhos de tabela', () => {
    renderDocs();
    const search = screen.getByLabelText(/Buscar componente, protocolo, tabela ou versão/);
    search.focus();
    expect(search).toHaveFocus();
    fireEvent.change(search, { target: { value: 'SAT-003' } });
    expect(screen.getByRole('listbox', { name: 'Resultados da documentação' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Protocolos' }));
    expect(screen.getByRole('navigation', { name: 'Índice da documentação' }).querySelector('[aria-current="true"]')).toHaveTextContent('Protocolos');
    expect(document.getElementById('documentation-section-title')).toHaveFocus();
  });
});
