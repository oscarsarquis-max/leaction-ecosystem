export type DeliveryAddressInput = {
  delivery_street: string;
  delivery_number: string;
  delivery_complement: string;
  delivery_district: string;
  delivery_city: string;
  delivery_state: string;
  delivery_postal_code: string;
};

export const BRAZIL_UFS: Array<{ value: string; label: string }> = [
  { value: "AC", label: "AC — Acre" },
  { value: "AL", label: "AL — Alagoas" },
  { value: "AP", label: "AP — Amapá" },
  { value: "AM", label: "AM — Amazonas" },
  { value: "BA", label: "BA — Bahia" },
  { value: "CE", label: "CE — Ceará" },
  { value: "DF", label: "DF — Distrito Federal" },
  { value: "ES", label: "ES — Espírito Santo" },
  { value: "GO", label: "GO — Goiás" },
  { value: "MA", label: "MA — Maranhão" },
  { value: "MT", label: "MT — Mato Grosso" },
  { value: "MS", label: "MS — Mato Grosso do Sul" },
  { value: "MG", label: "MG — Minas Gerais" },
  { value: "PA", label: "PA — Pará" },
  { value: "PB", label: "PB — Paraíba" },
  { value: "PR", label: "PR — Paraná" },
  { value: "PE", label: "PE — Pernambuco" },
  { value: "PI", label: "PI — Piauí" },
  { value: "RJ", label: "RJ — Rio de Janeiro" },
  { value: "RN", label: "RN — Rio Grande do Norte" },
  { value: "RS", label: "RS — Rio Grande do Sul" },
  { value: "RO", label: "RO — Rondônia" },
  { value: "RR", label: "RR — Roraima" },
  { value: "SC", label: "SC — Santa Catarina" },
  { value: "SP", label: "SP — São Paulo" },
  { value: "SE", label: "SE — Sergipe" },
  { value: "TO", label: "TO — Tocantins" },
];

export function emptyDeliveryAddress(): DeliveryAddressInput {
  return {
    delivery_street: "",
    delivery_number: "",
    delivery_complement: "",
    delivery_district: "",
    delivery_city: "",
    delivery_state: "",
    delivery_postal_code: "",
  };
}

export function maskPostalCode(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

export function addressFieldErrors(value: DeliveryAddressInput): Partial<Record<keyof DeliveryAddressInput, string>> {
  const errors: Partial<Record<keyof DeliveryAddressInput, string>> = {};
  if (!value.delivery_street.trim()) {
    errors.delivery_street = "Informe a rua do endereço de entrega.";
  }
  if (!value.delivery_number.trim()) {
    errors.delivery_number = "Informe o número. Se não houver número, escreva S/N.";
  }
  if (!value.delivery_district.trim()) {
    errors.delivery_district = "Informe o bairro da entrega.";
  }
  if (!value.delivery_city.trim()) {
    errors.delivery_city = "Informe a cidade da entrega.";
  }
  const uf = value.delivery_state.trim().toUpperCase();
  if (!BRAZIL_UFS.some((item) => item.value === uf)) {
    errors.delivery_state = "Escolha a sigla do estado, como CE.";
  }
  if (value.delivery_postal_code.replace(/\D/g, "").length !== 8) {
    errors.delivery_postal_code = "Informe o CEP com 8 dígitos.";
  }
  return errors;
}

export function addressValidationMessage(value: DeliveryAddressInput): string | null {
  const errors = addressFieldErrors(value);
  return (
    errors.delivery_street ||
    errors.delivery_number ||
    errors.delivery_district ||
    errors.delivery_city ||
    errors.delivery_state ||
    errors.delivery_postal_code ||
    null
  );
}

type Props = {
  value: DeliveryAddressInput;
  onChange: (next: DeliveryAddressInput) => void;
  note?: "checkout" | "accepted";
  errors?: Partial<Record<keyof DeliveryAddressInput, string>>;
};

export function DeliveryAddressFields({ value, onChange, note = "checkout", errors }: Props) {
  function set(field: keyof DeliveryAddressInput, next: string) {
    onChange({ ...value, [field]: next });
  }

  return (
    <fieldset className="checkout-address">
      <legend>Endereço de entrega</legend>
      <p className="fornada-note">
        {note === "accepted"
          ? "O horário preferido continua sendo preferência, não uma janela prometida. Completar o endereço não muda o aceite, a data, o total nem a reserva."
          : "O pedido será entregue no endereço indicado. A data escolhida e o horário preferido ainda dependem do aceite de A Loja."}
      </p>
      <label>
        Rua
        <input
          value={value.delivery_street}
          onChange={(event) => set("delivery_street", event.target.value)}
          required
          maxLength={160}
          autoComplete="street-address"
          aria-invalid={Boolean(errors?.delivery_street)}
        />
        {errors?.delivery_street ? <span className="field-error">{errors.delivery_street}</span> : null}
      </label>
      <div className="checkout-address-row">
        <label>
          Número
          <input
            value={value.delivery_number}
            onChange={(event) => set("delivery_number", event.target.value)}
            required
            maxLength={20}
            aria-invalid={Boolean(errors?.delivery_number)}
          />
          {errors?.delivery_number ? <span className="field-error">{errors.delivery_number}</span> : null}
        </label>
        <label>
          Complemento
          <input
            value={value.delivery_complement}
            onChange={(event) => set("delivery_complement", event.target.value)}
            maxLength={80}
          />
        </label>
      </div>
      <label>
        Bairro
        <input
          value={value.delivery_district}
          onChange={(event) => set("delivery_district", event.target.value)}
          required
          maxLength={80}
          aria-invalid={Boolean(errors?.delivery_district)}
        />
        {errors?.delivery_district ? <span className="field-error">{errors.delivery_district}</span> : null}
      </label>
      <label>
        Cidade
        <input
          value={value.delivery_city}
          onChange={(event) => set("delivery_city", event.target.value)}
          required
          maxLength={80}
          autoComplete="address-level2"
          aria-invalid={Boolean(errors?.delivery_city)}
        />
        {errors?.delivery_city ? <span className="field-error">{errors.delivery_city}</span> : null}
      </label>
      <div className="checkout-address-row">
        <label>
          Estado
          <select
            value={value.delivery_state}
            onChange={(event) => set("delivery_state", event.target.value)}
            required
            autoComplete="address-level1"
            aria-invalid={Boolean(errors?.delivery_state)}
          >
            <option value="">Selecione a sigla</option>
            {BRAZIL_UFS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          {errors?.delivery_state ? <span className="field-error">{errors.delivery_state}</span> : null}
        </label>
        <label>
          CEP
          <input
            value={value.delivery_postal_code}
            onChange={(event) => set("delivery_postal_code", maskPostalCode(event.target.value))}
            required
            inputMode="numeric"
            autoComplete="postal-code"
            aria-invalid={Boolean(errors?.delivery_postal_code)}
          />
          {errors?.delivery_postal_code ? <span className="field-error">{errors.delivery_postal_code}</span> : null}
        </label>
      </div>
    </fieldset>
  );
}

export function formatDeliveryAddress(address: {
  street: string;
  number: string | null;
  complement: string | null;
  district: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
}): string {
  const postal = address.postal_code || "";
  const cep = postal.length === 8 ? `${postal.slice(0, 5)}-${postal.slice(5)}` : postal;
  const complement = address.complement ? `, ${address.complement}` : "";
  return `${address.street}, ${address.number || ""}${complement} — ${address.district || ""}, ${address.city || ""}/${address.state || ""} ${cep}`.trim();
}
