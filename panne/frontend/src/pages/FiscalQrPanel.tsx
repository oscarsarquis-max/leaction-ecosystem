import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

type Reading = {
  recognized?: boolean;
  import_available?: boolean;
  message?: string;
  reason?: string;
  model_label?: string;
  model?: string;
  uf?: string;
  environment?: string;
  environment_label?: string;
  emission?: string;
  emission_label?: string;
  emission_matches_layout?: boolean;
  dependency?: string;
  access_key?: string;
  existing_document_id?: string | null;
  number?: string;
  series?: string;
  consultation_url?: string | null;
  items?: unknown[];
};

type Phase = "aguardando" | "permissao" | "lendo" | "consultando" | "pronto" | "invalido" | "indisponivel";

const PHASE_LABEL: Record<Phase, string> = {
  aguardando: "Aguardando o código ou o endereço.",
  permissao: "Aguardando permissão da câmera.",
  lendo: "Lendo o QR Code.",
  consultando: "Identificando o código.",
  pronto: "Chave lida no código.",
  invalido: "Código inválido.",
  indisponivel: "Consulta indisponível.",
};

export function FiscalQrPanel({
  api,
  onUseKey,
}: {
  api: { readFiscalQr: (url: string) => Promise<{ data: Record<string, unknown> }> };
  onUseKey: (accessKey: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const timerRef = useRef<number | null>(null);
  const generation = useRef(0);
  const cameraRead = useRef(false);
  const [phase, setPhase] = useState<Phase>("aguardando");
  const [pasted, setPasted] = useState("");
  const [reading, setReading] = useState<Reading | null>(null);
  const [detail, setDetail] = useState("");

  function stopCamera() {
    generation.current += 1;
    if (timerRef.current != null) window.clearInterval(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
  }

  useEffect(() => stopCamera, []);

  async function consult(raw: string) {
    const url = raw.trim();
    if (!url) return;
    setPhase("consultando");
    setReading(null);
    try {
      const response = await api.readFiscalQr(url);
      const data = response.data as Reading;
      setReading(data);
      if (data.recognized) setPhase("pronto");
      else setPhase("invalido");
      setDetail(
        data.recognized
          ? data.message || "Consulta disponível; importação automática indisponível nesta origem."
          : "Este código não abriu uma NFC-e. Você pode colar outro endereço ou preencher a nota.",
      );
    } catch {
      setPhase("indisponivel");
      setDetail("A consulta não respondeu. O texto colado permanece aqui. Nada foi gravado.");
    }
  }

  async function startCamera() {
    stopCamera();
    const token = generation.current;
    cameraRead.current = false;
    setPhase("permissao");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      if (token !== generation.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setPhase("lendo");
      const Detector = (window as unknown as { BarcodeDetector?: new (opts: { formats: string[] }) => { detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue?: string }>> } }).BarcodeDetector;
      if (!Detector) {
        setPhase("aguardando");
        setDetail("A câmera abriu, mas este navegador não lê QR sozinho. Cole o endereço.");
        return;
      }
      const detector = new Detector({ formats: ["qr_code"] });
      timerRef.current = window.setInterval(() => {
        const video = videoRef.current;
        if (!video || token !== generation.current || cameraRead.current) return;
        void detector.detect(video).then((codes) => {
          const value = codes[0]?.rawValue;
          if (!value || token !== generation.current || cameraRead.current) return;
          cameraRead.current = true;
          stopCamera();
          void consult(value);
        }).catch(() => undefined);
      }, 500);
    } catch {
      if (token === generation.current) {
        stopCamera();
        setPhase("indisponivel");
        setDetail("A câmera não foi permitida. Cole o endereço do QR Code.");
      }
    }
  }

  const environment =
    reading?.environment_label ||
    (reading?.environment === "producao"
      ? "produção"
      : reading?.environment === "homologacao"
        ? "homologação"
        : null);
  const emission =
    reading?.emission_label ||
    (reading?.emission === "contingencia" ? "contingência" : reading?.emission === "online" ? "online" : null);

  return (
    <section className="card entry-option" aria-label="Ler QR Code">
      <h2>Leia o QR Code da nota</h2>
      <p>
        Aponte a câmera ou cole o endereço. Isto lê a chave. Não importa a nota e não lança estoque.
      </p>
      <p className="meta" role="status">
        {PHASE_LABEL[phase]}
      </p>
      <div className="qr-frame">
        <video ref={videoRef} muted playsInline />
      </div>
      <p className="entry-actions">
        <button type="button" className="ghost" onClick={() => void startCamera()}>
          Usar câmera
        </button>
        <button
          type="button"
          className="ghost"
          onClick={() => {
            stopCamera();
            setPhase("aguardando");
            setReading(null);
            setDetail("");
          }}
        >
          Cancelar
        </button>
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void consult(pasted);
        }}
      >
        <label>
          Colar endereço do QR Code
          <input
            value={pasted}
            autoComplete="off"
            onChange={(event) => setPasted(event.target.value)}
          />
        </label>
        <button
          type="submit"
          className={reading?.recognized ? "ghost" : "primary"}
          disabled={!pasted.trim() || phase === "consultando"}
        >
          Ler código
        </button>
      </form>
      {detail ? (
        <p className={phase === "invalido" || phase === "indisponivel" ? "error" : "meta"} role="status">
          {detail}
        </p>
      ) : null}
      {reading?.recognized ? (
        <div>
          <p>
            {reading.model_label} {reading.uf ? `· ${reading.uf}` : ""} {environment ? `· ${environment}` : ""}
            {emission ? ` · ${emission}` : ""}
            {reading.number ? ` · nota ${reading.number}` : ""}
            {reading.series ? ` · série ${reading.series}` : ""}
          </p>
          <p className="meta">Número e série foram lidos no código. A assinatura fiscal não foi conferida.</p>
          {reading.emission_matches_layout === false ? (
            <p className="meta">O código e a chave divergem sobre a emissão.</p>
          ) : null}
          {reading.dependency ? <p className="meta">{reading.dependency}</p> : null}
          {reading.consultation_url ? (
            <p>
              <a href={reading.consultation_url} target="_blank" rel="noopener noreferrer">
                Abrir a consulta oficial
              </a>
            </p>
          ) : null}
          {reading.existing_document_id ? (
            <Link className="primary" to={`/gestao/compras/entradas/${reading.existing_document_id}`}>
              Abrir a nota
            </Link>
          ) : (
            <button type="button" className="primary" onClick={() => onUseKey(reading.access_key || "")}>
              Preencher a nota com esta chave
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}
