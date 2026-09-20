import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import SimulationPanel from './SimulationPanel';
import { MOCK_SCENARIOS } from './scenarios';
import { SEGSENSE_URL, SPIDERBANK_URL } from './urls';

const ALL = MOCK_SCENARIOS.map(scenario => scenario.id);
const simulation = {signalHttpEnabled:true,satellites:[
  {id:'segsense',available:true,missing:[],url:SEGSENSE_URL},
  {id:'spiderbank',available:false,missing:['Capability SIMULATE_WORKING_CAPITAL permanece indisponível'],url:SPIDERBANK_URL},
]};

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (url, options) => ({
    ok: true,
    text: async () => JSON.stringify(
      url === '/v1/console/monitor/simulation' ? simulation :
      url === '/v1/canonical/executions' && options?.method === 'POST' ? {execution:{executionId:'exec-real'}} :
      url === '/v1/canonical/signals' ? {processingStatus:'ACCEPTED_AND_RESUMED',executionId:'exec-wait'} :
      {items:[]}
    ),
  })));
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function renderPanel(props = {}) {
  const onOpened = vi.fn();
  render(<SimulationPanel availableScenarios={ALL} loadingScenarios={false} onOpened={onOpened} {...props} />);
  return onOpened;
}

describe('Simulation panel', () => {
  it('opens SpiderBank at the product URL when readiness says the chain is available', async () => {
    fetch.mockImplementation(async () => ({
      ok: true,
      text: async () => JSON.stringify({
        signalHttpEnabled: true,
        satellites: [
          {id:'segsense',available:true,missing:[],url:SEGSENSE_URL},
          {id:'spiderbank',available:true,missing:[],url:'http://127.0.0.1:5190/'},
        ],
      }),
    }));
    renderPanel();
    const spiderbank = await screen.findByTestId('satellite-card-spiderbank');
    expect(within(spiderbank).getByRole('link', {name:'Abrir SpiderBank'})).toHaveAttribute('href', 'http://127.0.0.1:5190/');
    expect(spiderbank).toHaveTextContent('Disponível');
  });

  it('renders identical satellite cards and blocks the credit journey when it is not integrated', async () => {
    renderPanel();
    const segsense = await screen.findByTestId('satellite-card-segsense');
    const spiderbank = screen.getByTestId('satellite-card-spiderbank');
    expect(segsense.children).toHaveLength(spiderbank.children.length);
    expect(within(segsense).getByRole('link', {name:'Abrir SegSense'})).toHaveAttribute('href', SEGSENSE_URL);
    expect(within(spiderbank).getByRole('button', {name:'Abrir SpiderBank'})).toBeDisabled();
    expect(spiderbank).toHaveTextContent('Capability SIMULATE_WORKING_CAPITAL permanece indisponível');
    expect(segsense).toHaveTextContent('Aparece pela origem registrada');
    expect(spiderbank).not.toHaveTextContent('documentos inspecionados');
  });

  it('starts a canonical scenario and forwards only the backend identity', async () => {
    const onOpened = renderPanel();
    fireEvent.click(await screen.findByRole('button', {name:'Executar Sucesso em múltiplas etapas'}));
    await waitFor(() => expect(onOpened).toHaveBeenCalledWith(expect.objectContaining({id:'exec-real'})));
    expect(fetch.mock.calls.some(([url, options]) => url === '/v1/canonical/executions' && options.method === 'POST')).toBe(true);
  });

  it('disables only the requested control while the request is in flight', async () => {
    let finish;
    fetch.mockImplementation(async (url, options) => {
      if (url === '/v1/canonical/executions' && options?.method === 'POST') {
        await new Promise(resolve => { finish = resolve; });
        return {ok:true,text:async()=>JSON.stringify({execution:{executionId:'exec-real'}})};
      }
      return {ok:true,text:async()=>JSON.stringify(url === '/v1/console/monitor/simulation' ? simulation : {items:[]})};
    });
    renderPanel();
    fireEvent.click(await screen.findByRole('button', {name:'Executar Retry com sucesso'}));
    expect(screen.getByRole('button', {name:'Executar Retry com sucesso'})).toBeDisabled();
    expect(screen.getByRole('button', {name:'Executar Falha técnica'})).toBeEnabled();
    finish();
    await waitFor(() => expect(screen.getByRole('button', {name:'Executar Retry com sucesso'})).toBeEnabled());
  });

  it('keeps a waiting execution on the two-phase control until the real signal is sent', async () => {
    const onOpened = renderPanel();
    fireEvent.click(await screen.findByRole('button', {name:'Executar Espera, sinal e retomada'}));
    expect(await screen.findByText('Execução em espera. Envie o sinal para retomar.')).toBeInTheDocument();
    expect(onOpened).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name:'Enviar sinal'}));
    await waitFor(() => expect(onOpened).toHaveBeenCalledWith(expect.objectContaining({id:'exec-real'})));
    expect(fetch.mock.calls.some(([url]) => url === '/v1/canonical/signals')).toBe(true);
  });

  it('does not invent a transaction when start fails without an execution id', async () => {
    fetch.mockImplementation(async (url) => ({
      ok: url !== '/v1/canonical/executions',
      status: url === '/v1/canonical/executions' ? 503 : 200,
      text: async () => JSON.stringify(url === '/v1/console/monitor/simulation' ? simulation : {title:'offline'}),
    }));
    const onOpened = renderPanel();
    fireEvent.click(await screen.findByRole('button', {name:'Executar Falha técnica'}));
    expect(await screen.findByText('Falha ao iniciar neste ambiente.')).toBeInTheDocument();
    expect(onOpened).not.toHaveBeenCalled();
  });

  it('does not keep satellites in a checking state after readiness fails', async () => {
    fetch.mockImplementation(async (url) => ({
      ok: url !== '/v1/console/monitor/simulation',
      status: url === '/v1/console/monitor/simulation' ? 500 : 200,
      text: async () => JSON.stringify({title:'offline'}),
    }));
    renderPanel();
    expect(await screen.findByText('Falha ao verificar os satélites neste ambiente.')).toBeInTheDocument();
    expect(screen.queryByText('Verificando')).not.toBeInTheDocument();
    expect(screen.getByRole('button', {name:'Abrir SegSense'})).toBeDisabled();
    expect(screen.getByRole('button', {name:'Abrir SpiderBank'})).toBeDisabled();
  });

  it('uses two columns on desktop and one column on narrow screens', () => {
    const css = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'monitor-workspace.css'), 'utf8');
    expect(css).toMatch(/\.scenario-lines[^{]*\{[^}]*grid-template-columns:\s*repeat\(2/);
    expect(css).toMatch(/max-width:\s*800px[\s\S]*\.scenario-lines \{ grid-template-columns: 1fr/);
  });
});
