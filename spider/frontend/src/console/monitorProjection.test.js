import { describe, it, expect } from 'vitest';
import {projectTransaction, projectTransactions, humanLog, buildMonitorFlow, defaultFlowSelection, classifyMonitorStatus, takeLatestArrivals} from './monitorProjection';
function event(type, metadata = {}, id = 'message-1') {return {eventId:type,executionId:id,eventType:type,source:'satellite-contract',category:'INTERACTION',occurredAt:'2026-09-17T12:00:00Z',metadata,outcome:'SUCCESS'};}
describe('Monitor evidence projection', () => {
  it('does not infer authenticated origin, completion or AI absence from missing events', () => {
    const t = projectTransaction('message-1',[event('SATELLITE_REQUEST_RECEIVED',{originSatellite:'forged'})]);
    expect(t.origin).toBeNull(); expect(t.ai).toBe('UNKNOWN');
    expect(t.state).toBe('SEM_RESULTADO_REGISTRADO');
    expect(t.phases.find(p=>p.key==='plan').events).toHaveLength(0);
  });
  it('retains the origin separately from component and executor', () => {
    const e = event('PROVIDER_RESULT_RECEIVED',{currentComponent:'SPIDER',executor:'insurance-provider-mock',aiUsage:'NOT_USED'});
    const t = projectTransaction('message-1',[event('SATELLITE_AUTHENTICATED',{originSatellite:'segsense'}),e,event('SATELLITE_RESPONSE_RETURNED',{reasonCode:'READY'})]);
    expect(t.origin).toBe('segsense');expect(t.executor).toBe('insurance-provider-mock');expect(t.ai).toBe('NOT_USED');expect(t.state).toBe('READY');
    expect(humanLog(e,t.origin)).toBe('[SEGSENSE] [SPIDER] PROVIDER_RESULT_RECEIVED SUCCESS');
  });
  it('does not mix evidence between transactions sharing a correlation', () => {
    const a = {...event('SATELLITE_AUTHENTICATED',{originSatellite:'segsense'}),correlationId:'same'};
    const b = {...event('SATELLITE_AUTHENTICATED',{originSatellite:'spiderbank'},'message-2'),correlationId:'same'};
    const rows = projectTransactions([a,b],[]);
    expect(rows).toHaveLength(2);expect(rows[0].events).toHaveLength(1);expect(rows[1].events).toHaveLength(1);
  });
  it('merges canonical evidence without duplicating execution and preserves negative result', () => {
    const e = {...event('EXECUTION_SUCCEEDED'),source:'canonical-engine'};
    const rows = projectTransactions([e],[{executionId:'message-1',state:'SUCCEEDED',technicalStatus:'BUSINESS_NEGATIVE'}]);
    expect(rows).toHaveLength(1);expect(rows[0].result).toBe('BUSINESS_NEGATIVE');
    expect(rows[0].origin).toBe('canonical');
  });
  it('keeps satellite origin unset when authentication is missing and marks canonical ingress', () => {
    const satellite = projectTransaction('message-1',[event('SATELLITE_REQUEST_RECEIVED',{originSatellite:'forged'})]);
    expect(satellite.origin).toBeNull();
    const canonical = projectTransaction('exec-1',[],{state:'SUCCEEDED',routeRef:'RETRY_THEN_SUCCESS@1'});
    expect(canonical.origin).toBe('canonical');
    expect(canonical.routeRef).toBe('RETRY_THEN_SUCCESS@1');
  });
  it('builds a single observed flow without empty architectural stages', () => {
    const t = projectTransaction('message-1',[event('SATELLITE_AUTHENTICATED',{originSatellite:'segsense'}),event('SATELLITE_RESPONSE_RETURNED',{reasonCode:'READY'})]);
    const flow = buildMonitorFlow(t);
    expect(flow.mode).toBe('observed');
    expect(flow.nodes.map(n => n.id)).toEqual(['origin','result']);
    expect(defaultFlowSelection(flow)).toBe('result');
    expect(flow.nodes.find(n => n.id === 'plan')).toBeUndefined();
  });
  it('uses persisted plan steps as the flow and keeps unrun steps as planned', () => {
    const t = projectTransaction('exec-1',[],{state:'RUNNING'});
    const flow = buildMonitorFlow(t,{plan:{orderedSteps:['step-a','step-b']},steps:[{stepRef:'step-a',state:'SUCCEEDED'}],detail:{summary:{state:'RUNNING'}}});
    expect(flow.mode).toBe('plan');
    expect(flow.nodes.map(n => [n.id,n.status])).toEqual([['step-a','completed'],['step-b','planned']]);
    expect(classifyMonitorStatus('WAITING_EXTERNAL')).toBe('waiting');
    expect(classifyMonitorStatus('FAILED')).toBe('failed');
    expect(classifyMonitorStatus('REJECTED')).toBe('rejected');
    expect(classifyMonitorStatus(null)).toBe('unknown');
  });
  it('keeps a FIFO window of the five latest arrivals', () => {
    const rows = Array.from({length: 6}, (_, i) => ({id:`sat-${i}`, lastActivityAt:`2026-09-17T12:0${i}:00Z`}));
    const window = takeLatestArrivals(rows, 5);
    expect(window.map(t => t.id)).toEqual(['sat-5','sat-4','sat-3','sat-2','sat-1']);
    expect(window.find(t => t.id === 'sat-0')).toBeUndefined();
  });
});
