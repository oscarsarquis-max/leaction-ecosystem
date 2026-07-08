from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app) # Fundamental para evitar erros de bloqueio (CORS) entre portas diferentes

@app.route('/api/simular', methods=['POST'])
def simular():
    try:
        dados = request.json
        trials = 1000 # Número de simulações Monte Carlo
        
        # Mapeando os dados do Frontend
        min_hist = float(dados.get('historiasMin', 50))
        max_hist = float(dados.get('historiasMax', 80))
        min_split = float(dados.get('splitMin', 1))
        max_split = float(dados.get('splitMax', 3))
        tp_pior = float(dados.get('tpPior', 5))
        tp_comum = float(dados.get('tpComum', 8))
        tp_melhor = float(dados.get('tpMelhor', 12))
        foco = float(dados.get('foco', 80)) / 100.0
        
        # Parse da data de início
        data_inicio_str = dados.get('dataInicio', datetime.today().strftime('%Y-%m-%d'))
        data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
        
        resultados_dias = []
        
        for _ in range(trials):
            # 1. Quantidade base e Split (Uniforme)
            historias_base = np.random.uniform(min_hist, max_hist)
            split = np.random.uniform(min_split, max_split)
            total_historias = historias_base * split
            
            # 2. Throughput Efetivo (Triangular)
            tp_base = np.random.triangular(tp_pior, tp_comum, tp_melhor)
            tp_efetivo = max(tp_base * foco, 0.1) # Evita divisão por zero
            
            # 3. Cálculo de dias (Considerando Throughput = 1 semana = 7 dias)
            dias = (total_historias / tp_efetivo) * 7
            resultados_dias.append(dias)
        
        # Calculando as datas com base nos percentis (Certeza)
        percentis = {
            '50': (data_inicio + timedelta(days=np.percentile(resultados_dias, 50))).strftime('%d/%m/%Y'),
            '75': (data_inicio + timedelta(days=np.percentile(resultados_dias, 75))).strftime('%d/%m/%Y'),
            '85': (data_inicio + timedelta(days=np.percentile(resultados_dias, 85))).strftime('%d/%m/%Y'),
            '95': (data_inicio + timedelta(days=np.percentile(resultados_dias, 95))).strftime('%d/%m/%Y')
        }
        
        return jsonify({
            'status': 'sucesso',
            'simulacoes': trials,
            'percentis': percentis
        }), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)