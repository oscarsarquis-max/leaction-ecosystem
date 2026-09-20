import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import MonitorShell from './MonitorShell';
const simulation = {signalHttpEnabled:true,satellites:[
  {id:'segsense',available:true,missing:[],url:'http://127.0.0.1:5178/demonstracao/mvp-integrado'},
  {id:'spiderbank',available:false,missing:['Capability SIMULATE_WORKING_CAPITAL permanece indisponível'],url:'/spiderbank'},
]};
const events = ['SATELLITE_AUTHENTICATED','SATELLITE_RESPONSE_RETURNED'].map((eventType,i)=>({eventId:`ev-${i}`,executionId:'sat-1',eventType,source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-09-17T12:00:00Z',outcome:'SUCCESS',metadata:{originSatellite:'segsense',aiUsage:'NOT_USED',reasonCode:i?'READY':'segsense'}}));
beforeEach(()=>vi.stubGlobal('fetch',vi.fn(async (url,options) => ({ok:true,text:async()=>JSON.stringify(
  url === '/v1/console/monitor/events' ? {available:true,items:events,availableScenarios:["SUCCESS_MULTI_STEP","RETRY_THEN_SUCCESS"]} :
  url === '/v1/console/monitor/simulation' ? simulation :
  url === '/v1/console/executions/sat-1/events' ? {items:events} :
  url === '/v1/canonical/executions' && options?.method === 'POST' ? {execution:{executionId:'new-execution'}} : {items:[]})
}))));
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('Monitor navigation and evidence',()=>{
  it('opens a satellite interaction on the first page without inventing a plan or empty architecture',async()=>{
    render(<MonitorShell/>);
    fireEvent.click(await screen.findByRole('button',{name:/SEGSENSE.*Interação de satélite/}));
    expect(await screen.findByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Resultado'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Origem/})).toBeInTheDocument();
    expect(screen.queryByText('Sem evidência disponível')).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Plano de execução/})).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Intent Contract/})).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Capacidades/})).not.toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Definição'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Evidências'})).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Arquitetura',exact:true})).not.toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Fluxo de transações',exact:true})).toBeInTheDocument();
    expect(screen.queryByText(/Ferramentas operacionais/)).not.toBeInTheDocument();
    expect(screen.queryByText(/laboratório/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Ao vivo/)).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Pausar'})).toBeInTheDocument();
  });
  it('uses search to select a transaction without emptying the live stream',async()=>{
    const bank=['SATELLITE_AUTHENTICATED','SATELLITE_RESPONSE_RETURNED'].map((eventType,i)=>({eventId:`bank-${i}`,executionId:'sat-2',eventType,source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-09-17T12:01:00Z',outcome:'SUCCESS',metadata:{originSatellite:'spiderbank',aiUsage:'NOT_USED',reasonCode:i?'READY':'spiderbank'}}));
    fetch.mockImplementation(async (url)=>({ok:true,text:async()=>JSON.stringify(
      url==='/v1/console/monitor/events'?{available:true,items:[...events,...bank],availableScenarios:[]}:
      url==='/v1/console/executions/sat-2/events'?{items:bank}:
      url==='/v1/console/executions/sat-1/events'?{items:events}:{items:[]}
    )}));
    render(<MonitorShell/>);
    await screen.findByRole('button',{name:/SPIDERBANK/});
    fireEvent.change(screen.getByLabelText(/Buscar no recorte/),{target:{value:'spiderbank'}});
    expect(screen.getByText(/1 correspondência/)).toBeInTheDocument();
    expect(within(screen.getByRole('listbox')).getByTitle('sat-2')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/SEGSENSE/})).toBeInTheDocument();
    fireEvent.keyDown(screen.getByLabelText(/Buscar no recorte/),{key:'Enter'});
    expect(await screen.findByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
    expect(within(screen.getByRole('listbox')).getByRole('option')).toHaveAttribute('aria-selected','true');
  });
  it('refreshes the live stream without a manual update',async()=>{
    render(<MonitorShell/>);
    await screen.findByText(/Ao vivo/);
    const before=fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length;
    fireEvent.click(screen.getByRole('button',{name:'Pausar'}));
    expect(screen.getByText(/Pausado/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Retomar'}));
    await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length).toBeGreaterThan(before));
    expect(screen.getByText(/Ao vivo/)).toBeInTheDocument();
  });
  it('keeps navigation as Monitor, Simulação and Documentação',()=>{
    render(<MonitorShell/>);
    const buttons = within(screen.getByRole('navigation',{name:'Navegação do Monitor'})).getAllByRole('button');
    expect(buttons.map(button=>button.textContent)).toEqual(['Monitor','Simulação','Documentação']);
    expect(buttons[0]).toHaveAttribute('aria-current','page');
  });
  it('submits a real canonical request before opening the returned transaction',async()=>{
    render(<MonitorShell/>);fireEvent.click(screen.getByRole('button',{name:'Simulação'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Executar Sucesso em múltiplas etapas'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Executar Sucesso em múltiplas etapas'}));
    expect(await screen.findByText('Execução registrada. Acompanhe o resultado no Monitor.')).toBeInTheDocument();
    expect(fetch.mock.calls.some(([url,o])=>url==='/v1/canonical/executions' && o.method==='POST')).toBe(true);
    await waitFor(()=>expect(fetch.mock.calls.some(([url])=>url==='/v1/console/executions/new-execution/events')).toBe(true));
  });
  it('disables unavailable routes and follows a rejection returned by the server',async()=>{
    const original = fetch.getMockImplementation();
    fetch.mockImplementation(async (url,options) => url === '/v1/canonical/executions' && options?.method === 'POST'
      ? {ok:false,status:422,text:async()=>JSON.stringify({execution:{executionId:'rejected-1',state:'REJECTED'},errors:[{code:'ROUTE_NOT_FOUND'}]})}
      : original(url,options));
    render(<MonitorShell/>);fireEvent.click(screen.getByRole('button',{name:'Simulação'}));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Executar Sucesso em múltiplas etapas'})).toBeEnabled());
    expect(screen.getByRole('button',{name:'Executar Negativa de negócio'})).toBeDisabled();
    fireEvent.click(screen.getByRole('button',{name:'Executar Sucesso em múltiplas etapas'}));
    expect(await screen.findByText('Transação registrada com rejeição ou falha.')).toBeInTheDocument();
    await waitFor(()=>expect(fetch.mock.calls.some(([url])=>url==='/v1/console/executions/rejected-1/events')).toBe(true));
  });
  it('keeps only the five most recent arrivals in the live stream',async()=>{
    const items=Array.from({length:6},(_,i)=>['SATELLITE_AUTHENTICATED','SATELLITE_RESPONSE_RETURNED'].map((eventType,n)=>({
      eventId:`ev-${i}-${n}`,executionId:`sat-${i}`,eventType,source:'satellite-contract',category:'INTERACTION',
      occurredAt:`2026-09-17T12:0${i}:0${n}Z`,outcome:'SUCCESS',metadata:{originSatellite:'segsense',aiUsage:'NOT_USED',reasonCode:n?'READY':'segsense'},
    }))).flat();
    fetch.mockImplementation(async (url)=>({ok:true,text:async()=>JSON.stringify(
      url==='/v1/console/monitor/events'?{available:true,items,availableScenarios:[]}:
      url.includes('/events')?{items:items.filter(e=>url.includes(e.executionId))}:{items:[]}
    )}));
    render(<MonitorShell/>);
    await screen.findByTitle('sat-5');
    expect(screen.getAllByRole('button',{name:/SEGSENSE/})).toHaveLength(5);
    expect(screen.queryByTitle('sat-0')).not.toBeInTheDocument();
    expect(screen.getByText(/5 mais recentes/)).toBeInTheDocument();
    expect(screen.getByText(/6 no recorte/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Buscar no recorte/),{target:{value:'sat-0'}});
    expect(screen.getByText(/1 correspondência/)).toBeInTheDocument();
    expect(within(screen.getByRole('listbox')).getByTitle('sat-0')).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole('listbox')).getByRole('option'));
    expect(within(screen.getByRole('listbox')).getByRole('option')).toHaveAttribute('aria-selected','true');
    expect(screen.getByText(/5 mais recentes/)).toBeInTheDocument();
  });
  it('exposes API failures without replacing them with fabricated transactions',async()=>{
    fetch.mockRejectedValue(new Error('offline'));render(<MonitorShell/>);
    expect(await screen.findByText('Eventos indisponíveis: offline')).toBeInTheDocument();
    expect(screen.queryByText('[SEGSENSE]')).not.toBeInTheDocument();
  });
});
