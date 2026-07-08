const express = require('express');
const axios = require('axios');
const cors = require('cors');
// const { Pool } = require('pg'); // Descomentaremos quando formos ligar o banco

const app = express();
app.use(express.json());
app.use(cors()); // Permite que o frontend (porta 5173) chame este backend (porta 3000)

app.post('/calcular-estimativa', async (req, res) => {
    const dadosFormulario = req.body;
    console.log("Recebido do Frontend:", dadosFormulario);

    try {
        // TODO: Aqui entrará a lógica de salvar os dados no PostgreSQL no futuro.

        // Repassa a requisição para o motor Python
        const flaskResponse = await axios.post('http://localhost:5000/api/simular', dadosFormulario);

        // O Frontend feito pelo Cursor espera um formato de dados para alimentar a tabela.
        // Vamos formatar a resposta exatamente como o App.jsx espera.
        res.status(200).json({
            mensagem: "Cálculo realizado com sucesso",
            percentis: flaskResponse.data.percentis // Acessando os percentis gerados pelo Python
        });

    } catch (error) {
        console.error("Erro ao processar simulação:", error.message);
        res.status(500).json({ 
            erro: 'Falha ao se comunicar com o motor de simulação (Python).' 
        });
    }
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`🚀 Gateway Node.js rodando na porta ${PORT}`);
});
