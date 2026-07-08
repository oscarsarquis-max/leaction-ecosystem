import { formatarData, formatarDataHora, formatarPeriodo } from "../utils/datas";

function StatusBadge({ status }) {
  const normalized = String(status || "").toUpperCase();
  const isSuccess = normalized === "SUCESSO" || normalized === "SUCCESS";
  const classes = isSuccess
    ? "bg-brand-verde/10 text-brand-verde"
    : normalized === "PROCESSANDO"
      ? "bg-brand-laranja/10 text-brand-laranja"
      : "bg-brand-vermelho/10 text-brand-vermelho";

  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase ${classes}`}>
      {status || "—"}
    </span>
  );
}

function CelulaTexto({ valor, className = "" }) {
  return (
    <td className={`px-4 py-3 text-sm text-brand-cinza ${className}`}>
      {valor || "—"}
    </td>
  );
}

function rotuloColaborador(item) {
  if (item.colaborador_nome && item.colaborador_matricula) {
    return `${item.colaborador_nome} (${item.colaborador_matricula})`;
  }

  return item.colaborador_nome || item.colaborador_matricula || "—";
}

function ImportHistoryTable({ importacoes }) {
  if (importacoes.length === 0) {
    return (
      <div className="card-panel border-dashed text-center text-sm text-brand-cinza">
        Nenhum registo de importação encontrado.
      </div>
    );
  }

  return (
    <div className="card-panel p-0">
      <div className="border-b border-gray-100 px-4 py-3 text-xs text-brand-cinza/70 sm:px-5">
        Deslize horizontalmente para ver todas as colunas.
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[1200px] w-full border-collapse text-left">
          <thead>
            <tr className="bg-brand-verde text-xs font-semibold uppercase tracking-wide text-white">
              <th className="whitespace-nowrap px-4 py-3">ID</th>
              <th className="whitespace-nowrap px-4 py-3">Ficheiro</th>
              <th className="whitespace-nowrap px-4 py-3">Cód. Indicador</th>
              <th className="whitespace-nowrap px-4 py-3">Indicador</th>
              <th className="whitespace-nowrap px-4 py-3">Grupo</th>
              <th className="whitespace-nowrap px-4 py-3">Colaborador</th>
              <th className="whitespace-nowrap px-4 py-3">Importado em</th>
              <th className="whitespace-nowrap px-4 py-3">Data referência</th>
              <th className="whitespace-nowrap px-4 py-3">Período</th>
              <th className="whitespace-nowrap px-4 py-3">Estado</th>
              <th className="min-w-[200px] whitespace-nowrap px-4 py-3">Detalhe / Erro</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {importacoes.map((item) => (
              <tr key={item.id} className="transition hover:bg-brand-verde/5">
                <CelulaTexto valor={item.id} className="whitespace-nowrap font-mono text-xs" />
                <td className="max-w-[220px] px-4 py-3 text-sm font-medium text-brand-cinza">
                  <span className="block truncate" title={item.nome_arquivo || undefined}>
                    {item.nome_arquivo || "—"}
                  </span>
                </td>
                <CelulaTexto
                  valor={item.cod_indicador}
                  className="whitespace-nowrap font-mono text-xs"
                />
                <CelulaTexto valor={item.nome_indicador} className="min-w-[180px]" />
                <CelulaTexto valor={item.nome_grupo} className="whitespace-nowrap" />
                <td className="min-w-[180px] px-4 py-3 text-sm text-brand-cinza">
                  <span className="line-clamp-2" title={rotuloColaborador(item)}>
                    {rotuloColaborador(item)}
                  </span>
                </td>
                <CelulaTexto
                  valor={formatarDataHora(item.data_importacao)}
                  className="whitespace-nowrap"
                />
                <CelulaTexto
                  valor={formatarData(item.data_referencia)}
                  className="whitespace-nowrap"
                />
                <CelulaTexto
                  valor={
                    !item.data_referencia_inicio && !item.data_referencia_fim
                      ? "Não informado no JSON"
                      : formatarPeriodo(item.data_referencia_inicio, item.data_referencia_fim)
                  }
                  className="whitespace-nowrap"
                />
                <td className="whitespace-nowrap px-4 py-3">
                  <StatusBadge status={item.status} />
                </td>
                <td className="max-w-[280px] px-4 py-3 text-sm text-brand-cinza">
                  <span
                    className="line-clamp-3 break-words"
                    title={item.mensagem_erro || undefined}
                  >
                    {item.mensagem_erro || "—"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ImportHistoryTable;
