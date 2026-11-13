import { useId, useRef, useState } from "react";
import { Photo } from "../admin/marketplace/Photo";
import { Button } from "../admin/shell/Button";
import { PartnerApiError, partnerApi } from "./partnerApi";

export const MAX_PHOTOS = 3;
const MAX_BYTES = 8 * 1024 * 1024;
const TYPES = ["image/jpeg", "image/png", "image/webp"];

type Props = {
  photos: string[];
  disabled?: boolean;
  onChange: (photos: string[]) => void;
};

export function PhotoPicker({ photos, disabled = false, onChange }: Props) {
  const inputId = useId();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [linkOpen, setLinkOpen] = useState(false);
  const [link, setLink] = useState("");
  const full = photos.length >= MAX_PHOTOS;

  async function upload(file: File) {
    setError(null);
    if (!TYPES.includes(file.type)) {
      setError("Envie a foto em JPEG, PNG ou WebP.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("A foto passa de 8 MB. Reduza o tamanho e tente de novo.");
      return;
    }
    setUploading(true);
    try {
      const saved = await partnerApi.uploadPhoto(file);
      onChange([...photos, saved.url].slice(0, MAX_PHOTOS));
    } catch (reason) {
      setError(reason instanceof PartnerApiError ? reason.message : "Não foi possível enviar a foto.");
    } finally {
      setUploading(false);
      if (fileRef.current) {
        fileRef.current.value = "";
      }
    }
  }

  function addLink() {
    const value = link.trim();
    if (!/^https?:\/\//.test(value)) {
      setError("O endereço precisa começar com https://");
      return;
    }
    setError(null);
    onChange([...photos, value].slice(0, MAX_PHOTOS));
    setLink("");
    setLinkOpen(false);
  }

  return (
    <div className="ptn-picker">
      <ul className="ptn-picker-grid" aria-label="Fotos do produto">
        {photos.map((src, index) => (
          <li key={`${src}-${index}`} className="ptn-picker-item">
            <Photo className="ptn-photo-preview" src={src} alt={`Foto ${index + 1}`} />
            <div className="ptn-picker-bar">
              <span className="mkt-muted">{index === 0 ? "Principal" : `Foto ${index + 1}`}</span>
              <div className="mkt-row">
                {index > 0 && !disabled ? (
                  <button
                    type="button"
                    className="mkt-link"
                    onClick={() => onChange([src, ...photos.filter((_, position) => position !== index)])}
                    aria-label={`Tornar a foto ${index + 1} principal`}
                  >
                    Tornar principal
                  </button>
                ) : null}
                {disabled ? null : (
                  <button
                    type="button"
                    className="mkt-link is-danger"
                    onClick={() => onChange(photos.filter((_, position) => position !== index))}
                    aria-label={`Remover a foto ${index + 1}`}
                  >
                    Remover
                  </button>
                )}
              </div>
            </div>
          </li>
        ))}
        {!full && !disabled ? (
          <li className="ptn-picker-item">
            <label htmlFor={inputId} className={uploading ? "ptn-picker-add is-busy" : "ptn-picker-add"}>
              <span className="ptn-picker-plus" aria-hidden="true">
                +
              </span>
              <span>{uploading ? "Enviando…" : photos.length ? "Adicionar outra foto" : "Adicionar foto"}</span>
              <span className="mkt-muted">JPEG, PNG ou WebP · até 8 MB</span>
            </label>
            <input
              ref={fileRef}
              id={inputId}
              className="mkt-sr"
              type="file"
              accept={TYPES.join(",")}
              disabled={uploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  void upload(file);
                }
              }}
            />
          </li>
        ) : null}
      </ul>
      {error ? (
        <p className="mkt-alert" role="alert">
          {error}
        </p>
      ) : null}
      {!full && !disabled ? (
        linkOpen ? (
          <div className="ptn-picker-link">
            <label className="mkt-field mkt-grow">
              Endereço da imagem
              <input
                className="mkt-input"
                type="url"
                inputMode="url"
                placeholder="https://"
                value={link}
                onChange={(event) => setLink(event.target.value)}
              />
            </label>
            <Button onClick={addLink}>Usar este endereço</Button>
            <Button
              onClick={() => {
                setLinkOpen(false);
                setLink("");
              }}
            >
              Cancelar
            </Button>
          </div>
        ) : (
          <button type="button" className="mkt-link ptn-picker-alt" onClick={() => setLinkOpen(true)}>
            A foto já está na internet? Colar o endereço
          </button>
        )
      ) : null}
    </div>
  );
}
