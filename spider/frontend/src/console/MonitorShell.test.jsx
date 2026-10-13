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
afterEach(()=>{cleanup();vi.unstubAllGlobals();window.history.replaceState(null,'','/');});
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
    expect(screen.getByRole('link',{name:'Sair'})).toHaveAttribute('href','/logout');
  });
  it('keeps a FinanceAction projection after events leave the recent window', async () => {
    const record = {
      recordId: 'int:actionfinance:list:acme:HOMOLOG',
      kind: 'SATELLITE_INTERACTION',
      origin: 'actionfinance',
      objective: 'LIST_EXTERNAL_PAYMENTS',
      technicalState: 'READY',
      eventKey: 'int:actionfinance:list:acme:HOMOLOG',
      updatedAt: '2026-10-13T12:00:00Z',
    };
    fetch.mockImplementation(async (url) => ({ok:true,text:async()=>JSON.stringify(
      String(url).startsWith('/v1/console/monitor/records') ? {items:[record],durable:false,retention:'P90D'} :
      url === '/v1/console/monitor/events' ? {available:true,items:[],availableScenarios:[]} :
      url === '/v1/console/monitor/simulation' ? simulation :
      {items:[]}
    )}));
    render(<MonitorShell/>);
    expect(await screen.findByRole('button', {name: /ACTIONFINANCE.*LIST_EXTERNAL_PAYMENTS/i})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', {name: /ACTIONFINANCE.*LIST_EXTERNAL_PAYMENTS/i}));
    expect(await screen.findByRole('heading', {name: 'Percurso registrado'})).toBeInTheDocument();
    expect(screen.queryByText(/exec-/i)).not.toBeInTheDocument();
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
    expect(screen.getAllByTitle('sat-0').length).toBeGreaterThan(0);
    expect(screen.getByText(/5 mais recentes/)).toBeInTheDocument();
  });

  it('does not return a manual Retry selection to the Finance deep link after a live refresh', async () => {
    const financeId = 'afm-d3288e80-77cb-41d6-8c6d-8e0214ad25c3';
    const retryId = 'exec-retry-public-1';
    const finance = ['SATELLITE_AUTHENTICATED','SATELLITE_RESPONSE_RETURNED'].map((eventType,i)=>({
      eventId:`fin-${i}`,executionId:financeId,eventType,source:'satellite-contract',category:'INTERACTION',
      occurredAt:`2026-10-02T12:39:4${i}Z`,outcome:'SUCCESS',
      metadata:{originSatellite:'actionfinance',aiUsage:'NOT_USED',reasonCode:i?'READY':'actionfinance'},
    }));
    const retry = [{eventId:'ret-0',executionId:retryId,eventType:'EXECUTION_SUCCEEDED',source:'canonical-engine',
      category:'INTERACTION',occurredAt:'2026-10-02T15:50:00Z',outcome:'SUCCESS',metadata:{originSatellite:undefined}}];
    window.history.replaceState(null,'',`/?q=${financeId}&execution=${financeId}`);
    fetch.mockImplementation(async(url)=>({ok:true,text:async()=>JSON.stringify(
      url==='/v1/console/monitor/events'?{available:true,items:[...finance,...retry],availableScenarios:['RETRY_THEN_SUCCESS']}:
      url==='/v1/console/executions'||url.startsWith('/v1/console/executions?')?{items:[
        {executionId:financeId,state:'SUCCEEDED',correlationId:financeId},
        {executionId:retryId,state:'SUCCEEDED',routeRef:'RETRY_THEN_SUCCESS@1'},
      ]}:
      url===`/v1/console/executions/${financeId}/events`?{items:finance}:
      url===`/v1/console/executions/${retryId}/events`?{items:retry}:{items:[]}
    )}));
    render(<MonitorShell/>);
    expect(await screen.findByRole('button',{name:/ACTIONFINANCE/})).toHaveAttribute('aria-pressed','true');
    fireEvent.click(screen.getByTitle(retryId).closest('button'));
    expect(screen.getByTitle(retryId).closest('button')).toHaveAttribute('aria-pressed','true');
    fireEvent.click(screen.getByRole('button',{name:'Simulação'}));
    fireEvent.click(screen.getByRole('button',{name:'Monitor'}));
    expect(screen.getByTitle(retryId).closest('button')).toHaveAttribute('aria-pressed','true');
    const before = fetch.mock.calls.filter(([url])=>url===`/v1/console/executions/${retryId}/events`).length;
    fireEvent.click(screen.getByRole('button',{name:'Atualizar'}));
    await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>url===`/v1/console/executions/${retryId}/events`).length).toBeGreaterThan(before));
    expect(screen.getByTitle(retryId).closest('button')).toHaveAttribute('aria-pressed','true');
    expect(screen.getByRole('button',{name:/ACTIONFINANCE/})).toHaveAttribute('aria-pressed','false');
    expect(window.location.search).toContain(`execution=${retryId}`);
    expect(window.location.search).not.toContain(financeId);
    expect(screen.getByText(/Ao vivo/)).toBeInTheDocument();
  });
  it('exposes API failures without replacing them with fabricated transactions',async()=>{
    fetch.mockRejectedValue(new Error('offline'));render(<MonitorShell/>);
    expect(await screen.findByText(/Eventos indisponíveis: .*não chegou à engine/)).toBeInTheDocument();
    expect(screen.queryByText('[SEGSENSE]')).not.toBeInTheDocument();
    expect(screen.queryByText('Nenhuma transação neste recorte.')).not.toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Tentar novamente'})).toBeInTheDocument();
    expect(screen.getByText(/Desatualizado/)).toBeInTheDocument();
    expect(screen.queryByText(/^Ao vivo/)).not.toBeInTheDocument();
  });
  it('keeps the selected execution after a transient related-events failure and resumes when visible',async()=>{
    const running=[
      {eventId:'run-0',executionId:'sat-run',eventType:'SATELLITE_AUTHENTICATED',source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-10-02T12:00:00Z',outcome:'SUCCESS',metadata:{originSatellite:'segsense',aiUsage:'NOT_USED'}},
      {eventId:'run-1',executionId:'sat-run',eventType:'SATELLITE_REQUEST_RECEIVED',source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-10-02T12:00:01Z',outcome:'SUCCESS',metadata:{originSatellite:'segsense',aiUsage:'NOT_USED'}},
    ];
    let related=0;
    fetch.mockImplementation(async(url)=>{
      if(url==='/v1/console/monitor/events') return {ok:true,text:async()=>JSON.stringify({available:true,items:running,availableScenarios:[]})};
      if(url==='/v1/console/executions/sat-run/events'){
        related+=1;
        if(related===2) throw new Error('blip');
        return {ok:true,text:async()=>JSON.stringify({items:running})};
      }
      return {ok:true,text:async()=>JSON.stringify({items:[]})};
    });
    render(<MonitorShell/>);
    expect(await screen.findByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/SEGSENSE/})).toHaveAttribute('aria-pressed','true');
    Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});
    fireEvent(document,new Event('visibilitychange'));
    await waitFor(()=>expect(screen.getByText(/Desatualizado|blip/)).toBeInTheDocument());
    expect(screen.getByRole('button',{name:/SEGSENSE/})).toHaveAttribute('aria-pressed','true');
    expect(screen.getByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
    fireEvent(document,new Event('visibilitychange'));
    await waitFor(()=>expect(screen.queryByText(/blip/)).not.toBeInTheDocument());
    expect(screen.getByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
  });
  it('does not treat an aborted related-events query as a business failure',async()=>{
    const abort=new DOMException('The operation was aborted.','AbortError');
    let once=false;
    const original=fetch.getMockImplementation();
    fetch.mockImplementation(async(url,options)=>{
      if(url==='/v1/console/executions/sat-1/events' && !once){
        once=true;
        throw abort;
      }
      return original(url,options);
    });
    render(<MonitorShell/>);
    await screen.findByRole('button',{name:/SEGSENSE/});
    expect(screen.queryByText(/aborted|AbortError/i)).not.toBeInTheDocument();
  });
  it('keeps a manual pause after the tab becomes visible',async()=>{
    render(<MonitorShell/>);
    await screen.findByText(/Ao vivo/);
    fireEvent.click(screen.getByRole('button',{name:'Pausar'}));
    expect(screen.getByText(/Pausado/)).toBeInTheDocument();
    const before=fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length;
    Object.defineProperty(document,'visibilityState',{configurable:true,get:()=>'visible'});
    fireEvent(document,new Event('visibilitychange'));
    await new Promise(resolve=>setTimeout(resolve,40));
    expect(fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length).toBe(before);
    expect(screen.getByText(/Pausado/)).toBeInTheDocument();
  });
  it('offers reauthentication on 401 without emptying a prior observation or looping refresh',async()=>{
    const original=fetch.getMockImplementation();
    let calls=0;
    fetch.mockImplementation(async(url,options)=>{
      if(url==='/v1/console/monitor/events'){
        calls+=1;
        if(calls>1) return {ok:false,status:401,text:async()=>JSON.stringify({title:'Unauthorized',status:401})};
      }
      return original(url,options);
    });
    render(<MonitorShell/>);
    expect(await screen.findByRole('button',{name:/SEGSENSE/})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Atualizar'}));
    await waitFor(()=>expect(screen.getAllByText(/Sessão expirada/).length).toBeGreaterThan(0));
    expect(screen.getByRole('link',{name:'Entrar novamente'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/SEGSENSE/})).toBeInTheDocument();
    const after=fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length;
    await new Promise(resolve=>setTimeout(resolve,50));
    expect(fetch.mock.calls.filter(([url])=>url==='/v1/console/monitor/events').length).toBe(after);
  });
  it('removes cached transactions when access is denied',async()=>{
    const original=fetch.getMockImplementation();
    let calls=0;
    fetch.mockImplementation(async(url,options)=>{
      if(url==='/v1/console/monitor/events'){
        calls+=1;
        if(calls>1) return {ok:false,status:403,text:async()=>JSON.stringify({title:'Forbidden',status:403})};
      }
      return original(url,options);
    });
    render(<MonitorShell/>);
    expect(await screen.findByRole('button',{name:/SEGSENSE/})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Atualizar'}));
    await waitFor(()=>expect(screen.getByText(/acesso a este recorte foi recusado/i)).toBeInTheDocument());
    expect(screen.queryByRole('button',{name:/SEGSENSE/})).not.toBeInTheDocument();
  });
});
