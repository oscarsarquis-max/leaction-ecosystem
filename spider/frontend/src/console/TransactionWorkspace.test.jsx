import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import TransactionWorkspace from './TransactionWorkspace';
import MonitorDocumentation from './MonitorDocumentation';
import { projectTransaction } from './monitorProjection';

function satelliteEvents() {
  return [
    {eventId:'ev-0',executionId:'sat-1',eventType:'SATELLITE_AUTHENTICATED',source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-09-17T12:00:00Z',outcome:'SUCCESS',metadata:{originSatellite:'origin-a'}},
    {eventId:'ev-1',executionId:'sat-1',eventType:'SATELLITE_RESPONSE_RETURNED',source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-09-17T12:00:01Z',outcome:'SUCCESS',metadata:{reasonCode:'READY'}},
  ];
}

afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('Same-page transaction investigation',()=>{
  it('reuses the cockpit journey for a canonical retry instead of a single plan step',async()=>{
    vi.stubGlobal('fetch',vi.fn(async url=>({ok:true,text:async()=>JSON.stringify(url.includes('/v1/context/')?{}:{
      summary:{executionId:'exec-1',state:'SUCCEEDED',technicalStatus:'SUCCESS',routeRef:'RETRY_THEN_SUCCESS@1',startedAt:'2026-09-03T12:00:00Z',completedAt:'2026-09-03T12:00:03Z'},
      timeline:{available:true,data:[
        {eventId:'tr-1',eventType:'STATE_TRANSITION',state:'RUNNING',occurredAt:'2026-09-03T12:00:00Z'},
        {eventId:'att-1',eventType:'ATTEMPT',stepRef:'step-a',attemptNumber:1,state:'FAILED',occurredAt:'2026-09-03T12:00:00Z'},
        {eventId:'att-2',eventType:'ATTEMPT',stepRef:'step-a',attemptNumber:2,state:'SUCCEEDED',occurredAt:'2026-09-03T12:00:01Z'},
        {eventId:'tr-2',eventType:'STATE_TRANSITION',state:'SUCCEEDED',occurredAt:'2026-09-03T12:00:03Z'},
      ]},
      plan:{available:true,data:{planId:'plan-demo',routeRef:'RETRY_THEN_SUCCESS@1',orderedSteps:['step-a']}},
      steps:{available:true,data:[{stepRef:'step-a',state:'SUCCEEDED',attemptCount:2,attempts:[
        {attemptNumber:1,state:'FAILED',disposition:'UNCERTAIN',safeErrorCode:'TRANSIENT'},
        {attemptNumber:2,state:'SUCCEEDED',disposition:'CERTAIN'},
      ]}]},
    })})));
    render(<TransactionWorkspace transaction={projectTransaction('exec-1',[],{state:'SUCCEEDED',routeRef:'RETRY_THEN_SUCCESS@1',startedAt:'2026-09-03T12:00:00Z'})}/>);
    expect(await screen.findByRole('button',{name:/Solicitação recebida/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Contrato canônico/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/^Engine/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Interaction #1/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/^↻?Retry/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Interaction #2/})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Execução concluída/})).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/^step-a$/})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:/Interaction #1/}));
    expect(screen.getByRole('heading',{name:'Definição'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Evidências'})).toBeInTheDocument();
    expect(screen.getByTestId('journey-step-detail')).toHaveTextContent('falha transitória');
    expect(screen.getByTestId('journey-step-detail')).toHaveTextContent('TRANSIENT');
    expect(screen.queryByText(/Etapa operacional do plano persistido/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Todos os eventos desta transação/)).not.toBeInTheDocument();
  });
  it('drops the previous transaction records when selection changes',async()=>{
    vi.stubGlobal('fetch',vi.fn(async url=>({ok:true,text:async()=>JSON.stringify(url.includes('exec-a')?{summary:{executionId:'exec-a',state:'SUCCEEDED',routeRef:'ROUTE-A'}}:{summary:{executionId:'exec-b',state:'SUCCEEDED'}})})));
    const view=render(<TransactionWorkspace transaction={projectTransaction('exec-a',[],{state:'SUCCEEDED',routeRef:'ROUTE-A'})}/>);
    await screen.findByRole('button',{name:/Contrato canônico/});
    expect(screen.getByText('exec-a')).toBeInTheDocument();
    view.rerender(<TransactionWorkspace transaction={projectTransaction('exec-b',[],{state:'SUCCEEDED'})}/>);
    await waitFor(()=>expect(screen.queryByText('exec-a')).not.toBeInTheDocument());
    expect(screen.getByText('exec-b')).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Contrato canônico/})).not.toBeInTheDocument();
  });
  it('shows the recorded path of a satellite interaction without empty plan blocks',()=>{
    render(<TransactionWorkspace transaction={projectTransaction('sat-1', satelliteEvents())}/>);
    expect(screen.getByRole('heading',{name:'Percurso registrado'})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:/Origem/})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Resultado'})).toBeInTheDocument();
    expect(screen.queryByText(/Não há plano persistido/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Intent Contract/})).not.toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Definição'})).toBeInTheDocument();
    expect(screen.getByRole('heading',{name:'Evidências'})).toBeInTheDocument();
  });
  it('does not treat absence of evidence as failure',()=>{
    render(<TransactionWorkspace transaction={projectTransaction('sat-1',[satelliteEvents()[0]])}/>);
    expect(screen.getByRole('heading',{name:'Origem'})).toBeInTheDocument();
    expect(screen.queryByText('Falha técnica')).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:/Resultado/})).not.toBeInTheDocument();
  });
  it('provides documentation without requiring a selected transaction',()=>{
    render(<MonitorDocumentation/>);
    expect(screen.getByRole('heading',{name:'Documentação da Spider'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Arquitetura'}));
    expect(screen.getByTestId('architecture-diagram')).toBeInTheDocument();
  });
});
