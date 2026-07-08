import { getTableColumns } from "../utils/metricas";
import { formatarData, formatarDataHora } from "../utils/datas";
import { getScoreStatus } from "../theme/brand";

const SCORE_COLUMNS = new Set(["score", "pontuacao", "nota"]);
const DATETIME_COLUMNS = new Set(["data_importacao"]);

function formatCellValue(column, value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  if (typeof value === "string" && !Number.isNaN(Date.parse(value))) {
    if (DATETIME_COLUMNS.has(column)) {
      return formatarDataHora(value);
    }
    return formatarData(value);
  }
  return String(value);
}

function formatColumnLabel(column) {
  return column.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function getCellClass(column, value) {
  if (!SCORE_COLUMNS.has(column)) return "text-brand-cinza";
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return "text-brand-cinza";

  const status = getScoreStatus(numeric);
  if (status === "failure") return "font-semibold text-brand-vermelho";
  if (status === "alert") return "font-semibold text-brand-laranja";
  return "font-semibold text-brand-verde";
}

function ItemsTable({ rows }) {
  if (rows.length === 0) {
    return (
      <div className="card-panel border-dashed text-center text-sm text-brand-cinza">
        Nenhum registo encontrado na chave{" "}
        <code className="rounded bg-gray-100 px-1.5 py-0.5 text-brand-verde">itens</code> dos
        JSONs ingeridos.
      </div>
    );
  }

  const columns = getTableColumns(rows);

  return (
    <div className="card-panel overflow-hidden p-0">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-brand-cinza"
                >
                  {formatColumnLabel(column)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {rows.map((row) => (
              <tr key={row.id} className="transition hover:bg-brand-verde/5">
                {columns.map((column) => (
                  <td
                    key={`${row.id}-${column}`}
                    className={`whitespace-nowrap px-4 py-3 text-sm ${getCellClass(column, row[column])}`}
                  >
                    {formatCellValue(column, row[column])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ItemsTable;
