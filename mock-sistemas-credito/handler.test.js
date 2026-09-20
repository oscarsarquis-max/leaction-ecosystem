import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { request as httpRequest } from 'node:http';
import { processRequest, CAPABILITY, MAX_BYTES } from './handler.js';
import { createMockServer } from './server.js';
const credential = 'test-only-credential-123456';
const sample = JSON.parse(readFileSync(new URL('./examples/request.json', import.meta.url)));
const make = () => structuredClone(sample);
const invoke = (body = make(), changes = {}) => processRequest({
 method:'POST', path:'/v1/provider/capabilities/' + CAPABILITY + '/executions',
 headers:{'content-type':'application/json','x-credit-mock-credential':credential},
 raw:JSON.stringify(body), ...changes
}, {credential});
test('synthetic calculation is labelled, correlated and cent-exact', () => {
 const r = invoke(); assert.equal(r.status,200); assert.equal(r.body.status,'COMPLETED');
 assert.equal(r.body.requestId,sample.requestId); assert.equal(r.body.correlationId,sample.correlationId);
 assert.equal(r.body.result.totalCents,1120000);
 assert.equal(r.body.result.installmentsCents.reduce((a,b)=>a+b,0),1120000);
 assert.equal(r.body.result.offerable,false); assert.equal(r.body.result.testDouble,true);
 assert.match(r.body.result.watermark,/NÃO É OFERTA/);
 assert.deepEqual(invoke().body.result,r.body.result);
});
test('scenarios return no fabricated financial terms', () => {
 for (const [scenario,status,reason] of [['MISSING_CONTEXT','PENDING','MISSING_CONTEXT'],['REJECTED','REJECTED','SYNTHETIC_SCENARIO_REJECTED'],['HUMAN_REVIEW','PENDING','SYNTHETIC_HUMAN_REVIEW']]) {
  const b=make(); b.inputs.scenarioKey=scenario; const r=invoke(b);
  assert.equal(r.body.status,status); assert.ok(r.body.reasonCodes.includes(reason));
  assert.equal(r.body.result.totalCents,undefined);
 }
 const b=make(); b.inputs.scenarioKey='UNAVAILABLE'; const r=invoke(b);
 assert.equal(r.status,503); assert.equal(r.body.retryable,true);
});
test('missing amounts produce a question, never a default amount', () => {
 const b=make(); delete b.inputs.principalCents;
 assert.deepEqual(invoke(b).body.result.missingFields,['principalCents']);
});
test('auth and capability boundaries', () => {
 assert.equal(invoke(make(),{headers:{}}).status,401);
 assert.equal(invoke(make(),{path:'/v1/provider/capabilities/OTHER/executions'}).body.errorCode,'CAPABILITY_NOT_AVAILABLE');
 assert.equal(invoke(make(),{path:'/unknown'}).status,404);
 assert.throws(()=>createMockServer('short'));
});
test('reject invalid JSON, oversized UTF8, invalid contract and extraneous context', () => {
 assert.equal(invoke(make(),{raw:'{'}).status,400);
 assert.equal(invoke(make(),{raw:'ã'.repeat(MAX_BYTES)}).status,413);
 for (const change of [
  b=>b.contractVersion='1.0', b=>b.purpose='INSURANCE_PROTECTION_ASSESSMENT',
  b=>b.objective='leaked context', b=>b.inputs.customerName='Real name',
  b=>b.inputs.monthlyRateBps=500, b=>b.inputs.principalCents=-1,
  b=>b.inputs.principalCents=1.5, b=>b.inputs.termMonths=37,
  b=>b.inputs.scenarioKey='UNKNOWN', b=>b.requestId='short',
  b=>b.dataClassification='PERSONAL', b=>b.callback='https://example.org',
  b=>b.requestedAt='yesterday', b=>b.inputs=null
 ]) {const b=make(); change(b); assert.equal(invoke(b).status,400);}
 for (const b of [null,[],true]) assert.equal(invoke(b).status,400);
});
test('HTTP smoke, headers, malformed JSON and streamed byte limit', async t => {
 const server=createMockServer(credential);
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 t.after(()=>new Promise(resolve=>server.close(resolve)));
 const port=server.address().port;
 const call=(path,method='GET',raw='',headers={})=>new Promise((resolve,reject)=>{
  const req=httpRequest({hostname:'127.0.0.1',port,path,method,headers},res=>{
   let text='';res.setEncoding('utf8');res.on('data',c=>text+=c);
   res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,body:JSON.parse(text)}));
  }); req.on('error',reject);req.end(raw);
 });
 assert.equal((await call('/health')).body.integratedWithSpider,false);
 const path='/v1/provider/capabilities/'+CAPABILITY+'/executions';
 const headers={'content-type':'application/json','x-credit-mock-credential':credential};
 const ok=await call(path,'POST',JSON.stringify(sample),headers);
 assert.equal(ok.status,200);assert.equal(ok.headers['cache-control'],'no-store');
 assert.equal((await call(path,'POST','{',headers)).status,400);
 assert.equal((await call(path,'POST','x'.repeat(MAX_BYTES+1),headers)).status,413);
});
test('assessment 0.2 capabilities stay modular and synthetic', () => {
 const assess = (capability, scenario = 'SUCCESS') => processRequest({
  method:'POST', path:'/v1/provider/capabilities/' + capability + '/executions',
  headers:{'content-type':'application/json','x-credit-mock-credential':credential},
  raw:JSON.stringify({
   contractVersion:'credit-mock/0.2', requestId:'req-assess-0001', correlationId:'corr-assess-0001',
   decisionId:'dec-assess-0001', capabilityId:capability, capabilityVersion:'1.0',
   purpose:'WORKING_CAPITAL_ASSESSMENT', inputs:{scenarioKey:scenario, subjectRef:'cust-demo-ok'},
   dataClassification:'INTERNAL', requestedAt:'2026-09-18T15:00:00Z', callback:null
  })
 }, {credential});
 const profile = assess('GET_CUSTOMER_PROFILE');
 assert.equal(profile.status,200);
 assert.equal(profile.body.contractVersion,'credit-mock/0.2');
 assert.equal(profile.body.result.profile.legalName,'Empresa Sintética Demo Ltda');
 assert.equal(assess('GET_CUSTOMER_PROFILE','NO_PROFILE').body.status,'PENDING');
 assert.equal(assess('CHECK_CUSTOMER_REGISTRATION','PENDING_REGISTRATION').body.status,'PENDING');
 assert.equal(assess('FIND_ELIGIBLE_PRODUCTS','INELIGIBLE').body.status,'REJECTED');
 const products = assess('FIND_ELIGIBLE_PRODUCTS');
 assert.equal(products.body.result.products[0].offerable,false);
 assert.equal(products.body.result.products[0].commercialValidity,false);
 assert.equal(assess('GET_CREDIT_PROFILE','UNAVAILABLE').status,503);
});
