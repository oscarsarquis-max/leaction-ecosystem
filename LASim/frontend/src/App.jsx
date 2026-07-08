// ============================================================================
// LeAction Simulator - Monte Carlo para Previsibilidade Ágil
// ----------------------------------------------------------------------------
// Componente principal da aplicação. Responsável por:
//  1. Coletar parâmetros da simulação através de um formulário controlado.
//  2. Disparar a simulação no backend (Node) via HTTP POST com axios.
//  3. Exibir os percentis de confiança (50%, 75%, 85%, 95%) em uma tabela.
//  4. Reservar área para futura visualização do histograma com `recharts`.
// ============================================================================

import { useState } from 'react'
import axios from 'axios'

// URL do endpoint do backend. Centralizada em uma constante para facilitar
// uma futura migração para variáveis de ambiente (import.meta.env).
const API_URL = 'http://localhost:3000/calcular-estimativa'

// Percentis de confiança que serão exibidos na tabela de resultados.
// A API deve retornar uma data correspondente para cada um destes.
const PERCENTIS_CONFIANCA = [50, 75, 85, 95]

function App() {
  // --------------------------------------------------------------------------
  // ESTADO DO FORMULÁRIO
  // --------------------------------------------------------------------------
  // Cada campo de entrada é um "controlled component": seu valor vive no
  // estado do React e é sincronizado com o <input> via `value` + `onChange`.
  // Usamos um único objeto `formData` para agrupar todos os parâmetros, o
  // que simplifica o envio para a API (basta enviar o objeto inteiro).
  // --------------------------------------------------------------------------
  const [formData, setFormData] = useState({
    // Data de início da simulação (formato ISO yyyy-mm-dd, aceito por <input type="date">).
    dataInicio: new Date().toISOString().split('T')[0],
    // Faixa estimada de histórias no backlog (mín / máx).
    historiasMin: 50,
    historiasMax: 80,
    // Taxa de divisão: quantas histórias menores cada item do backlog vira (mín / máx).
    taxaDivisaoMin: 1,
    taxaDivisaoMax: 3,
    // Throughput histórico do time (itens entregues por sprint/semana).
    throughputPior: 5,
    throughputComum: 8,
    throughputMelhor: 12,
    // Percentual de foco real da equipe (descontando reuniões, suporte, etc.).
    focoEquipe: 80,
  })

  // --------------------------------------------------------------------------
  // ESTADO DE UI
  // --------------------------------------------------------------------------
  // `carregando` controla a exibição do indicador "Carregando..." enquanto a
  // requisição está em andamento. `resultado` guarda a resposta da API e
  // `erro` armazena a mensagem em caso de falha.
  // --------------------------------------------------------------------------
  const [carregando, setCarregando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [erro, setErro] = useState(null)

  // --------------------------------------------------------------------------
  // HANDLER GENÉRICO DE CAMPOS
  // --------------------------------------------------------------------------
  // Atualiza qualquer campo do formulário usando o atributo `name` do input.
  // Para campos numéricos converte a string em Number; para `date` mantém
  // como string (o backend pode parsear). Usamos o "functional update"
  // (prev => ...) para evitar race conditions.
  // --------------------------------------------------------------------------
  const handleChange = (event) => {
    const { name, value, type } = event.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value,
    }))
  }

  // --------------------------------------------------------------------------
  // SUBMISSÃO DO FORMULÁRIO
  // --------------------------------------------------------------------------
  // 1. Previne o reload padrão do <form>.
  // 2. Limpa o resultado/erro anterior e ativa o estado de carregamento.
  // 3. Faz POST no backend com `axios` enviando o objeto `formData`.
  // 4. Em caso de sucesso: salva a resposta no estado.
  //    Em caso de erro: salva mensagem amigável.
  // 5. Independentemente do resultado, desliga o "carregando" no `finally`.
  // --------------------------------------------------------------------------
  const handleSubmit = async (event) => {
    event.preventDefault()
    setCarregando(true)
    setErro(null)
    setResultado(null)

    try {
      const response = await axios.post(API_URL, formData)
      setResultado(response.data)
    } catch (err) {
      console.error('Falha ao executar simulação:', err)
      setErro(
        err.response?.data?.message ||
          'Não foi possível executar a simulação. Verifique se o backend está rodando em ' +
            API_URL,
      )
    } finally {
      setCarregando(false)
    }
  }

  // --------------------------------------------------------------------------
  // RENDERIZAÇÃO
  // --------------------------------------------------------------------------
  return (
    <div style={styles.app}>
      {/* Cabeçalho da aplicação */}
      <header style={styles.header}>
        <h1 style={styles.title}>LeAction Simulator</h1>
        <p style={styles.subtitle}>
          Simulador de Monte Carlo para previsibilidade ágil
        </p>
      </header>

      {/* Layout principal: formulário à esquerda, resultados à direita.
          Em telas pequenas, o CSS `flex-wrap` faz quebrar para coluna única. */}
      <main style={styles.main}>
        {/* ---------------------------------------------------------------- */}
        {/* COLUNA ESQUERDA - Formulário de entrada                          */}
        {/* ---------------------------------------------------------------- */}
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Parâmetros da Simulação</h2>

          <form onSubmit={handleSubmit}>
            {/* Data de Início */}
            <div style={styles.field}>
              <label style={styles.label} htmlFor="dataInicio">
                Data de Início
              </label>
              <input
                id="dataInicio"
                type="date"
                name="dataInicio"
                value={formData.dataInicio}
                onChange={handleChange}
                style={styles.input}
              />
            </div>

            {/* Histórias - Mín / Máx lado a lado */}
            <fieldset style={styles.fieldset}>
              <legend style={styles.legend}>Histórias no Backlog</legend>
              <div style={styles.row}>
                <NumberField
                  label="Mínimo"
                  name="historiasMin"
                  value={formData.historiasMin}
                  onChange={handleChange}
                />
                <NumberField
                  label="Máximo"
                  name="historiasMax"
                  value={formData.historiasMax}
                  onChange={handleChange}
                />
              </div>
            </fieldset>

            {/* Taxa de Divisão */}
            <fieldset style={styles.fieldset}>
              <legend style={styles.legend}>Taxa de Divisão</legend>
              <div style={styles.row}>
                <NumberField
                  label="Mínimo"
                  name="taxaDivisaoMin"
                  value={formData.taxaDivisaoMin}
                  onChange={handleChange}
                  step="0.1"
                />
                <NumberField
                  label="Máximo"
                  name="taxaDivisaoMax"
                  value={formData.taxaDivisaoMax}
                  onChange={handleChange}
                  step="0.1"
                />
              </div>
            </fieldset>

            {/* Throughput - 3 valores (pior / comum / melhor) */}
            <fieldset style={styles.fieldset}>
              <legend style={styles.legend}>Throughput (itens por sprint)</legend>
              <div style={styles.row}>
                <NumberField
                  label="Pior"
                  name="throughputPior"
                  value={formData.throughputPior}
                  onChange={handleChange}
                />
                <NumberField
                  label="Comum"
                  name="throughputComum"
                  value={formData.throughputComum}
                  onChange={handleChange}
                />
                <NumberField
                  label="Melhor"
                  name="throughputMelhor"
                  value={formData.throughputMelhor}
                  onChange={handleChange}
                />
              </div>
            </fieldset>

            {/* Foco da Equipe (%) */}
            <div style={styles.field}>
              <label style={styles.label} htmlFor="focoEquipe">
                Foco da Equipe (%)
              </label>
              <input
                id="focoEquipe"
                type="number"
                name="focoEquipe"
                min="0"
                max="100"
                value={formData.focoEquipe}
                onChange={handleChange}
                style={styles.input}
              />
            </div>

            {/* Botão de submissão. Fica desabilitado enquanto carrega
                para evitar duplo clique e disparo de múltiplas requisições. */}
            <button
              type="submit"
              disabled={carregando}
              style={{
                ...styles.button,
                ...(carregando ? styles.buttonDisabled : {}),
              }}
            >
              {carregando ? 'Calculando...' : 'Rodar Simulação'}
            </button>
          </form>
        </section>

        {/* ---------------------------------------------------------------- */}
        {/* COLUNA DIREITA - Área de resultados                              */}
        {/* ---------------------------------------------------------------- */}
        <section style={styles.card}>
          <h2 style={styles.sectionTitle}>Resultados</h2>

          {/* Renderização condicional baseada nos estados de UI:
              - carregando -> spinner / texto
              - erro       -> mensagem em vermelho
              - resultado  -> tabela de percentis
              - vazio      -> dica para o usuário                          */}
          {carregando && (
            <div style={styles.loading}>
              <div style={styles.spinner} />
              <p>Carregando simulação...</p>
            </div>
          )}

          {erro && !carregando && (
            <div style={styles.errorBox}>
              <strong>Erro:</strong> {erro}
            </div>
          )}

          {!carregando && !erro && !resultado && (
            <p style={styles.placeholderText}>
              Preencha os parâmetros e clique em <em>Rodar Simulação</em> para
              ver os resultados.
            </p>
          )}

          {resultado && !carregando && (
            <>
              {/* Tabela de Percentis de Confiança */}
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Certeza (%)</th>
                    <th style={styles.th}>Data de Entrega</th>
                  </tr>
                </thead>
                <tbody>
                  {PERCENTIS_CONFIANCA.map((percentil) => (
                    <tr key={percentil}>
                      <td style={styles.td}>{percentil}%</td>
                      <td style={styles.td}>
                        {/* A API pode retornar as datas em diferentes formatos.
                            Aqui suportamos `percentis[50]`, `datas[50]` ou
                            uma chave direta como `p50`. Ajuste conforme o
                            contrato real do backend. */}
                        {resultado.percentis?.[percentil] ??
                          resultado.datas?.[percentil] ??
                          resultado[`p${percentil}`] ??
                          '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Espaço reservado para o histograma (será preenchido depois
                  com a biblioteca `recharts`). Mantemos uma altura fixa para
                  que o layout não "pule" quando o gráfico for inserido. */}
              <div style={styles.chartPlaceholder}>
                <span style={styles.chartPlaceholderText}>
                  Histograma da distribuição (a ser renderizado com recharts)
                </span>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  )
}

// ============================================================================
// COMPONENTE AUXILIAR: NumberField
// ----------------------------------------------------------------------------
// Pequeno componente reutilizável para campos numéricos com label. Evita
// repetição da estrutura <label> + <input type="number"> várias vezes.
// ============================================================================
function NumberField({ label, name, value, onChange, step = '1' }) {
  return (
    <div style={{ ...styles.field, flex: 1 }}>
      <label style={styles.label} htmlFor={name}>
        {label}
      </label>
      <input
        id={name}
        type="number"
        name={name}
        value={value}
        onChange={onChange}
        step={step}
        style={styles.input}
      />
    </div>
  )
}

// ============================================================================
// ESTILOS (CSS-in-JS via objetos JS)
// ----------------------------------------------------------------------------
// Optei por estilos inline em objetos para manter ZERO dependências externas
// (sem styled-components, sem Tailwind). É simples e suficiente para um MVP.
// ============================================================================
const styles = {
  app: {
    minHeight: '100vh',
    background: '#f5f7fa',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif",
    color: '#1f2937',
    padding: '24px',
    boxSizing: 'border-box',
  },
  header: {
    maxWidth: '1200px',
    margin: '0 auto 24px',
    borderBottom: '2px solid #e5e7eb',
    paddingBottom: '16px',
  },
  title: {
    margin: 0,
    fontSize: '28px',
    color: '#0f172a',
  },
  subtitle: {
    margin: '4px 0 0',
    color: '#64748b',
    fontSize: '14px',
  },
  main: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'flex',
    gap: '24px',
    flexWrap: 'wrap',
    alignItems: 'flex-start',
  },
  card: {
    flex: '1 1 420px',
    background: '#ffffff',
    borderRadius: '8px',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
  },
  sectionTitle: {
    marginTop: 0,
    marginBottom: '20px',
    fontSize: '18px',
    color: '#0f172a',
    borderBottom: '1px solid #e5e7eb',
    paddingBottom: '8px',
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    marginBottom: '16px',
  },
  fieldset: {
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '12px 16px 4px',
    marginBottom: '16px',
  },
  legend: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#475569',
    padding: '0 6px',
  },
  row: {
    display: 'flex',
    gap: '12px',
  },
  label: {
    fontSize: '13px',
    fontWeight: 500,
    color: '#374151',
    marginBottom: '6px',
  },
  input: {
    padding: '8px 10px',
    fontSize: '14px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    outline: 'none',
    backgroundColor: '#fff',
  },
  button: {
    width: '100%',
    padding: '12px 16px',
    fontSize: '15px',
    fontWeight: 600,
    color: '#ffffff',
    background: '#2563eb',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    transition: 'background 0.15s ease',
    marginTop: '8px',
  },
  buttonDisabled: {
    background: '#94a3b8',
    cursor: 'not-allowed',
  },
  loading: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '32px',
    color: '#475569',
  },
  spinner: {
    width: '32px',
    height: '32px',
    border: '3px solid #e5e7eb',
    borderTopColor: '#2563eb',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
    marginBottom: '12px',
  },
  errorBox: {
    padding: '12px 16px',
    background: '#fef2f2',
    color: '#b91c1c',
    border: '1px solid #fecaca',
    borderRadius: '6px',
    fontSize: '14px',
  },
  placeholderText: {
    color: '#94a3b8',
    fontSize: '14px',
    textAlign: 'center',
    padding: '24px 0',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginBottom: '24px',
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    background: '#f1f5f9',
    color: '#0f172a',
    fontSize: '13px',
    fontWeight: 600,
    borderBottom: '1px solid #e5e7eb',
  },
  td: {
    padding: '10px 12px',
    fontSize: '14px',
    borderBottom: '1px solid #f1f5f9',
  },
  chartPlaceholder: {
    height: '260px',
    border: '1px dashed #cbd5e1',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: '#fafbfc',
  },
  chartPlaceholderText: {
    color: '#94a3b8',
    fontSize: '13px',
    fontStyle: 'italic',
  },
}

export default App
