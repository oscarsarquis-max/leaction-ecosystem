export type DeliveryAddressInput = {
  delivery_street: string;
  delivery_number: string;
  delivery_complement: string;
  delivery_district: string;
  delivery_city: string;
  delivery_state: string;
  delivery_postal_code: string;
};

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

type Props = {
  value: DeliveryAddressInput;
  onChange: (next: DeliveryAddressInput) => void;
};

export function DeliveryAddressFields({ value, onChange }: Props) {
  function set(field: keyof DeliveryAddressInput, next: string) {
    onChange({ ...value, [field]: next });
  }

  return (
    <fieldset className="checkout-address">
      <legend>Endereço de entrega</legend>
      <label>
        Rua
        <input
          value={value.delivery_street}
          onChange={(event) => set("delivery_street", event.target.value)}
          required
          maxLength={160}
          autoComplete="street-address"
        />
      </label>
      <div className="checkout-address-row">
        <label>
          Número
          <input
            value={value.delivery_number}
            onChange={(event) => set("delivery_number", event.target.value)}
            required
            maxLength={20}
          />
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
        />
      </label>
      <label>
        Cidade
        <input
          value={value.delivery_city}
          onChange={(event) => set("delivery_city", event.target.value)}
          required
          maxLength={80}
          autoComplete="address-level2"
        />
      </label>
      <div className="checkout-address-row">
        <label>
          Estado
          <input
            value={value.delivery_state}
            onChange={(event) => set("delivery_state", event.target.value.toUpperCase())}
            required
            minLength={2}
            maxLength={2}
            autoComplete="address-level1"
          />
        </label>
        <label>
          CEP
          <input
            value={value.delivery_postal_code}
            onChange={(event) => set("delivery_postal_code", event.target.value)}
            required
            inputMode="numeric"
            minLength={8}
            maxLength={9}
            autoComplete="postal-code"
          />
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
