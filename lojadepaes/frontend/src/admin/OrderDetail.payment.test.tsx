import { render, screen, within } from "@testing-library/react";
import { OrderDetailView } from "./OrderDetail";
import type { OrderDetail, PaymentRecord } from "./types";

const pix: PaymentRecord = {id:"pix",provider:"actionhub",external_reference:"old-pix",expected_cents:7000,currency:"BRL",financial_status:"cancelled",external_status_raw:"cancelled",amount_paid_cents:null,amount_refunded_cents:null,confirmed_at:null,last_synced_at:"2026-10-27T20:08:00Z",sanitized_error:"cancelled",method:"pix",pix_expires_at:null};
const card: PaymentRecord = {...pix,id:"card",external_reference:"paid-card",financial_status:"paid",external_status_raw:"approved",amount_paid_cents:7000,amount_refunded_cents:0,confirmed_at:"2026-10-27T20:10:26Z",sanitized_error:null,method:"card"};
function show(records: PaymentRecord[], settled: boolean) {
  const money={cents:7000,currency:"BRL"};
  const order={id:"order",public_reference:"LP-TEST",status:"confirmed",created_at:"2026-10-27T20:00:00Z",currency:"BRL",total:money,subtotal:money,delivery_fee:{...money,cents:0},discount:{...money,cents:0},items:[],notes:[],history:[],allowed_actions:[],payment_records:records,payment_events:[],financially_settled:settled,financial_kind:settled?"settled":"unknown",address:{},fulfillment_modality:"delivery",holds_capacity:true} as unknown as OrderDetail;
  render(<OrderDetailView order={order} loading={false} error={null} conflict={false} busyAction={null} noteError={null} onBack={()=>{}} onReload={()=>{}} onAction={()=>{}} onNote={()=>{}} onEvaluateAdaptation={()=>{}} />);
  return within(screen.getByRole("heading",{name:"Pagamento do pedido"}).closest("article")!);
}
it("shows the actual payment method and value, without cancelled attempts as commercial states",()=>{
  const panel=show([pix,card],true);
  expect(panel.getByText("Pago")).toBeInTheDocument();
  expect(panel.getByText("Forma de pagamento: Cartão")).toBeInTheDocument();
  expect(panel.getByText(/Valor recebido: R\$\s*70,00/)).toBeInTheDocument();
  expect(panel.getByText(/Referência do pagamento: paid-card/)).toBeInTheDocument();
  expect(panel.queryByText(/cancelled|Cancelado|old-pix|applied/)).not.toBeInTheDocument();
});
it("does not present a pending attempt as a payment received",()=>{
  const panel=show([pix,{...card,financial_status:"pending",amount_paid_cents:null,confirmed_at:null}],false);
  expect(panel.getByText("Aguardando confirmação do pagamento")).toBeInTheDocument();
  expect(panel.queryByText(/^Valor recebido:/)).not.toBeInTheDocument();
  expect(panel.queryByText("Pago")).not.toBeInTheDocument();
});
