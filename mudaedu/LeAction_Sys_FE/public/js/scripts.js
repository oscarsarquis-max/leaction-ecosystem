document.addEventListener('DOMContentLoaded', () => {

    // --- VARIÁVEL GLOBAL PARA O DIAGNÓSTICO--- diagnosticos.ejs
    const reportData = window.diagnosticReport || {};

    window.api = {
        async fetchRecords(tableName, query = '') {
            try {
                const encodedQuery = encodeURIComponent(query);
                const url = `${API_BASE_URL}/${tableName}?search_query=${encodedQuery}`;
                const response = await fetch(url);
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}. Detalhes: ${errorText}`);
                }
                const data = await response.json();
                return data;
            } catch (error) {
                console.error(`Erro ao buscar dados de ${tableName}:`, error);
                return [];
            }
        },
        async createRecord(tableName, data) {
            try {
                const response = await fetch(`${API_BASE_URL}/${tableName}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMessage = `Erro ao criar registro em ${tableName}: ${response.status} - ${response.statusText}. Detalhes: ${errorText}`;
                    try {
                        const errorJson = JSON.parse(errorText);
                        if (errorJson.error) errorMessage = `Erro ao criar registro: ${errorJson.error}`;
                    } catch (e) { /* not JSON */ }
                    throw new Error(errorMessage);
                }
                return await response.json();
            } catch (error) {
                console.error(`Erro ao criar registro em ${tableName}:`, error);
                alert(error.message);
                return null;
            }
        },
        async updateRecord(tableName, id, data) {
            try {
                const response = await fetch(`${API_BASE_URL}/${tableName}/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMessage = `Erro ao atualizar registro em ${tableName}: ${response.status} - ${response.statusText}. Detalhes: ${errorText}`;
                     try {
                        const errorJson = JSON.parse(errorText);
                        if (errorJson.error) errorMessage = `Erro ao atualizar registro: ${errorJson.error}`;
                    } catch (e) { /* not JSON */ }
                    throw new Error(errorMessage);
                }
                return await response.json();
            } catch (error) {
                console.error(`Erro ao atualizar registro em ${tableName}:`, error);
                alert(error.message);
                return null;
            }
        },
        async fetchRecordById(tableName, id) {
            try {
                const url = `${API_BASE_URL}/${tableName}/${id}`;
                const response = await fetch(url);
                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}. Detalhes: ${errorText}`);
                }
                const data = await response.json();
                return data;
            } catch (error) {
                console.error(`Erro ao buscar registro ${id} de ${tableName}:`, error);
                alert(`Erro ao buscar registro: ${error.message}`);
                return null;
            }
        },
        async deleteRecord(tableName, id) {
            if (!confirm(`Tem certeza que deseja deletar o registro ${id} da tabela ${tableName}?`)) {
                return false;
            }
            try {
                const response = await fetch(`${API_BASE_URL}/${tableName}/${id}`, {
                    method: 'DELETE'
                });
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMessage = `Não foi possível deletar o registro.`;
                    if (response.status === 409) {
                        try {
                            const errorJson = JSON.parse(errorText);
                            if (errorJson.details && errorJson.details.includes('Violação de chave estrangeira')) {
                                if (tableName === 'leaf_bloc') {
                                    errorMessage = `Não foi possível deletar o Bloco (ID: ${id}). Existem Sprints ou outros registros que dependem dele. Por favor, remova ou desassocie os registros dependentes primeiro.`;
                                } else {
                                    errorMessage = `Não foi possível deletar o registro (ID: ${id}) da tabela '${tableName}'. Existem outros registros que dependem deste. Por favor, remova ou desassocie os registros dependentes primeiro.`;
                                }
                            } else if (errorJson.error) {
                                errorMessage = `Erro ao deletar: ${errorJson.error}`;
                            } else {
                                errorMessage = `Não foi possível deletar o registro (ID: ${id}) da tabela '${tableName}'. Ele está sendo referenciado por outros registros.`;
                            }
                        } catch (jsonParseError) {
                            errorMessage = `Não foi possível deletar o registro (ID: ${id}) da tabela '${tableName}'. Ele está sendo referenciado por outros registros.`;
                            console.warn("Could not parse 409 error response as JSON:", jsonParseError, "Response text:", errorText);
                        }
                    } else {
                        try {
                            const errorJson = JSON.parse(errorText);
                            if (errorJson.error) {
                                errorMessage = `Erro ao deletar: ${errorJson.error}`;
                            } else {
                                errorMessage = `Erro inesperado ao deletar registro: ${response.status} - ${response.statusText}. Detalhes: ${errorText}`;
                            }
                        } catch (jsonParseError) {
                            errorMessage = `Erro inesperado ao deletar registro: ${response.status} - ${response.statusText}.`;
                            console.warn("Could not parse error response as JSON for non-409 status:", jsonParseError, "Response text:", errorText);
                        }
                    }
                    throw new Error(errorMessage);
                }
                return await response.json();
            } catch (error) {
                console.error(`Erro ao deletar registro em ${tableName}:`, error);
                alert(error.message);
                return null;
            }
        }
    };

    // --- Funções Auxiliares Genéricas ---
    function formatDateForInput(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        date.setMinutes(date.getMinutes() + date.getTimezoneOffset());
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    async function populateSelect(selectElement, tableName, idField, nameField) {
        if (!selectElement) return;
        selectElement.innerHTML = '<option value="">Carregando...</option>';
        const records = await window.api.fetchRecords(tableName);
        selectElement.innerHTML = '<option value="">Selecione...</option>';
        if (records && records.length > 0) {
            records.forEach(record => {
                const option = document.createElement('option');
                option.value = record[idField];
                option.textContent = record[nameField];
                selectElement.appendChild(option);
            });
        } else {
            selectElement.innerHTML = '<option value="">Nenhum item encontrado</option>';
        }
    }

// --- Lógica para a página de Clientes (VERSÃO DEFINITIVA B2B) ---
if (document.getElementById('clientes-page')) {
    const form = document.querySelector('#clientes-form');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const tableBody = document.querySelector('#clientes-table tbody');
    const saveOrAddButton = document.getElementById('saveOrAddButton');

    let currentRecordIdForEdit = null;

    // 1. LISTAGEM (As 6 Colunas)
    async function loadClientes(query = '') {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:20px;">Carregando...</td></tr>';

        try {
            const response = await fetch(`/api/admin/clientes-search?q=${encodeURIComponent(query)}`);
            const records = await response.json();
            tableBody.innerHTML = '';

            if (records && records.length > 0) {
                records.forEach(record => {
                    const row = tableBody.insertRow();

                    const isChecked = record.tem_projeto ? 'checked' : '';
                    const statusLabel = record.tem_projeto ? 'ATIVO' : 'OFF';
                    const statusColor = record.tem_projeto ? '#27ae60' : '#ccc';

                    // Formatação do contato
                    const contatoHtml = `
                        <div style="display:flex; flex-direction:column; font-size:0.85em;">
                            <span title="Email">📧 ${record.mail_clie || '-'}</span>
                            <span title="Telefone" style="color:#666; margin-top:3px;">📞 ${record.fone_clie || ''}</span>
                        </div>
                    `;

                    // Formatação da Empresa (CNPJ abaixo do nome)
                    const empresaHtml = `
                        <strong>${record.empresa_clie || 'Não Informado'}</strong><br>
                        <span style="font-size:0.75em; color:#999;">CNPJ: ${record.docu_clie || '-'}</span>
                    `;

                    row.innerHTML = `
                        <td style="color:#888;">#${record.id_clie}</td>
                        
                        <td>
                            <i class="fas fa-user-circle" style="color:#ddd; margin-right:5px;"></i>
                            <strong>${record.nome_clie}</strong>
                        </td>
                        
                        <td>${empresaHtml}</td>
                        
                        <td>${contatoHtml}</td>
                        
                        <td style="text-align: center;">
                            <label class="switch">
                                <input type="checkbox" class="project-toggle" data-id="${record.id_clie}" ${isChecked}>
                                <span class="slider"></span>
                            </label>
                            <div class="status-badge" style="color:${statusColor}">${statusLabel}</div>
                        </td>

                        <td class="actions" style="text-align:center;">
                            <button class="edit-btn btn-icon" data-id="${record.id_clie}"><i class="fas fa-pen"></i></button>
                            <button class="delete-btn btn-icon" data-id="${record.id_clie}"><i class="fas fa-trash"></i></button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px;">Nenhum registro encontrado.</td></tr>`;
            }
        } catch (error) {
            console.error(error);
            tableBody.innerHTML = `<tr><td colspan="6" style="color:red; text-align:center">Erro de conexão.</td></tr>`;
        }
    }

    // 2. FORMULÁRIO (SALVAR COM EMPRESA)
    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            // Mapeamento dos campos (IMPORTANTE: Mapear 'empresa_clie')
            const data = {
                EMPRESA_CLIE: form.empresa_clie.value, // NOVO CAMPO
                DOCU_CLIE: form.docu_clie.value,
                NOME_CLIE: form.nome_clie.value, // Representante
                MAIL_CLIE: form.mail_clie.value,
                FONE_CLIE: form.fone_clie.value,
                ADRE_CLIE: form.adre_clie.value,
                ZIPN_CLIE: form.zipn_clie.value,
                CLIMA_ORGANIZACIONAL: form.clima_organizacional ? form.clima_organizacional.value : ''
            };

            if (!data.NOME_CLIE || !data.DOCU_CLIE || !data.MAIL_CLIE) {
                alert("Preencha os campos obrigatórios (*)");
                return;
            }

            let result;
            try {
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_clie', currentRecordIdForEdit, data);
                    if (result) alert('Atualizado com sucesso!');
                } else {
                    result = await window.api.createRecord('ctdi_clie', data);
                    if (result && result.id) alert('Cadastro criado com sucesso!');
                }
                clearForm();
                loadClientes(searchInput.value);
            } catch (err) {
                alert("Erro ao salvar: " + err);
            }
        });
    }

    // 3. CARREGAR PARA EDIÇÃO
    async function loadRecordIntoForm(recordId) {
        const record = await window.api.fetchRecordById('ctdi_clie', recordId);
        if (record) {
            // Popula os campos
            form.empresa_clie.value = record.empresa_clie || ''; // NOVO
            form.docu_clie.value = record.docu_clie;
            form.nome_clie.value = record.nome_clie;
            form.mail_clie.value = record.mail_clie;
            form.fone_clie.value = record.fone_clie || '';
            form.adre_clie.value = record.adre_clie || '';
            form.zipn_clie.value = record.zipn_clie || '';

            if (form.clima_organizacional) {
                form.clima_organizacional.value = record.clima_organizacional || '';
            }

            currentRecordIdForEdit = recordId;
            saveOrAddButton.innerHTML = '<i class="fas fa-sync"></i> Atualizar Dados';
            saveOrAddButton.style.background = '#f39c12';

            // Rola a página para o formulário
            form.scrollIntoView({ behavior: 'smooth' });
        }
    }

    function clearForm() {
        form.reset();
        currentRecordIdForEdit = null;
        saveOrAddButton.innerHTML = '<i class="fas fa-check"></i> Salvar Cadastro';
        saveOrAddButton.style.background = '#27ae60';
    }

    // Listeners do Toggle e Botões (Mantidos igual ao anterior)
    tableBody.addEventListener('change', async (event) => { /* ... código do toggle já existente ... */
        if (event.target.classList.contains('project-toggle')) {
             // ... copie a lógica do toggle que te passei antes ...
             // Se precisar eu reposto, mas é a mesma lógica de fetch('/api/admin/toggle-project')
             const checkbox = event.target;
             const recordId = checkbox.dataset.id;
             const acao = checkbox.checked ? 'ativar' : 'desativar';
             const badge = checkbox.parentElement.nextElementSibling;
             badge.innerText = '...';
             try {
                const response = await fetch('/api/admin/toggle-project', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id_clie: recordId, acao: acao })
                });
                const result = await response.json();
                if (result.success) {
                    badge.innerText = checkbox.checked ? 'ATIVO' : 'OFF';
                    badge.style.color = checkbox.checked ? '#27ae60' : '#ccc';
                } else {
                    alert('Erro: ' + result.message);
                    checkbox.checked = !checkbox.checked;
                }
             } catch(e) { checkbox.checked = !checkbox.checked; }
        }
    });

    tableBody.addEventListener('click', async (event) => {
        // Logica dos botões Editar e Excluir
        const btn = event.target.closest('button');
        if (!btn) return;

        const recordId = btn.dataset.id;
        if (btn.classList.contains('delete-btn')) {
            if(confirm('Excluir este cadastro?')) {
                await window.api.deleteRecord('ctdi_clie', recordId);
                loadClientes(searchInput.value);
            }
        } else if (btn.classList.contains('edit-btn')) {
            loadRecordIntoForm(recordId);
        }
    });

    if (searchBtn) searchBtn.addEventListener('click', () => loadClientes(searchInput.value));

    // Inicia
    loadClientes();
}

    // --- Lógica para a página de Dimensões ---
    if (document.getElementById('dimensoes-page')) {
        const form = document.querySelector('#dimensoes-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#dimensoes-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');

        let currentRecordIdForEdit = null;

        async function loadDimensoes(query = '') {
            const records = await window.api.fetchRecords('leaf_dime', query);
            tableBody.innerHTML = '';
            if (records && records.length > 0) {
                records.forEach(dime => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${dime.id_dime}</td>
                        <td>${dime.name_dime}</td>
                        <td>${dime.desc_dime || ''}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${dime.id_dime}">Editar</button>
                            <button class="delete-btn" data-id="${dime.id_dime}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="4">Nenhuma dimensão encontrada.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('leaf_dime', recordId);
            if (record) {
                form.name_dime.value = record.name_dime;
                form.desc_dime.value = record.desc_dime || '';
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
            } else {
                alert('Não foi possível carregar a Dimensão para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_DIME: form.name_dime.value,
                    DESC_DIME: form.desc_dime.value,
                };
                if (!data.NAME_DIME) {
                    alert("Por favor, preencha o Nome da Dimensão.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('leaf_dime', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Dimensão (ID: ${currentRecordIdForEdit}) atualizada com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('leaf_dime', data);
                    if (result && result.id) {
                        alert(`Dimensão "${data.NAME_DIME}" criada com sucesso. ID: ${result.id}`);
                    }
                }
                clearForm();
                loadDimensoes(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadDimensoes(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('leaf_dime', recordId);
                    if (result) {
                        alert('Dimensão deletada com sucesso!');
                        loadDimensoes(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        loadDimensoes();
    }

    // --- Lógica para a página de Fases ---
    if (document.getElementById('fases-page')) {
        const form = document.querySelector('#fases-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#fases-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');

        let currentRecordIdForEdit = null;

        async function loadFases(query = '') {
            const fases = await window.api.fetchRecords('ctdi_phase', query);
            tableBody.innerHTML = '';
            if (fases && fases.length > 0) {
                fases.forEach(fase => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${fase.id_phase}</td>
                        <td>${fase.name_phase}</td>
                        <td>${fase.desc_phase || ''}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${fase.id_phase}">Editar</button>
                            <button class="delete-btn" data-id="${fase.id_phase}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="4">Nenhuma fase encontrada.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('ctdi_phase', recordId);
            if (record) {
                form.name_phase.value = record.name_phase;
                form.desc_phase.value = record.desc_phase || '';
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
            } else {
                alert('Não foi possível carregar a Fase para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_PHASE: form.name_phase.value,
                    DESC_PHASE: form.desc_phase.value,
                };
                if (!data.NAME_PHASE) {
                    alert("Por favor, preencha o Nome da Fase.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_phase', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Fase (ID: ${currentRecordIdForEdit}) atualizada com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_phase', data);
                    if (result && result.id) {
                        alert(`Fase "${data.NAME_PHASE}" criada com sucesso. ID: ${result.id}`);
                    }
                }
                clearForm();
                loadFases(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadFases(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('ctdi_phase', recordId);
                    if (result) {
                        alert('Fase deletada com sucesso!');
                        loadFases(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        loadFases();
    }

    // --- Lógica para a página de Blocos ---
    if (document.getElementById('blocos-page')) {
        // VARIÁVEL phaseSelect REMOVIDA
        const dimeSelect = document.getElementById('id_dime');
        const domaSelect = document.getElementById('id_doma');
        const form = document.querySelector('#blocos-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#blocos-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');

        let currentRecordIdForEdit = null;

        async function loadAllDropdowns() {
            // População de Fases (ctdi_phase) REMOVIDA
            if (dimeSelect) await populateSelect(dimeSelect, 'leaf_dime', 'id_dime', 'name_dime');
            if (domaSelect) await populateSelect(domaSelect, 'leaf_doma', 'id_doma', 'name_doma');
        }

        async function loadBlocos(query = '') {
            const blocos = await window.api.fetchRecords('leaf_bloc', query);
            tableBody.innerHTML = '';
            if (blocos && blocos.length > 0) {
                blocos.forEach(bloco => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${bloco.id_bloc}</td>
                        <td>${bloco.name_bloc}</td>
                        <td>${bloco.desc_bloc || ''}</td>
                        <td>${bloco.name_dime_text || bloco.id_dime}</td>
                        <td>${bloco.name_doma_text || bloco.id_doma}</td>
                        <td class="actions">
                            <button class="btn green-btn view-btn" data-id="${bloco.id_bloc}">Editar</button>
                            <button class="btn red-btn view-btn" data-id="${bloco.id_bloc}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                // colspan alterado para 6
                tableBody.innerHTML = `<tr><td colspan="6">Nenhum bloco encontrado.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            // É importante manter a verificação aqui para evitar o TypeError
            if (clearFormButton) clearFormButton.style.display = 'none';
            loadAllDropdowns();
        }

        async function loadRecordIntoForm(recordId) {
            await loadAllDropdowns();
            const record = await window.api.fetchRecordById('leaf_bloc', recordId);
            if (record) {
                form.name_bloc.value = record.name_bloc;
                form.desc_bloc.value = record.desc_bloc || '';
                // CAMPO id_phase REMOVIDO AQUI
                form.id_dime.value = record.id_dime;
                form.id_doma.value = record.id_doma;
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                if (clearFormButton) clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o Bloco para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_BLOC: form.name_bloc.value,
                    DESC_BLOC: form.desc_bloc.value,
                    // ID_PHASE REMOVIDO
                    ID_DIME: parseInt(form.id_dime.value),
                    ID_DOMA: parseInt(form.id_doma.value),
                };
                // Checagem ID_PHASE REMOVIDA
                if (!data.NAME_BLOC || isNaN(data.ID_DIME) || data.ID_DIME === 0 || isNaN(data.ID_DOMA) || data.ID_DOMA === 0) {
                    alert("Por favor, preencha o nome do Bloco e selecione todos os campos obrigatórios.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('leaf_bloc', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Bloco (ID: ${currentRecordIdForEdit}) atualizado com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('leaf_bloc', data);
                    if (result && result.id) {
                        alert(`Bloco criado com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadBlocos(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadBlocos(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('leaf_bloc', recordId);
                    if (result) {
                        alert('Bloco deletado com sucesso!');
                        loadBlocos(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadAllDropdowns();
        loadBlocos();
    }

// --- Lógica para a página de Questões ---
if (document.getElementById('questoes-page')) {
    const form = document.querySelector('#form-ques');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const tableBody = document.querySelector('#questoes-table tbody');
    const clearFormButton = document.getElementById('clearFormButton');
    const dimeSelect = document.getElementById('id_dime_select');
    const domaSelect = document.getElementById('id_doma_select');

    let currentRecordIdForEdit = null;

    async function loadAllDropdowns() {
        if (dimeSelect) await populateSelect(dimeSelect, 'leaf_dime', 'id_dime', 'name_dime');
        if (domaSelect) await populateSelect(domaSelect, 'leaf_doma', 'id_doma', 'name_doma');
    }

    async function loadQuestoes(query = '') {
        try {
            const response = await fetch(`${window.location.origin}/api/ctdi_quest${query ? '?q=' + query : ''}`);
            const questoes = await response.json();
            tableBody.innerHTML = '';
            if (questoes && questoes.length > 0) {
                questoes.forEach(questao => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${questao.id_ques}</td>
                        <td>${questao.desc_ques || ''}</td>
                        <td>${questao.name_dime_text || questao.id_dime}</td>
                        <td>${questao.name_doma_text || questao.id_doma}</td>
                        <td class="actions">
                            <button class="btn green-btn edit-btn" data-id="${questao.id_ques}">Editar</button>
                            <button class="btn red-btn delete-btn" data-id="${questao.id_ques}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="5">Nenhuma questão encontrada.</td></tr>`;
            }
        } catch (e) { console.error("Erro ao carregar questões:", e); }
    }

    function clearForm() {
        if (form) form.reset();
        currentRecordIdForEdit = null;
        if(document.getElementById('id_ques')) document.getElementById('id_ques').value = '';
        document.querySelectorAll('input[name="target_item"]').forEach(cb => cb.checked = false);
        for (let i = 0; i <= 5; i++) {
            if (document.getElementById(`label_${i}`)) document.getElementById(`label_${i}`).value = '';
            if (document.getElementById(`desc_${i}`)) document.getElementById(`desc_${i}`).value = '';
        }
        loadAllDropdowns();
    }

    async function loadRecordIntoForm(recordId) {
        try {
            const response = await fetch(`${window.location.origin}/api/ctdi_quest/${recordId}`);
            if (!response.ok) throw new Error("Erro 404 ao carregar registro");
            const record = await response.json();

            if (record) {
                document.getElementById('id_ques').value = record.id_ques;
                document.getElementById('desc_ques').value = record.desc_ques || '';
                document.getElementById('id_dime_select').value = record.id_dime;
                document.getElementById('id_doma_select').value = record.id_doma;
                document.getElementById('presurvey_ques').checked = record.presurvey_ques;
                document.getElementById('quali_ques_def').value = record.quali_ques || '';
                document.getElementById('permite_aberta').checked = !!record.quali_ques;
                document.getElementById('insight_chave').value = record.insight_chave || '';

                // Novos campos
                if(document.getElementById('prefu_ques')) document.getElementById('prefu_ques').value = record.prefu_ques || 'P';
                if(document.getElementById('setor_ques')) document.getElementById('setor_ques').value = record.setor_ques || 'GERAL';

                const targets = record.target_context ? record.target_context.split(';') : [];
                document.querySelectorAll('input[name="target_item"]').forEach(cb => {
                    cb.checked = targets.includes(cb.value);
                });

                if (record.rubricas) {
                    record.rubricas.forEach(rb => {
                        if (document.getElementById(`label_${rb.grad_rubr}`))
                            document.getElementById(`label_${rb.grad_rubr}`).value = rb.label_rubr;
                        if (document.getElementById(`desc_${rb.grad_rubr}`))
                            document.getElementById(`desc_${rb.grad_rubr}`).value = rb.desc_rubr;
                    });
                }
                currentRecordIdForEdit = recordId;
                if (typeof abrirModal === 'function') abrirModal(true);
            }
        } catch (e) { alert("Erro ao carregar: " + e.message); }
    }

    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            try {
                const rubricas = [];
                for (let i = 0; i <= 5; i++) {
                    const lb = document.getElementById(`label_${i}`)?.value || '';
                    const ds = document.getElementById(`desc_${i}`)?.value || '';
                    if (lb.trim() || ds.trim()) {
                        rubricas.push({ grad_rubr: i, label_rubr: lb, desc_rubr: ds });
                    }
                }

                const targets = Array.from(document.querySelectorAll('input[name="target_item"]:checked'))
                                     .map(cb => cb.value)
                                     .join(';');

                // Força a sincronia do ID caso a variável global tenha se perdido
                const idFromInput = document.getElementById('id_ques')?.value;
                const finalId = currentRecordIdForEdit || idFromInput;

                const data = {
                    desc_ques: document.getElementById('desc_ques').value,
                    id_dime: parseInt(document.getElementById('id_dime_select').value),
                    id_doma: parseInt(document.getElementById('id_doma_select').value),
                    presurvey_ques: document.getElementById('presurvey_ques').checked,
                    quali_ques: document.getElementById('quali_ques_def').value,
                    insight_chave: document.getElementById('insight_chave').value,
                    target_context: targets,
                    rubricas: rubricas,
                    prefu_ques: document.getElementById('prefu_ques')?.value || 'P',
                    setor_ques: document.getElementById('setor_ques')?.value || 'GERAL'
                };

                console.log("Enviando dados para o servidor:", data);

                const url = finalId ? `/api/ctdi_quest/${finalId}` : `/api/ctdi_quest`;
                const method = finalId ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                if (response.ok) {
                    alert("Configuração MASTER salva com sucesso!");
                    clearForm();
                    if (typeof fecharModal === 'function') fecharModal();
                    loadQuestoes();
                } else {
                    const err = await response.json();
                    alert("Erro no servidor: " + (err.error || "Falha desconhecida"));
                }
            } catch (error) {
                console.error("Erro no processamento do formulário:", error);
                alert("Erro local ao preparar os dados. Verifique o console.");
            }
        });
    }

    if (tableBody) {
        tableBody.addEventListener('click', async (event) => {
            const recordId = event.target.dataset.id;
            if (event.target.classList.contains('edit-btn')) {
                await loadRecordIntoForm(recordId);
            } else if (event.target.classList.contains('delete-btn')) {
                if (confirm("Deseja deletar esta questão MASTER?")) {
                    const response = await fetch(`${window.location.origin}/api/ctdi_quest/${recordId}`, { method: 'DELETE' });
                    if (response.ok) loadQuestoes();
                }
            }
        });
    }

    loadAllDropdowns();
    loadQuestoes();
}

    // --- Lógica para a página de Sprints ---
    if (document.getElementById('sprints-page')) {
        const form = document.querySelector('#sprints-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#sprints-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');
        const blocSelect = document.getElementById('id_bloc');

        let currentRecordIdForEdit = null;

        async function loadAllDropdowns() {
            if (blocSelect) await populateSelect(blocSelect, 'leaf_bloc', 'id_bloc', 'name_bloc');
        }

        async function loadSprints(query = '') {
            const sprints = await window.api.fetchRecords('ctdi_sprn', query);
            tableBody.innerHTML = '';
            if (sprints && sprints.length > 0) {
                sprints.forEach(sprint => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${sprint.id_sprn}</td>
                        <td>${sprint.name_bloc_text || sprint.id_bloc}</td>
                        <td>${sprint.name_sprn}</td>
                        <td>${sprint.desc_sprn || ''}</td>
                        <td>${sprint.ordr_sprn}</td>
                        <td>${formatDateForInput(sprint.dtini_sprn)}</td>
                        <td>${formatDateForInput(sprint.dtend_sprn)}</td>
                        <td>${sprint.stat_sprn}</td>
                        <td>${sprint.week_sprn}</td>
                        <td>${sprint.targv_sprn}</td>
                        <td>${sprint.realv_sprn}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${sprint.id_sprn}">Editar</button>
                            <button class="delete-btn" data-id="${sprint.id_sprn}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="12">Nenhuma sprint encontrada.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            clearFormButton.style.display = 'none';
            loadAllDropdowns();
        }

        async function loadRecordIntoForm(recordId) {
            await loadAllDropdowns();
            const record = await window.api.fetchRecordById('ctdi_sprn', recordId);
            if (record) {
                form.id_bloc.value = record.id_bloc;
                form.name_sprn.value = record.name_sprn;
                form.desc_sprn.value = record.desc_sprn || '';
                form.ordr_sprn.value = record.ordr_sprn;
                form.dtini_sprn.value = formatDateForInput(record.dtini_sprn);
                form.dtend_sprn.value = formatDateForInput(record.dtend_sprn);
                form.stat_sprn.value = record.stat_sprn;
                form.week_sprn.value = record.week_sprn;
                form.targv_sprn.value = record.targv_sprn;
                form.realv_sprn.value = record.realv_sprn;
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar a Sprint para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_SPRN: form.name_sprn.value,
                    DESC_SPRN: form.desc_sprn.value,
                    ORDR_SPRN: parseInt(form.ordr_sprn.value),
                    DTINI_SPRN: form.dtini_sprn.value,
                    DTEND_SPRN: form.dtend_sprn.value,
                    STAT_SPRN: form.stat_sprn.value,
                    WEEK_SPRN: parseInt(form.week_sprn.value),
                    TARGV_SPRN: parseInt(form.targv_sprn.value),
                    REALV_SPRN: parseInt(form.realv_sprn.value),
                    ID_BLOC: parseInt(form.id_bloc.value),
                };
                if (!data.NAME_SPRN || !data.DTINI_SPRN || !data.DTEND_SPRN || !data.STAT_SPRN ||
                    isNaN(data.ID_BLOC) || data.ID_BLOC === 0 ||
                    isNaN(data.ORDR_SPRN) || isNaN(data.WEEK_SPRN) ||
                    isNaN(data.TARGV_SPRN) || isNaN(data.REALV_SPRN)) {
                    alert("Por favor, preencha todos os campos obrigatórios e numéricos com valores válidos.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_sprn', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Sprint (ID: ${currentRecordIdForEdit}) atualizada com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_sprn', data);
                    if (result && result.id) {
                        alert(`Sprint criada com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadSprints(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadSprints(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('ctdi_sprn', recordId);
                    if (result) {
                        alert('Sprint deletada com sucesso!');
                        loadSprints(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadAllDropdowns();
        loadSprints();
    }

    // --- Lógica para a página de Rodadas ---
    if (document.getElementById('rodadas-page')) {
        const form = document.querySelector('#rodadas-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#rodadas-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');
        const dimeSelect = document.getElementById('id_dime');

        let currentRecordIdForEdit = null;

        async function loadAllDropdowns() {
            if (dimeSelect) await populateSelect(dimeSelect, 'leaf_dime', 'id_dime', 'name_dime');
        }

        async function loadRodadas(query = '') {
            const rodadas = await window.api.fetchRecords('ctdi_roun', query);
            tableBody.innerHTML = '';
            if (rodadas && rodadas.length > 0) {
                rodadas.forEach(rodada => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${rodada.id_roun}</td>
                        <td>${rodada.name_dime_text || rodada.id_dime}</td>
                        <td>${rodada.name_roun}</td>
                        <td>${rodada.desc_roun || ''}</td>
                        <td>${rodada.ordr_roun}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${rodada.id_roun}">Editar</button>
                            <button class="delete-btn" data-id="${rodada.id_roun}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="6">Nenhuma rodada encontrada.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            clearFormButton.style.display = 'none';
            loadAllDropdowns();
        }

        async function loadRecordIntoForm(recordId) {
            await loadAllDropdowns();
            const record = await window.api.fetchRecordById('ctdi_roun', recordId);
            if (record) {
                form.id_dime.value = record.id_dime;
                form.name_roun.value = record.name_roun;
                form.desc_roun.value = record.desc_roun || '';
                form.ordr_roun.value = record.ordr_roun;
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar a Rodada para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    ID_DIME: parseInt(form.id_dime.value),
                    NAME_ROUN: form.name_roun.value,
                    DESC_ROUN: form.desc_roun.value,
                    ORDR_ROUN: parseInt(form.ordr_roun.value),
                };
                if (!data.NAME_ROUN || isNaN(data.ID_DIME) || data.ID_DIME === 0 || isNaN(data.ORDR_ROUN)) {
                    alert("Por favor, preencha todos os campos obrigatórios e numéricos com valores válidos.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_roun', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Rodada (ID: ${currentRecordIdForEdit}) atualizada com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_roun', data);
                    if (result && result.id) {
                        alert(`Rodada criada com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadRodadas(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadRodadas(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('ctdi_roun', recordId);
                    if (result) {
                        alert('Rodada deletada com sucesso!');
                        loadRodadas(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadAllDropdowns();
        loadRodadas();
    }

    // --- Lógica para a página de Questionários ---
    if (document.getElementById('surveys-page')) {
        const form = document.querySelector('#surveys-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#surveys-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');

        const matuSelect = document.getElementById('id_matu');
        const dimeSelect = document.getElementById('id_dime');
        const domaSelect = document.getElementById('id_doma');
        const quesSelect = document.getElementById('id_ques');

        let currentRecordIdForEdit = null;

        async function loadAllDropdowns() {
            if (matuSelect) await populateSelect(matuSelect, 'ctdi_matu', 'id_matu', 'nome_clie_text');
            if (dimeSelect) await populateSelect(dimeSelect, 'leaf_dime', 'id_dime', 'name_dime');
            if (domaSelect) await populateSelect(domaSelect, 'leaf_doma', 'id_doma', 'name_doma');
            if (quesSelect) await populateSelect(quesSelect, 'ctdi_quest', 'id_ques', 'desc_ques');
        }

        async function loadSurveys(query = '') {
            const surveys = await window.api.fetchRecords('ctdi_surv', query);
            tableBody.innerHTML = '';
            if (surveys && surveys.length > 0) {
                surveys.forEach(survey => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${survey.id_surv}</td>
                        <td>${survey.nome_clie_text_from_matu || survey.id_matu}</td>
                        <td>${survey.name_dime_text || survey.id_dime}</td>
                        <td>${survey.name_doma_text || survey.id_doma}</td>
                        <td>${survey.desc_ques_text || survey.id_ques}</td>
                        <td>${survey.grad_ques}</td>
                        <td class="actions">
                            <button class="btn green-btn edit-btn" data-id="${survey.id_surv}">Editar</button>
                            <button class="btn red-btn delete-btn" data-id="${survey.id_surv}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="7">Nenhum questionário encontrado.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            clearFormButton.style.display = 'none';
            loadAllDropdowns();
        }

        async function loadRecordIntoForm(recordId) {
            await loadAllDropdowns();
            const record = await window.api.fetchRecordById('ctdi_surv', recordId);
            if (record) {
                form.id_matu.value = record.id_matu;
                form.id_dime.value = record.id_dime;
                form.id_doma.value = record.id_doma;
                form.id_ques.value = record.id_ques;
                form.grad_ques.value = record.grad_ques;
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o Questionário para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    ID_MATU: parseInt(form.id_matu.value),
                    ID_DIME: parseInt(form.id_dime.value),
                    ID_DOMA: parseInt(form.id_doma.value),
                    ID_QUES: parseInt(form.id_ques.value),
                    GRAD_QUES: form.grad_ques.value
                };
                if (isNaN(data.ID_MATU) || data.ID_MATU === 0 || isNaN(data.ID_DIME) || data.ID_DIME === 0 || isNaN(data.ID_DOMA) || data.ID_DOMA === 0 || isNaN(data.ID_QUES) || data.ID_QUES === 0 || !data.GRAD_QUES.trim()) {
                    alert("Por favor, preencha todos os campos e selecione os itens obrigatórios.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_surv', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Questionário (ID: ${currentRecordIdForEdit}) atualizado com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_surv', data);
                    if (result && result.id) {
                        alert(`Questionário criado com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadSurveys(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadSurveys(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('ctdi_surv', recordId);
                    if (result) {
                        alert('Questionário deletado com sucesso!');
                        loadSurveys(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadAllDropdowns();
        loadSurveys();
    }

    // --- Lógica para a página de Domínios ---
    if (document.getElementById('dominios-page')) {
        const form = document.querySelector('#dominios-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#dominios-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');

        let currentRecordIdForEdit = null;

        async function loadDominios(query = '') {
            const dominios = await window.api.fetchRecords('leaf_doma', query);
            tableBody.innerHTML = '';
            if (dominios && dominios.length > 0) {
                dominios.forEach(dominio => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${dominio.id_doma}</td>
                        <td>${dominio.name_doma}</td>
                        <td>${dominio.desc_doma || ''}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${dominio.id_doma}">Editar</button>
                            <button class="delete-btn" data-id="${dominio.id_doma}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="4">Nenhum domínio encontrado.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            clearFormButton.style.display = 'none';
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('leaf_doma', recordId);
            if (record) {
                form.name_doma.value = record.name_doma;
                form.desc_doma.value = record.desc_doma || '';
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o Domínio para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    name_doma: form.name_doma.value,
                    desc_doma: form.desc_doma.value
                };
                if (!data.name_doma.trim()) {
                    alert("Por favor, preencha o Nome do Domínio.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('leaf_doma', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Domínio (ID: ${currentRecordIdForEdit}) atualizado com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('leaf_doma', data);
                    if (result && result.id) {
                        alert(`Domínio criado com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadDominios(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadDominios(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('leaf_doma', recordId);
                    if (result) {
                        alert('Domínio deletado com sucesso!');
                        loadDominios(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadDominios();
    }

    // --- Lógica para a página de Entregáveis ---
    if (document.getElementById('entregaveis-page')) {
        const form = document.querySelector('#entregaveis-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#entregaveis-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');

        let currentRecordIdForEdit = null;

        async function loadEntregaveis(query = '') {
            const entregaveis = await window.api.fetchRecords('leaf_derv', query);
            tableBody.innerHTML = '';
            if (entregaveis && entregaveis.length > 0) {
                entregaveis.forEach(entregavel => {
                    const row = tableBody.insertRow();
                    row.innerHTML = `
                        <td>${entregavel.id_derv}</td>
                        <td>${entregavel.name_derv}</td>
                        <td>${entregavel.desc_derv || ''}</td>
                        <td>${entregavel.defi_derv || ''}</td>
                        <td>${entregavel.comp_derv || ''}</td>
                        <td>${entregavel.metr_derv || ''}</td>
                        <td class="actions">
                            <button class="edit-btn" data-id="${entregavel.id_derv}">Editar</button>
                            <button class="delete-btn" data-id="${entregavel.id_derv}">Deletar</button>
                        </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="7">Nenhum entregável encontrado.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            clearFormButton.style.display = 'none';
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('leaf_derv', recordId);
            if (record) {
                form.name_derv.value = record.name_derv;
                form.desc_derv.value = record.desc_derv || '';
                form.defi_derv.value = record.defi_derv || '';
                form.comp_derv.value = record.comp_derv || '';
                form.metr_derv.value = record.metr_derv || '';
                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o Entregável para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_DERV: form.name_derv.value,
                    DESC_DERV: form.desc_derv.value,
                    DEFI_DERV: form.defi_derv.value,
                    COMP_DERV: form.comp_derv.value,
                    METR_DERV: form.metr_derv.value
                };
                if (!data.NAME_DERV.trim()) {
                    alert("Por favor, preencha o Nome do Entregável.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('leaf_derv', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Entregável (ID: ${currentRecordIdForEdit}) atualizado com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('leaf_derv', data);
                    if (result && result.id) {
                        alert(`Entregável criado com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadEntregaveis(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadEntregaveis(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                if (event.target.classList.contains('delete-btn')) {
                    const recordId = event.target.dataset.id;
                    const result = await window.api.deleteRecord('leaf_derv', recordId);
                    if (result) {
                        alert('Entregável deletado com sucesso!');
                        loadEntregaveis(searchInput.value);
                    }
                } else if (event.target.classList.contains('edit-btn')) {
                    const recordId = event.target.dataset.id;
                    await loadRecordIntoForm(recordId);
                }
            });
        }
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadEntregaveis();
    }

    // --- Lógica para a página de Movimentos ---
    if (document.getElementById('movimentos-page')) {
        const form = document.querySelector('#movimentos-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#movimentos-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');

        let currentRecordIdForEdit = null;

        async function loadMovimentos(query = '') {
            const movimentos = await window.api.fetchRecords('ctdi_movi', query);
            tableBody.innerHTML = '';
            if (movimentos && movimentos.length > 0) {
                movimentos.forEach(movimento => {
                    const row = tableBody.insertRow();
                    // ATENÇÃO: Colspan ajustado para 7 colunas
                    row.innerHTML = `
                        <td>${movimento.id_movi}</td>
                        <td>${movimento.name_movi}</td>
                        <td>${movimento.desc_movi || ''}</td>
                        <td>${movimento.diag_movi || ''}</td>
                        <td>${movimento.crtr_movi || ''}</td>
                        <td>${movimento.intv_movi || ''}</td>
                        <td class="actions">
                            <button class="btn blue-btn edit-btn" data-id="${movimento.id_movi}">Editar</button>
                            <button class="btn red-btn delete-btn" data-id="${movimento.id_movi}">Deletar</button>
                       </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="7">Nenhum movimento encontrado.</td></tr>`;
            }
        }

        function clearForm() {
            form.reset();
            currentRecordIdForEdit = null;
            saveOrAddButton.textContent = 'Adicionar';
            if (clearFormButton) clearFormButton.style.display = 'none';
            loadMovimentos(searchInput.value);
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('ctdi_movi', recordId);
            if (record) {
                form.name_movi.value = record.name_movi;
                form.desc_movi.value = record.desc_movi || '';
                form.diag_movi.value = record.diag_movi || '';
                form.crtr_movi.value = record.crtr_movi || '';

                // CRÍTICO: intv_movi.value usa a string direta (que o database.py garante)
                form.intv_movi.value = record.intv_movi || '';

                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                if (clearFormButton) clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o Movimento para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    NAME_MOVI: form.name_movi.value,
                    DESC_MOVI: form.desc_movi.value,
                    DIAG_MOVI: form.diag_movi.value,
                    CRTR_MOVI: form.crtr_movi.value,
                    INTV_MOVI: form.intv_movi.value,
                };
                if (!data.NAME_MOVI.trim()) {
                    alert("Por favor, preencha o Nome do Movimento.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_movi', currentRecordIdForEdit, data);
                    if (result) {
                        alert(`Movimento (ID: ${currentRecordIdForEdit}) atualizado com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_movi', data);
                    if (result && result.id) {
                        alert(`Movimento criado com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
            });
        }

        // Event listener para a tabela (Editar/Deletar)
        if (tableBody) {
            tableBody.addEventListener('click', async (event) => {
                const target = event.target;
                const recordId = target.dataset.id;

                if (!recordId) return;

                if (target.classList.contains('delete-btn')) {
                    const result = await window.api.deleteRecord('ctdi_movi', recordId);
                    if (result) {
                        alert('Movimento deletado com sucesso!');
                        loadMovimentos(searchInput.value);
                    }
                } else if (target.classList.contains('edit-btn')) {
                    // AQUI ESTÁ O TRATAMENTO PARA EDITAR
                    await loadRecordIntoForm(recordId);
                }
                // Não há mais um view-btn genérico, apenas a lógica de CRUD.
            });
        }

        // Event listener para o botão de busca (se existir)
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadMovimentos(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }

        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }

        loadMovimentos();
    }
    // --- Lógica para a página de Maturidades ---
    if (document.getElementById('maturidades-page')) {
        const form = document.querySelector('#maturidades-form');
        const searchInput = document.getElementById('search-input');
        const searchBtn = document.getElementById('search-btn');
        const tableBody = document.querySelector('#maturidades-table tbody');
        const saveOrAddButton = document.getElementById('saveOrAddButton');
        const clearFormButton = document.getElementById('clearFormButton');
        const clientSearchInput = document.getElementById('client-name-search');
        const searchResultsDiv = document.getElementById('search-results');
        const idClieInput = document.getElementById('id_clie');

        let currentRecordIdForEdit = null;

        if (clientSearchInput && searchResultsDiv) {
            clientSearchInput.addEventListener('input', async () => {
                const query = clientSearchInput.value.trim();
                searchResultsDiv.innerHTML = '';
                idClieInput.value = '';

                if (query.length < 3) {
                    return;
                }

                const clients = await window.api.fetchRecords('ctdi_clie', query);

                if (clients && clients.length > 0) {
                    clients.forEach(client => {
                        const resultItem = document.createElement('div');
                        resultItem.classList.add('search-result-item');
                        resultItem.textContent = client.nome_clie;
                        resultItem.dataset.id = client.id_clie;
                        resultItem.dataset.name = client.nome_clie;
                        searchResultsDiv.appendChild(resultItem);
                    });
                } else {
                    searchResultsDiv.innerHTML = '<div class="no-results">Nenhum cliente encontrado.</div>';
                }
            });

            searchResultsDiv.addEventListener('click', (event) => {
                const selectedItem = event.target.closest('.search-result-item');
                if (selectedItem) {
                    const selectedId = selectedItem.dataset.id;
                    const selectedName = selectedItem.dataset.name;
                    clientSearchInput.value = selectedName;
                    idClieInput.value = selectedId;
                    searchResultsDiv.innerHTML = '';

                    // --- CORREÇÃO CRÍTICA: INJETAR ZEROS AUTOMATICAMENTE ---
                    // Isso satisfaz o formulário e a validação, evitando que o usuário precise digitar.
                    // O backend já está configurado para salvar 0.00.
                    const form = document.querySelector('#maturidades-form');
                    form.pdom_matu.value = '0.00';
                    form.pdim_matu.value = '0.00';
                    form.pgen_matu.value = '0.00';
                    // -----------------------------------------------------
                }
            });
        }

        async function loadMaturidades(query = '') {
            const tableBody = document.querySelector('#maturidades-table tbody');
            if (!tableBody) return;

            const maturidades = await window.api.fetchRecords('ctdi_matu', query);
            tableBody.innerHTML = ''; // Limpa antes de popular

            // Função auxiliar para formatar o score, tratando nulos e strings
            const formatScore = (score) => {
                const num = parseFloat(score);
                return isNaN(num) ? '0.00' : num.toFixed(2);
            };

            if (maturidades && maturidades.length > 0) {
                maturidades.forEach(maturidade => {
                    // CRÍTICO: Não use insertRow() ou innerHTML.innerHTML se já estiver usando insertRow()
                    const row = tableBody.insertRow(); // Cria uma nova linha (<tr>)

                    const generalScore = maturidade.pgen_matu;

                    // Insere o conteúdo dentro da nova linha <tr> criada
                    row.innerHTML = `
                        <td>${maturidade.id_matu}</td>
                        <td>${maturidade.nome_clie_text || maturidade.id_clie}</td>
                        
                        <td>${formatScore(generalScore)}</td> 
                        <td>${formatScore(generalScore)}</td>
                        <td>${formatScore(generalScore)}</td>
                        
                        <td class="actions">
                            <button class="btn blue-btn view-btn" data-id="${maturidade.id_matu}">Avaliação</button>
                            <button class="btn green-btn view-btn-dia" data-id="${maturidade.id_matu}">Diagnóstico</button>
                         </td>
                    `;
                });
            } else {
                tableBody.innerHTML = `<tr><td colspan="6">Nenhuma maturidade encontrada.</td></tr>`;
            }
        }

        function clearForm() {
            const form = document.querySelector('#maturidades-form'); // Adiciona a busca do form aqui
            const saveOrAddButton = document.getElementById('saveOrAddButton');
            const clearFormButton = document.getElementById('clearFormButton'); // Adiciona a busca do botão aqui
            const searchResultsDiv = document.getElementById('search-results');

            form.reset();
            currentRecordIdForEdit = null; // Assume que esta variável global está definida
            saveOrAddButton.textContent = 'Adicionar Maturidade';

            // CORREÇÃO: Verifica se o botão existe antes de manipular o estilo
            if (clearFormButton) {
                clearFormButton.style.display = 'none';
            }

            if (searchResultsDiv) searchResultsDiv.innerHTML = '';
            // Adiciona o loadMaturidades se a função existir no escopo global
            if (typeof loadMaturidades === 'function') loadMaturidades(document.getElementById('search-input').value);
        }

        async function loadRecordIntoForm(recordId) {
            const record = await window.api.fetchRecordById('ctdi_matu', recordId);
            if (record) {
                if (clientSearchInput) clientSearchInput.value = record.nome_clie_text || '';
                if (idClieInput) idClieInput.value = record.id_clie;
                form.pdom_matu.value = record.pdom_matu;
                form.pdim_matu.value = record.pdim_matu;
                form.pgen_matu.value = record.pgen_matu;

                currentRecordIdForEdit = recordId;
                saveOrAddButton.textContent = 'Salvar Alterações';
                clearFormButton.style.display = 'inline-block';
            } else {
                alert('Não foi possível carregar o registro para edição.');
            }
        }

        if (form) {
            form.addEventListener('submit', async (event) => {
                event.preventDefault();
                const data = {
                    ID_CLIE: parseInt(idClieInput.value),
                };
                if (isNaN(data.ID_CLIE)) {
                    alert("Por favor, selecione um cliente válido.");
                    return;
                }
                let result;
                if (currentRecordIdForEdit) {
                    result = await window.api.updateRecord('ctdi_matu', currentRecordIdForEdit, data);
                    if(result) {
                        alert(`Maturidade (ID: ${currentRecordIdForEdit}) atualizada com sucesso!`);
                    }
                } else {
                    result = await window.api.createRecord('ctdi_matu', data);
                    if (result && result.id) {
                        alert(`Maturidade criada com sucesso! ID: ${result.id}`);
                    }
                }
                clearForm();
                loadMaturidades(searchInput.value);
            });
        }
        if (searchBtn) {
            searchBtn.addEventListener('click', () => {
                const query = searchInput.value;
                if (query.length >= 3 || query.length === 0) {
                    loadMaturidades(query);
                } else {
                    alert("A busca deve conter pelo menos 3 caracteres alfanuméricos ou ser vazia para listar todos.");
                }
            });
        }
if (tableBody) {
    tableBody.addEventListener('click', async (event) => {
        const target = event.target;

        // Verifica se o elemento clicado é um botão
        if (target.tagName === 'BUTTON') {
            const recordId = target.dataset.id;

            if (target.classList.contains('delete-btn')) {
                const result = await window.api.deleteRecord('ctdi_matu', recordId);
                if (result) {
                    alert('Maturidade deletada com sucesso!');
                    loadMaturidades(searchInput.value);
                }
            } else if (target.classList.contains('edit-btn')) {
                await loadRecordIntoForm(recordId);
            } else if (target.classList.contains('view-btn')) {
                // CORREÇÃO: Lógica para o novo botão 'Ver Avaliação'
                window.location.href = `/avaliacoes/${recordId}`;
            }
        }
    });
}
        if (clearFormButton) {
            clearFormButton.addEventListener('click', clearForm);
        }
        loadMaturidades();
    }

// --- Lógica para a página de Avaliação (Questionário do Cliente) ---
if (document.getElementById('evaluation-page')) {
    const evaluationForm = document.getElementById('evaluationForm');

    if (evaluationForm) {
        // 1. Definições de Variáveis de Escopo
        const statusPresent = document.getElementById('statusPresent');
        const statusFuture = document.getElementById('statusFuture');
        const TYPE_MATU_PRESENT = 'P';
        const TYPE_MATU_FUTURE = 'F';
        const maturityId = evaluationForm.dataset.maturityId;
        const futureSubmitBtn = evaluationForm.querySelector('.future-submit-btn');
        const statusFutureEl = document.getElementById('statusFuture');

        const steps = document.querySelectorAll('.wizard-step');
        const indicators = document.querySelectorAll('.step-indicator');
        let currentStep = 0;
        const assessmentSavedIds = new Set();

        // --- FUNÇÕES DE UTILIDADE ---

        const ASSESSMENT_META = {
            mini: { totalMin: 3, totalQuestions: 28, label: 'Diagnóstico inicial', icon: 'fa-bolt' },
            full: { totalMin: 28, totalQuestions: 162, label: 'Assessment completo', icon: 'fa-clipboard-list' }
        };

        function getPresurveyProgress() {
            const items = [...document.querySelectorAll('#step-0 .question-item')];
            const configuredTotal = parseInt(evaluationForm.dataset.miniTotal, 10);
            const total = configuredTotal > 0 ? configuredTotal : items.length;
            const answered = items.filter(isQuestionAnswered).length;
            return {
                total,
                answered: Math.min(answered, total),
                complete: total > 0 && answered >= total,
            };
        }

        function getAssessmentSessionKey(suffix) {
            return `assessment_${suffix}_${maturityId}`;
        }

        function ensureAssessmentSessionStart() {
            const key = getAssessmentSessionKey('started');
            let start = sessionStorage.getItem(key);
            if (!start) {
                start = String(Date.now());
                sessionStorage.setItem(key, start);
            }
            return parseInt(start, 10);
        }

        function recordAnswerStreak() {
            const streakKey = getAssessmentSessionKey('streak');
            const lastKey = getAssessmentSessionKey('last_answer');
            const now = Date.now();
            const last = parseInt(sessionStorage.getItem(lastKey) || '0', 10);
            let streak = parseInt(sessionStorage.getItem(streakKey) || '0', 10);
            streak = last && (now - last) < 120000 ? streak + 1 : 1;
            sessionStorage.setItem(streakKey, String(streak));
            sessionStorage.setItem(lastKey, String(now));
            return streak;
        }

        function getAnswerStreak() {
            return parseInt(sessionStorage.getItem(getAssessmentSessionKey('streak')) || '0', 10);
        }

        function syncUnlockedMilestones(pct) {
            const key = getAssessmentSessionKey('milestones');
            const unlocked = JSON.parse(sessionStorage.getItem(key) || '[]');
            [25, 50, 75, 100].forEach(m => {
                if (pct >= m && !unlocked.includes(m)) unlocked.push(m);
            });
            sessionStorage.setItem(key, JSON.stringify(unlocked));
            return unlocked.sort((a, b) => a - b);
        }

        function getUnlockedMilestones() {
            return JSON.parse(sessionStorage.getItem(getAssessmentSessionKey('milestones')) || '[]');
        }

        function getAssessmentScopeItems(isRestricted) {
            if (isRestricted) {
                const step0 = document.getElementById('step-0');
                return step0 ? [...step0.querySelectorAll('.question-item')] : [];
            }
            // Assessment completo: 162 indicadores (exclui presurvey do mini, que fica só na aba 0)
            return [...document.querySelectorAll('#evaluationForm .question-item[data-presurvey="false"]')];
        }

        function isQuestionAnswered(item) {
            const qId = String(item.dataset.questionId);
            if (item.querySelector('input[type="radio"]:checked')) return true;
            return assessmentSavedIds.has(qId);
        }

        function bootstrapAssessmentSavedIds() {
            assessmentSavedIds.clear();
            const isRestricted = evaluationForm.getAttribute('data-restricted') === 'true';
            const scopeIds = new Set(
                getAssessmentScopeItems(isRestricted).map(item => String(item.dataset.questionId))
            );

            getAssessmentScopeItems(isRestricted).forEach(item => {
                if (item.querySelector('input[type="radio"]:checked')) {
                    assessmentSavedIds.add(String(item.dataset.questionId));
                }
            });

            const savedFromServer = (evaluationForm.dataset.savedIds || '')
                .split(',')
                .map(id => id.trim())
                .filter(Boolean);
            savedFromServer.forEach(id => {
                if (scopeIds.has(id)) assessmentSavedIds.add(id);
            });
        }

        function parseQuestionGrad(rawValue) {
            return window.parseQuestionGrad
                ? window.parseQuestionGrad(rawValue)
                : (rawValue === 'na' || rawValue == null || rawValue === '' ? null : Number(rawValue));
        }

        function restoreSurveyAnswerToDom(answer) {
            const qId = String(answer.id_ques);
            const items = document.querySelectorAll(`.question-item[data-question-id="${qId}"]`);
            if (!items.length) return;

            const hasGrad = answer.grad_ques !== null && answer.grad_ques !== undefined;
            const targetValue = hasGrad ? String(answer.grad_ques) : 'na';

            items.forEach(item => {
                let matched = false;
                item.querySelectorAll(`input[type="radio"][name="question-${qId}"]`).forEach(input => {
                    const inputVal = input.value;
                    const isMatch = targetValue === 'na'
                        ? inputVal === 'na'
                        : (inputVal !== 'na' && Number(inputVal) === Number(targetValue));
                    if (isMatch) {
                        input.checked = true;
                        matched = true;
                    }
                });
                if (matched || hasGrad || answer.grad_ques === 0) {
                    assessmentSavedIds.add(qId);
                }
                const ta = item.querySelector('.quali-textarea');
                if (ta && answer.quali_ques) ta.value = answer.quali_ques;
            });
        }

        function countAssessmentProgress(isRestricted) {
            const meta = isRestricted ? ASSESSMENT_META.mini : ASSESSMENT_META.full;
            const scopeItems = getAssessmentScopeItems(isRestricted);
            const configuredTotal = parseInt(
                isRestricted ? evaluationForm.dataset.miniTotal : evaluationForm.dataset.fullTotal,
                10
            );
            const total = configuredTotal > 0 ? configuredTotal : (scopeItems.length || meta.totalQuestions);
            const answered = scopeItems.filter(isQuestionAnswered).length;

            return { total, answered: Math.min(answered, total), scopeItems };
        }

        function formatAssessmentDuration(seconds) {
            const s = Math.max(0, Math.round(seconds));
            if (s < 60) return `~${Math.max(1, s)} seg restantes`;
            const min = Math.round(s / 60);
            return min === 1 ? '~1 min restante' : `~${min} min restantes`;
        }

        function getAssessmentPaceLabel(avgSecPerQ, targetSecPerQ, answered) {
            if (answered === 0) return 'Ritmo: aguardando 1ª resposta';
            if (answered === 1) return 'Ritmo: calculando…';
            const ratio = avgSecPerQ / targetSecPerQ;
            const perMin = (60 / avgSecPerQ).toFixed(1);
            if (ratio <= 0.85) return `Ritmo excelente · ${perMin} quest/min`;
            if (ratio <= 1.15) return `Ritmo ideal · ${perMin} quest/min`;
            if (ratio <= 1.5) return `Ritmo moderado · ${perMin} quest/min`;
            return `Sem pressa · ${perMin} quest/min — qualidade importa`;
        }

        function getAssessmentStatusLabel(pct, answered) {
            if (answered === 0) return 'Não iniciado';
            if (pct >= 100) return 'Completo';
            if (pct >= 75) return 'Reta final';
            if (pct >= 50) return 'No fluxo';
            if (pct >= 25) return 'Em andamento';
            return 'Aquecendo';
        }

        const MILESTONE_BADGES = {
            25: { icon: 'fa-star', label: '25% conquistado' },
            50: { icon: 'fa-medal', label: 'Metade do caminho' },
            75: { icon: 'fa-gem', label: '75% desbloqueado' },
            100: { icon: 'fa-crown', label: '100% completo' }
        };

        function buildGamificationBadges(state) {
            const badges = [];
            const { pct, answered, streak, ratio, isRestricted, unlocked } = state;

            if (answered === 0) {
                badges.push({ icon: 'fa-hourglass-start', label: 'Aguardando início', variant: 'muted' });
                return badges;
            }

            if (answered >= 1) {
                badges.push({ icon: 'fa-play-circle', label: '1ª resposta', variant: 'violet' });
            }

            if (ratio <= 0.85 && answered >= 3) {
                badges.push({ icon: 'fa-trophy', label: '1º no tempo', variant: 'gold' });
            } else if (ratio <= 1.15 && answered >= 3) {
                badges.push({ icon: 'fa-bolt', label: 'Ritmo top', variant: 'gold' });
            }

            if (streak >= 3) {
                badges.push({ icon: 'fa-fire', label: `${streak} seguidas`, variant: 'fire' });
            }

            unlocked.forEach(m => {
                const def = MILESTONE_BADGES[m];
                if (def) badges.push({ icon: def.icon, label: def.label, variant: 'green' });
            });

            if (!isRestricted && answered >= 50) {
                badges.push({ icon: 'fa-shield-alt', label: 'Maratonista', variant: 'violet' });
            }
            if (!isRestricted && answered >= 100) {
                badges.push({ icon: 'fa-rocket', label: 'Centurião', variant: 'gold' });
            }
            if (isRestricted && pct >= 50) {
                badges.push({ icon: 'fa-magic', label: 'Quase no relatório', variant: 'gold' });
            }

            return badges.slice(0, 6);
        }

        function getGamificationCallout(state) {
            const { pct, answered, streak, ratio, isRestricted, total, remainingQ, newlyUnlocked } = state;

            if (newlyUnlocked) {
                const def = MILESTONE_BADGES[newlyUnlocked];
                return `Badge desbloqueado: ${def ? def.label : newlyUnlocked + '%'}! Continue — você está voando.`;
            }

            if (answered === 0) {
                return isRestricted
                    ? `${total} questões na 1ª aba. Responda a 1ª e desbloqueie seu primeiro badge!`
                    : '162 questões pela frente — cada resposta aproxima seu diagnóstico completo. Vamos!';
            }

            if (ratio <= 0.85 && answered >= 3) {
                return 'Você está em 1º lugar no tempo de resposta — continue assim!';
            }

            if (streak >= 7) {
                return `${streak} respostas seguidas sem pausa! Foco de campeão — mantenha o ritmo.`;
            }
            if (streak >= 4) {
                return 'Sequência impressionante! Cada resposta fortalece seu relatório personalizado.';
            }

            if (pct >= 100) {
                return 'Parabéns! Todas as questões respondidas. Revise e finalize para gerar seu diagnóstico.';
            }

            if (pct >= 75) {
                return isRestricted
                    ? `Faltam ${remainingQ} questões para seu diagnóstico preliminar. A reta final é sua!`
                    : `Reta final: ${remainingQ} de ${total} questões. Você está entre os mais dedicados — siga!`;
            }

            if (pct >= 50) {
                return isRestricted
                    ? 'Metade concluída! Seu relatório preliminar está cada vez mais próximo.'
                    : 'Metade das 162 questões! Momentum excelente — a IA já tem muito contexto sobre você.';
            }

            if (pct >= 25) {
                return 'Ótimo começo! Você superou o primeiro marco — continue desbloqueando badges.';
            }

            if (answered >= 5 && ratio <= 1.15) {
                return 'Ritmo consistente. Profissionais que mantêm esse pace concluem 40% mais rápido.';
            }

            return isRestricted
                ? `${answered} de ${total} respondidas. Mais ${remainingQ} e seu diagnóstico preliminar estará pronto!`
                : `${answered} de 162 respondidas. Persistência aqui = diagnóstico muito mais preciso.`;
        }

        function renderGamificationBadges(badges) {
            const container = document.getElementById('assessment-gamify-badges');
            if (!container) return;
            container.innerHTML = badges.map(b =>
                `<span class="assessment-gamify-badge assessment-gamify-badge--${b.variant}"><i class="fas ${b.icon}"></i> ${b.label}</span>`
            ).join('');
        }

        async function assertAssessmentComplete() {
            const isRestricted = evaluationForm.getAttribute('data-restricted') === 'true';
            if (isRestricted) {
                const pre = getPresurveyProgress();
                if (!pre.complete) {
                    alert(
                        `Complete as ${pre.total - pre.answered} questão(ões) restantes da 1ª aba ` +
                        `(diagnóstico inicial) antes de gerar o relatório preliminar.`
                    );
                    return false;
                }
                return true;
            }
            try {
                const res = await fetch(
                    `/api/assessment/ia-master/coverage/${maturityId}?mini=false`
                );
                if (!res.ok) return true;
                const data = await res.json();
                if (data.coverage && !data.coverage.can_finalize) {
                    alert(
                        `Para garantir a qualidade do diagnóstico, ainda faltam ${data.coverage.missing_count} ` +
                        `indicador(es) de ${data.coverage.total}. Complete via IA Master ou modo detalhado.`
                    );
                    return false;
                }
            } catch (e) {
                console.warn('Verificação de cobertura indisponível:', e);
            }
            return true;
        }

        function syncEvaluationChromeOffset() {
            const page = document.getElementById('evaluation-page');
            if (!page) return;

            const content = page.closest('.content');
            const contentPadBottom = content ? parseFloat(getComputedStyle(content).paddingBottom) || 0 : 0;
            const pageTop = page.getBoundingClientRect().top;
            const available = Math.floor(window.innerHeight - pageTop - contentPadBottom);

            if (available > 200) {
                page.style.height = `${available}px`;
                page.style.maxHeight = `${available}px`;
            }
        }

        function syncAssessmentDockLayout() {
            syncEvaluationChromeOffset();

            const dock = document.getElementById('assessment-progress-dock');
            if (!dock || dock.offsetHeight <= 0) return;

            const header = document.querySelector('.main-header') || document.querySelector('header');
            const ctx = document.querySelector('.context-bar');
            const hasContext = ctx && getComputedStyle(ctx).display !== 'none';
            const headerH = header ? header.offsetHeight : 60;
            const ctxH = hasContext ? ctx.offsetHeight : 0;

            document.documentElement.style.setProperty(
                '--assessment-dock-offset',
                `${headerH + ctxH + dock.offsetHeight}px`
            );
        }

        function atualizarProgressoGeral(options = {}) {
            const form = document.getElementById('evaluationForm');
            if (!form) return;

            const isRestricted = form.getAttribute('data-restricted') === 'true';
            const meta = isRestricted ? ASSESSMENT_META.mini : ASSESSMENT_META.full;
            const { total, answered } = countAssessmentProgress(isRestricted);
            const pct = total > 0 ? Math.min(100, Math.round((answered / total) * 100)) : 0;

            const prevUnlocked = getUnlockedMilestones();
            const unlocked = syncUnlockedMilestones(pct);
            const newlyUnlocked = options.fromAnswer
                ? unlocked.find(m => !prevUnlocked.includes(m))
                : null;

            const startTime = ensureAssessmentSessionStart();
            const elapsedSec = (Date.now() - startTime) / 1000;
            const targetSecPerQ = total > 0 ? (meta.totalMin * 60) / total : 9;
            const avgSecPerQ = answered >= 2 ? elapsedSec / answered : targetSecPerQ;
            const ratio = answered >= 2 ? avgSecPerQ / targetSecPerQ : 1;
            const remainingQ = Math.max(0, total - answered);
            const remainingSec = answered >= 2
                ? remainingQ * avgSecPerQ
                : remainingQ * targetSecPerQ;
            const streak = getAnswerStreak();

            const gamifyState = {
                pct, answered, total, remainingQ, streak, ratio, isRestricted, unlocked, newlyUnlocked
            };

            const pctEl = document.getElementById('assessment-progress-pct');
            const countEl = document.getElementById('assessment-progress-count');
            const fillEl = document.getElementById('assessment-progress-fill');
            const timeEl = document.getElementById('assessment-progress-time');
            const paceEl = document.getElementById('assessment-progress-pace');
            const statusEl = document.getElementById('assessment-progress-status');
            const calloutEl = document.getElementById('assessment-gamify-callout-text');
            const modeEl = document.getElementById('assessment-progress-mode');

            if (pctEl) pctEl.textContent = `${pct}%`;
            if (countEl) {
                countEl.textContent = isRestricted
                    ? `${answered} de ${total} questões`
                    : `${answered} de 162 questões`;
            }
            if (fillEl) {
                fillEl.style.width = `${pct}%`;
                fillEl.classList.toggle('assessment-progress-dock__fill--mini', isRestricted);
            }
            if (timeEl) {
                timeEl.textContent = answered >= total && total > 0
                    ? 'Concluído'
                    : formatAssessmentDuration(remainingSec);
            }
            if (paceEl) paceEl.textContent = getAssessmentPaceLabel(avgSecPerQ, targetSecPerQ, answered);
            if (statusEl) {
                statusEl.textContent = getAssessmentStatusLabel(pct, answered);
                statusEl.classList.toggle('assessment-progress-dock__status--done', pct >= 100);
            }
            if (calloutEl) calloutEl.textContent = getGamificationCallout(gamifyState);
            if (modeEl) {
                modeEl.className = `assessment-progress-dock__badge${isRestricted ? ' assessment-progress-dock__badge--mini' : ''}`;
                modeEl.innerHTML = `<i class="fas ${meta.icon}"></i> ${meta.label}`;
            }

            renderGamificationBadges(buildGamificationBadges(gamifyState));

            const legacyBar = document.getElementById('progress-container');
            if (legacyBar) legacyBar.remove();

            syncAssessmentDockLayout();

            if (isRestricted) {
                document.dispatchEvent(new CustomEvent('assessment-presurvey-changed', {
                    detail: getPresurveyProgress(),
                }));
            }
        }

        function collectAnswers(prefuQues) {
            const answers = [];
            evaluationForm.querySelectorAll(`.question-item[data-prefu="${prefuQues}"]`).forEach(questionDiv => {
                const questionId = questionDiv.dataset.questionId;
                const selectedOption = questionDiv.querySelector(`input[name="question-${questionId}"]:checked`);

                // CORREÇÃO: Captura dinamicamente a textarea de evidências da pergunta atual
                const txtArea = questionDiv.querySelector('.quali-textarea');
                const textoEvidencia = txtArea ? txtArea.value.trim() : '';

                if (selectedOption) {
                    answers.push({
                        id_ques: parseInt(questionId, 10),
                        grad_ques: parseQuestionGrad(selectedOption.value),
                        quali_ques: textoEvidencia, // Injeta o texto coletado com segurança
                        id_dime: parseInt(questionDiv.dataset.dimId, 10),
                        id_doma: parseInt(questionDiv.dataset.domaId, 10),
                        prefu_ques: questionDiv.dataset.prefu
                    });
                }
            });
            return answers;
        }

        async function submitAnswers(prefuQues, buttonElement, statusElement, finalizeCalculation = false) {
            const safeStatus = statusElement || { textContent: '', style: {} };
            const answers = collectAnswers(prefuQues);
            const originalButtonText = buttonElement.textContent;

            if (answers.length === 0) return false;

            buttonElement.disabled = true;
            try {
                const endpoint = `${API_BASE_URL}/ctdi_surv`;
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id_matu: parseInt(maturityId, 10),
                        answers: answers,
                        finalize: finalizeCalculation
                    }),
                });
                return response.ok;
            } catch (error) {
                console.error('Erro no envio:', error);
                return false;
            }
        }

        async function loadSavedAnswers(mId) {
            try {
                const response = await fetch(`${API_BASE_URL}/ctdi_surv/by_maturity/${mId}`);
                if (!response.ok) return;
                const answersData = await response.json();

                if (answersData && answersData.length > 0) {
                    const isRestricted = evaluationForm.getAttribute('data-restricted') === 'true';
                    const scopeIds = new Set(
                        getAssessmentScopeItems(isRestricted).map(item => String(item.dataset.questionId))
                    );

                    answersData.forEach(answer => restoreSurveyAnswerToDom(answer));
                    answersData.forEach(answer => {
                        const qId = String(answer.id_ques);
                        if (scopeIds.has(qId)) assessmentSavedIds.add(qId);
                    });

                    const totalP = document.querySelectorAll('.question-item[data-prefu="P"]').length;
                    let countP = 0, countF = 0;

                    answersData.forEach(answer => {
                        const qId = String(answer.id_ques);
                        if (!scopeIds.has(qId)) return;

                        const qEl = document.querySelector(`.question-item[data-question-id="${qId}"]`);
                        if (qEl) {
                            if (qEl.dataset.prefu === 'P') countP++;
                            if (qEl.dataset.prefu === 'F') countF++;
                        }
                    });

                    if (totalP > 0 && countP >= totalP) {
                        const pBtn = document.querySelector('.present-submit-btn');
                        if (pBtn) {
                            pBtn.disabled = true;
                            pBtn.style.background = 'linear-gradient(45deg, #d4af37, #f1c40f)';
                            pBtn.style.color = 'white';
                            pBtn.textContent = "Avaliação do Estado Atual Finalizada!";
                        }
                    }
                    const totalQuestions = ASSESSMENT_META.full.totalQuestions;
                    if (countP + countF >= totalQuestions) {
                        if (futureSubmitBtn) {
                            futureSubmitBtn.disabled = true;
                            futureSubmitBtn.style.background = 'linear-gradient(45deg, #d4af37, #f1c40f)';
                            futureSubmitBtn.style.color = 'white';
                            futureSubmitBtn.style.boxShadow = '0 4px 15px rgba(212, 175, 55, 0.3)';
                            futureSubmitBtn.textContent = "Avaliação Finalizada com Sucesso!";
                        }
                    }
                }
            } catch (e) { console.error('Erro ao carregar respostas:', e); }
        }

        function showStep(n) {
            if (window.panelDxVozInstances && window.panelDxVozInstances.assessment) {
                var voz = window.panelDxVozInstances.assessment;
                if (voz.sessionAtiva) voz.parar(true);
            }
            steps.forEach((step, index) => {
                if (index === n) {
                    step.style.setProperty('display', 'block', 'important');
                    step.classList.add('active');
                } else {
                    step.style.setProperty('display', 'none', 'important');
                    step.classList.remove('active');
                }

                if (indicators[index]) {
                    if (index === n) {
                        indicators[index].classList.add('active');
                    } else {
                        indicators[index].classList.remove('active');
                    }
                }
            });
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // --- EVENT LISTENERS ---

        // 1. Salvamento Automático (Change para Radios - Notas)
        evaluationForm.addEventListener('change', async (e) => {
            if (e.target.type === 'radio') {
                const questionDiv = e.target.closest('.question-item');
                const singleAnswer = {
                    id_matu: parseInt(maturityId, 10),
                    id_ques: parseInt(questionDiv.dataset.questionId, 10),
                    grad_ques: parseQuestionGrad(e.target.value),
                    quali_ques: questionDiv.querySelector('.quali-textarea')?.value.trim() || '', // Mantém o texto se houver
                    id_dime: parseInt(questionDiv.dataset.dimId, 10),
                    id_doma: parseInt(questionDiv.dataset.domaId, 10),
                    prefu_ques: questionDiv.dataset.prefu
                };

                try {
                    await fetch(`${API_BASE_URL}/ctdi_surv/partial`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(singleAnswer),
                    });
                    questionDiv.style.borderLeft = "4px solid #6c5ce7";
                    assessmentSavedIds.add(String(questionDiv.dataset.questionId));
                    recordAnswerStreak();
                    atualizarProgressoGeral({ fromAnswer: true });
                } catch (err) { console.error("Erro no salvamento parcial:", err); }
            }
        });

        // 2. NOVO: Salvamento Automático (Blur para Textareas - Evidências)
        evaluationForm.addEventListener('blur', async (e) => {
            // Verifica se o elemento que perdeu o foco é a nossa área de texto
            if (e.target.classList.contains('quali-textarea')) {
                const questionDiv = e.target.closest('.question-item');
                const questionId = questionDiv.dataset.questionId;

                // Captura o rádio selecionado (se houver) para não zerar a nota ao salvar o texto
                const selectedRadio = questionDiv.querySelector(`input[name="question-${questionId}"]:checked`);

                const partialData = {
                    id_matu: parseInt(maturityId, 10),
                    id_ques: parseInt(questionId, 10),
                    grad_ques: selectedRadio ? parseQuestionGrad(selectedRadio.value) : null,
                    quali_ques: e.target.value.trim(), // Nome exato da coluna no seu DB
                    id_dime: parseInt(questionDiv.dataset.dimId, 10),
                    id_doma: parseInt(questionDiv.dataset.domaId, 10),
                    prefu_ques: questionDiv.dataset.prefu
                };

                try {
                    await fetch(`${API_BASE_URL}/ctdi_surv/partial`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(partialData),
                    });
                    // Feedback visual em azul/roxo para diferenciar que foi o texto que salvou
                    questionDiv.style.borderLeft = "4px solid #6c5ce7";
                } catch (err) {
                    console.error("Erro no salvamento qualitativo:", err);
                }
            }
        }, true); // 'true' habilita a captura do evento em elementos que não propagam o focus/blur por padrão

        // 2. Navegação Wizard (Click) - CORREÇÃO DE CLIQUE E PREVENÇÃO DE SUBMIT
        evaluationForm.addEventListener('click', (e) => {
            const nextBtn = e.target.closest('.next-btn');
            const prevBtn = e.target.closest('.prev-btn');

            if (nextBtn) {
                e.preventDefault();
                if (currentStep < steps.length - 1) {
                    currentStep++;
                    showStep(currentStep);
                }
            } else if (prevBtn) {
                e.preventDefault();
                if (currentStep > 0) {
                    currentStep--;
                    showStep(currentStep);
                }
            }
        });

        // 3. Clique nos Indicadores/Abas
        indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => {
                currentStep = index;
                showStep(currentStep);
            });
        });

        // 4. Finalização (Submit Final)
        if (futureSubmitBtn) {
            futureSubmitBtn.addEventListener('click', async (event) => {
                event.preventDefault();
                if (!(await assertAssessmentComplete())) return;
                if(!confirm("Deseja finalizar sua avaliação e gerar o diagnóstico?")) return;

                futureSubmitBtn.disabled = true;
                futureSubmitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando...';

                const okP = await submitAnswers(TYPE_MATU_PRESENT, futureSubmitBtn, statusFutureEl, false);
                if (okP) {
                    await new Promise(r => setTimeout(r, 500));
                    const okF = await submitAnswers(TYPE_MATU_FUTURE, futureSubmitBtn, statusFutureEl, true);
                    if (okF) {
                        futureSubmitBtn.style.background = 'linear-gradient(45deg, #d4af37, #f1c40f)';
                        futureSubmitBtn.textContent = "Avaliação Finalizada com Sucesso!";
                        setTimeout(() => window.location.href = '/', 2000);
                    }
                } else {
                    futureSubmitBtn.disabled = false;
                    futureSubmitBtn.textContent = "Finalizar e Gerar Diagnóstico";
                }
            });
        }

        // --- INICIALIZAÇÃO ---
        const legacyProgress = document.getElementById('progress-container');
        if (legacyProgress) legacyProgress.remove();

        syncAssessmentDockLayout();
        window.addEventListener('resize', syncAssessmentDockLayout);

        const assessmentDockEl = document.getElementById('assessment-progress-dock');
        if (assessmentDockEl && typeof ResizeObserver !== 'undefined') {
            const dockResizeObserver = new ResizeObserver(() => syncAssessmentDockLayout());
            dockResizeObserver.observe(assessmentDockEl);
        }

        (async () => {
            bootstrapAssessmentSavedIds();
            if (maturityId && maturityId !== "undefined") {
                await loadSavedAnswers(maturityId);
            }
            showStep(currentStep);
            atualizarProgressoGeral();
        })();

        document.addEventListener('assessment-coverage-changed', async () => {
            if (maturityId && maturityId !== "undefined") {
                await loadSavedAnswers(maturityId);
                atualizarProgressoGeral();
            }
        });

        window.panelDxAssessment = {
            isRestricted: () => evaluationForm.getAttribute('data-restricted') === 'true',
            getPresurveyState: getPresurveyProgress,
            refreshProgress: () => atualizarProgressoGeral(),
            maturityId,
        };
    }
}


    // --- Lógica para a página de Avaliações (listagem) --- [VERSÃO UNIFICADA]
    if (document.getElementById('avaliacoes-list-page')) {
        const tableBody = document.querySelector('.data-table tbody');
        const searchBtn = document.getElementById('search-btn');
        const searchInput = document.getElementById('search-input');

        // 1. Lógica de Clique nos Ícones (Redirecionamento)
        if (tableBody) {
            tableBody.addEventListener('click', (event) => {
                // Encontra o botão mais próximo do clique, mesmo que tenha sido no ícone
                const btn = event.target.closest('button') || event.target.closest('a');
                if (!btn) return;

                const recordId = btn.dataset.id;
                if (!recordId) return;

                // Direciona para Avaliação (Ícone Laranja)
                if (btn.classList.contains('view-btn')) {
                    window.location.href = `/avaliacoes/${recordId}`;
                }

                // Direciona para Diagnóstico (Ícone Vermelho)
                if (btn.classList.contains('view-btn-dia')) {
                    window.location.href = `/diagnostico/${recordId}`;
                }
            });
        }

        // 2. Lógica de Busca (Botão Azul)
        if (searchBtn && searchInput) {
            const executarFiltro = () => {
                const termo = searchInput.value.toLowerCase().trim();
                const linhas = tableBody.querySelectorAll('tr');

                linhas.forEach(linha => {
                    // O nome do cliente está na segunda coluna (index 1)
                    const nomeCliente = linha.cells[1] ? linha.cells[1].textContent.toLowerCase() : '';
                    if (nomeCliente.includes(termo)) {
                        linha.style.display = '';
                    } else {
                        linha.style.display = 'none';
                    }
                });
            };

            // Clique no botão de busca
            searchBtn.addEventListener('click', executarFiltro);

            // Busca ao apertar "Enter"
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') executarFiltro();
            });
        }
    }

   // --- Matriz de Desempenho (compartilhada: relatório + dashboard) ---
    const MATURITY_DOM_LIST = [
        {id: 1, name: 'Estratégia Digital (ds)'},
        {id: 2, name: 'Modelo de Negócio Digital (bm)'},
        {id: 3, name: 'Cultura de Inovação (ic)'},
        {id: 4, name: 'Cultura de Dados (dcd)'},
        {id: 5, name: 'Cultura de Colaboração (cc)'},
        {id: 6, name: 'Governança Digital (dg)'},
        {id: 7, name: 'Plataformas Digitais (dp)'},
        {id: 8, name: 'Capacidades Digitais (dcp)'},
        {id: 9, name: 'Métricas Digitais (dm)'}
    ];

    const DOMAIN_INITIALS_MAP = {
        '1': 'ds', '2': 'bm', '3': 'ic', '4': 'dcd', '5': 'cc',
        '6': 'dg', '7': 'dp', '8': 'dcp', '9': 'dm'
    };

    const MATRIX_HYBRID_ALPHA = 0.4;
    const MATRIX_HYBRID_BETA = 0.25;

    const MATRIX_DOMAIN_COLORS = {
        '1': { fill: 'rgba(108, 92, 231, 0.92)', border: '#4A2E80' },
        '2': { fill: 'rgba(91, 33, 182, 0.92)', border: '#3b0764' },
        '3': { fill: 'rgba(217, 119, 6, 0.92)', border: '#92400e' },
        '4': { fill: 'rgba(124, 45, 18, 0.92)', border: '#7c2d12' },
        '5': { fill: 'rgba(8, 145, 178, 0.92)', border: '#0e7490' },
        '6': { fill: 'rgba(147, 51, 234, 0.92)', border: '#6b21a8' },
        '7': { fill: 'rgba(5, 150, 105, 0.92)', border: '#047857' },
        '8': { fill: 'rgba(185, 28, 28, 0.92)', border: '#991b1b' },
        '9': { fill: 'rgba(99, 102, 241, 0.92)', border: '#4338ca' }
    };

    const MATRIX_RADIUS_MIN = 8;
    const MATRIX_RADIUS_MAX = 22;

    function getMatrixNumericScore(score) {
        const num = parseFloat(score);
        return isNaN(num) ? 0 : num;
    }

    function computeRawFragmentation(point) {
        const range = Math.max(0, (point.maxPres ?? point.meanPres) - point.minPres);
        const fromSignals = Math.min(1, Math.max(
            range / 2.0,
            (point.cvPres || 0) / 0.30,
            (point.stdPres || 0) / 1.0,
            (point.scoreG || 0) / 1.5,
            (point.blockGapStd || 0) / 1.0,
            (point.blockGapRange || 0) / 2.0
        ));
        if (Number.isFinite(point.fragmentationIndex)) {
            return Math.max(point.fragmentationIndex, fromSignals);
        }
        return fromSignals;
    }

    function applyMatrixBubbleSizes(dataPoints) {
        dataPoints.forEach((p) => {
            p.rawFragmentation = computeRawFragmentation(p);
        });

        const rawVals = dataPoints.map((p) => p.rawFragmentation);
        const rawMin = Math.min(...rawVals);
        const rawMax = Math.max(...rawVals);
        const hasSpread = rawMax - rawMin > 0.02;

        const gapSorted = [...dataPoints].sort((a, b) => a.scoreG - b.scoreG);

        dataPoints.forEach((p) => {
            let frag = hasSpread
                ? (p.rawFragmentation - rawMin) / (rawMax - rawMin)
                : 0;

            const gapRank = gapSorted.indexOf(p) / Math.max(1, dataPoints.length - 1);
            frag = Math.max(frag, gapRank * 0.65);

            if (!hasSpread && frag < 0.1) {
                frag = 0.08 + gapRank * 0.55;
            }

            p.fragmentation = Math.min(1, Math.max(0.04, frag));
            p.pointRadius = fragmentationToRadius(p.fragmentation);
        });
    }

    function getMatrixDomainStats(report, domId, scoresPres, scoresFut, scoresGap) {
        const backend = report?.matrix_domain_stats?.[domId];
        if (backend) {
            return {
                meanPres: getMatrixNumericScore(backend.mean_pres),
                meanFut: getMatrixNumericScore(backend.mean_fut),
                adjustedReality: getMatrixNumericScore(backend.adjusted_reality),
                minPres: getMatrixNumericScore(backend.min_pres),
                maxPres: getMatrixNumericScore(backend.max_pres),
                cvPres: getMatrixNumericScore(backend.cv_pres),
                stdPres: getMatrixNumericScore(backend.std_pres),
                rangePres: getMatrixNumericScore(backend.range_pres),
                gap: getMatrixNumericScore(backend.gap),
                cvPenalty: getMatrixNumericScore(backend.cv_penalty),
                weaknessPenalty: getMatrixNumericScore(backend.weakness_penalty),
                blockCount: parseInt(backend.block_count_pres, 10) || 0,
                blockGapStd: getMatrixNumericScore(backend.block_gap_std),
                blockGapRange: getMatrixNumericScore(backend.block_gap_range),
                fragmentationIndex: getMatrixNumericScore(backend.fragmentation_index)
            };
        }

        const meanPres = getMatrixNumericScore(scoresPres[domId]);
        const meanFut = getMatrixNumericScore(scoresFut[domId]);
        const gap = getMatrixNumericScore(scoresGap[domId]) || Math.max(0, meanFut - meanPres);

        return {
            meanPres,
            meanFut,
            adjustedReality: meanPres,
            minPres: meanPres,
            maxPres: meanPres,
            cvPres: 0,
            stdPres: 0,
            rangePres: 0,
            gap,
            cvPenalty: 0,
            weaknessPenalty: 0,
            blockCount: 0,
            blockGapStd: 0,
            blockGapRange: 0,
            fragmentationIndex: Math.min(1, gap / 1.5)
        };
    }

    function fragmentationToRadius(score) {
        const eased = Math.pow(Math.max(0, score), 0.4);
        return MATRIX_RADIUS_MIN + eased * (MATRIX_RADIUS_MAX - MATRIX_RADIUS_MIN);
    }

    function parseMatrixBubbleRgb(color) {
        const match = String(color).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) return { r: 108, g: 92, b: 231 };
        return { r: +match[1], g: +match[2], b: +match[3] };
    }

    function shadeMatrixRgb(rgb, factor) {
        return {
            r: Math.min(255, Math.max(0, Math.round(rgb.r * factor))),
            g: Math.min(255, Math.max(0, Math.round(rgb.g * factor))),
            b: Math.min(255, Math.max(0, Math.round(rgb.b * factor)))
        };
    }

    function drawMatrix3DBubble(ctx, x, y, radius, fillColor, borderColor, initials) {
        const base = parseMatrixBubbleRgb(fillColor);
        const dark = shadeMatrixRgb(base, 0.5);
        const mid = shadeMatrixRgb(base, 0.88);
        const light = shadeMatrixRgb(base, 1.28);
        const highlight = shadeMatrixRgb(base, 1.55);

        ctx.save();

        ctx.shadowColor = 'rgba(74, 46, 128, 0.2)';
        ctx.shadowBlur = Math.max(2, radius * 0.12);
        ctx.shadowOffsetX = radius * 0.06;
        ctx.shadowOffsetY = radius * 0.08;
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgb(${dark.r}, ${dark.g}, ${dark.b})`;
        ctx.fill();
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;

        const gradient = ctx.createRadialGradient(
            x - radius * 0.34,
            y - radius * 0.36,
            radius * 0.05,
            x + radius * 0.08,
            y + radius * 0.1,
            radius
        );
        gradient.addColorStop(0, `rgb(${highlight.r}, ${highlight.g}, ${highlight.b})`);
        gradient.addColorStop(0.38, `rgb(${light.r}, ${light.g}, ${light.b})`);
        gradient.addColorStop(0.72, `rgb(${mid.r}, ${mid.g}, ${mid.b})`);
        gradient.addColorStop(1, `rgb(${dark.r}, ${dark.g}, ${dark.b})`);

        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.strokeStyle = borderColor;
        ctx.lineWidth = Math.max(2, radius * 0.055);
        ctx.stroke();

        ctx.beginPath();
        ctx.ellipse(
            x - radius * 0.3,
            y - radius * 0.34,
            radius * 0.24,
            radius * 0.15,
            -0.55,
            0,
            Math.PI * 2
        );
        ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        ctx.fill();

        ctx.beginPath();
        ctx.ellipse(
            x + radius * 0.22,
            y + radius * 0.28,
            radius * 0.18,
            radius * 0.1,
            0.4,
            0,
            Math.PI * 2
        );
        ctx.fillStyle = 'rgba(0, 0, 0, 0.12)';
        ctx.fill();

        const fontSize = Math.max(8, Math.min(12, Math.round(radius * 0.42)));
        const label = String(initials || '').toUpperCase();
        ctx.font = `800 ${fontSize}px Segoe UI, Tahoma, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = 'rgba(30, 20, 50, 0.35)';
        ctx.fillText(label, x + 1, y + 1);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, x, y);

        ctx.restore();
    }

    const MATRIX_3D_BUBBLE_PLUGIN = {
        id: 'matrix3dBubbles',
        afterDatasetsDraw(chart) {
            const meta = chart.getDatasetMeta(0);
            if (!meta?.data?.length) return;

            const { ctx } = chart;
            meta.data.forEach((element) => {
                const raw = element.$context?.raw;
                if (!raw || !Number.isFinite(element.x) || !Number.isFinite(element.y)) return;
                drawMatrix3DBubble(
                    ctx,
                    element.x,
                    element.y,
                    raw.pointRadius ?? MATRIX_RADIUS_MIN,
                    raw.bubbleFill,
                    raw.bubbleBorder,
                    raw.initials
                );
            });
        }
    };

    if (typeof Chart !== 'undefined') {
        try {
            Chart.register(MATRIX_3D_BUBBLE_PLUGIN);
        } catch (err) {
            // plugin já registrado
        }
    }

    function computeMatrixMedian(values, fallback) {
        const nums = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
        if (!nums.length) return fallback;
        const mid = Math.floor(nums.length / 2);
        return nums.length % 2 === 0 ? (nums[mid - 1] + nums[mid]) / 2 : nums[mid];
    }

    function renderPrioritizationMatrix(report, canvasId) {
        const targetId = canvasId || 'prioritizationMatrix';
        const ctx = document.getElementById(targetId);
        if (!ctx || typeof Chart === 'undefined') return;

        try {
        const existingChart = Chart.getChart(ctx);
        if (existingChart) existingChart.destroy();

        const MAX_SCORE = 5.0;
        const scoresPres = report?.scores_detalhe_presente?.pdom_scores || {};
        const scoresFut = report?.scores_detalhe_futuro?.pdom_scores || {};
        const scoresGap = report?.scores_detalhe_gap?.pdom_scores || {};
        const dataPoints = [];

        MATURITY_DOM_LIST.forEach((dom) => {
            const id_doma = dom.id.toString();
            const stats = getMatrixDomainStats(report, id_doma, scoresPres, scoresFut, scoresGap);
            const colors = MATRIX_DOMAIN_COLORS[id_doma] || MATRIX_DOMAIN_COLORS['1'];

            dataPoints.push({
                x: Math.min(MAX_SCORE, Math.max(0, stats.meanFut)),
                y: Math.min(MAX_SCORE, Math.max(0, stats.adjustedReality)),
                rawX: stats.meanFut,
                rawY: stats.adjustedReality,
                meanPres: stats.meanPres,
                label: dom.name,
                domId: id_doma,
                initials: DOMAIN_INITIALS_MAP[id_doma] || '??',
                scoreF: stats.meanFut,
                scoreP: stats.meanPres,
                scoreG: stats.gap,
                cvPres: stats.cvPres,
                minPres: stats.minPres,
                maxPres: stats.maxPres,
                rangePres: stats.rangePres,
                stdPres: stats.stdPres,
                blockGapStd: stats.blockGapStd,
                blockGapRange: stats.blockGapRange,
                fragmentationIndex: stats.fragmentationIndex,
                cvPenalty: stats.cvPenalty,
                weaknessPenalty: stats.weaknessPenalty,
                blockCount: stats.blockCount,
                bubbleFill: colors.fill,
                bubbleBorder: colors.border
            });
        });

        const matrixMeta = report?.matrix_meta || {};
        const medianAmbition = Number.isFinite(matrixMeta.median_ambition)
            ? matrixMeta.median_ambition
            : computeMatrixMedian(dataPoints.map((p) => p.rawX), 2.5);
        const medianReality = Number.isFinite(matrixMeta.median_reality_adjusted)
            ? matrixMeta.median_reality_adjusted
            : computeMatrixMedian(dataPoints.map((p) => p.rawY), 2.5);

        applyMatrixBubbleSizes(dataPoints);

        const MATRIX_THEME = {
            axis: '#4A2E80',
            qVictory: 'rgba(108, 92, 231, 0.16)',
            qEverest: 'rgba(185, 28, 28, 0.11)',
            qInertia: 'rgba(217, 119, 6, 0.14)',
            qDeath: 'rgba(124, 45, 18, 0.12)'
        };

        const annotations = [
            { type: 'box', xMin: medianAmbition, xMax: MAX_SCORE, yMin: medianReality, yMax: MAX_SCORE, backgroundColor: MATRIX_THEME.qVictory, borderWidth: 0 },
            { type: 'box', xMin: medianAmbition, xMax: MAX_SCORE, yMin: 0, yMax: medianReality, backgroundColor: MATRIX_THEME.qEverest, borderWidth: 0 },
            { type: 'box', xMin: 0, xMax: medianAmbition, yMin: medianReality, yMax: MAX_SCORE, backgroundColor: MATRIX_THEME.qInertia, borderWidth: 0 },
            { type: 'box', xMin: 0, xMax: medianAmbition, yMin: 0, yMax: medianReality, backgroundColor: MATRIX_THEME.qDeath, borderWidth: 0 },
            { type: 'line', xMin: 0, xMax: MAX_SCORE, yMin: medianReality, yMax: medianReality, borderColor: MATRIX_THEME.axis, borderWidth: 2, borderDash: [6, 4] },
            { type: 'line', xMin: medianAmbition, xMax: medianAmbition, yMin: 0, yMax: MAX_SCORE, borderColor: MATRIX_THEME.axis, borderWidth: 2, borderDash: [6, 4] }
        ];

        new Chart(ctx, {
            type: 'scatter',
            plugins: [MATRIX_3D_BUBBLE_PLUGIN],
            data: {
                datasets: [{
                    label: 'Domínios',
                    data: dataPoints,
                    pointStyle: 'circle',
                    backgroundColor: 'transparent',
                    borderColor: 'transparent',
                    borderWidth: 0,
                    hoverBackgroundColor: 'rgba(108, 92, 231, 0.12)',
                    hoverBorderColor: 'transparent',
                    pointRadius: (context) => context.raw?.pointRadius ?? MATRIX_RADIUS_MIN,
                    pointHoverRadius: (context) => (context.raw?.pointRadius ?? MATRIX_RADIUS_MIN) + 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: false,
                layout: {
                    padding: { top: 12, right: 16, bottom: 12, left: 12 }
                },
                plugins: {
                    annotation: { annotations },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const p = context.raw;
                                return [
                                    `${p.label} (${p.initials.toUpperCase()})`,
                                    `Ambição (X): ${p.rawX.toFixed(2)}`,
                                    `Realidade média: ${p.meanPres.toFixed(2)}`,
                                    `Realidade ajustada (Y): ${p.rawY.toFixed(2)}`,
                                    `Elo mais fraco: ${p.minPres.toFixed(2)}`,
                                    `Amplitude presente: ${(p.rangePres ?? 0).toFixed(2)} (min ${p.minPres.toFixed(2)} · max ${(p.maxPres ?? p.minPres).toFixed(2)})`,
                                    `CV presente: ${p.cvPres.toFixed(2)} (σ ${p.stdPres.toFixed(2)})`,
                                    `Dispersão entre blocos: σ ${(p.blockGapStd ?? 0).toFixed(2)} · amp. ${(p.blockGapRange ?? 0).toFixed(2)}`,
                                    `Índice fragmentação: ${(p.rawFragmentation ?? 0).toFixed(2)} → ${(p.fragmentation * 100).toFixed(0)}% · raio ${p.pointRadius.toFixed(0)}px`,
                                    `Penalidade CV: −${p.cvPenalty.toFixed(2)} · elo fraco: −${p.weaknessPenalty.toFixed(2)}`,
                                    `Lacuna: ${p.scoreG.toFixed(2)}`
                                ];
                            }
                        }
                    },
                    legend: { display: false },
                    title: { display: false }
                },
                scales: {
                    x: {
                        title: { display: true, text: 'Ambição (futuro médio)', font: { weight: 'bold', size: 12 }, color: '#4A2E80' },
                        min: 0,
                        max: MAX_SCORE,
                        ticks: {
                            stepSize: 1,
                            color: '#64748b',
                            callback(value) {
                                if (Math.abs(value - medianAmbition) < 0.05) {
                                    return `${medianAmbition.toFixed(1)} (med.)`;
                                }
                                if (value === MAX_SCORE) return `${MAX_SCORE} (Alto)`;
                                if (value === 0) return '0 (Baixo)';
                                return value;
                            }
                        },
                        grid: {
                            color: (context) => (Math.abs(context.tick.value - medianAmbition) < 0.05 ? MATRIX_THEME.axis : 'rgba(74, 46, 128, 0.08)'),
                            lineWidth: (context) => (Math.abs(context.tick.value - medianAmbition) < 0.05 ? 2 : 1)
                        }
                    },
                    y: {
                        title: { display: true, text: 'Realidade ajustada (presente)', font: { weight: 'bold', size: 12 }, color: '#4A2E80' },
                        min: 0,
                        max: MAX_SCORE,
                        ticks: {
                            stepSize: 1,
                            color: '#64748b',
                            callback(value) {
                                if (Math.abs(value - medianReality) < 0.05) {
                                    return `${medianReality.toFixed(1)} (med.)`;
                                }
                                if (value === MAX_SCORE) return `${MAX_SCORE} (Alta)`;
                                if (value === 0) return '0 (Baixa)';
                                return value;
                            }
                        },
                        grid: {
                            color: (context) => (Math.abs(context.tick.value - medianReality) < 0.05 ? MATRIX_THEME.axis : 'rgba(74, 46, 128, 0.08)'),
                            lineWidth: (context) => (Math.abs(context.tick.value - medianReality) < 0.05 ? 2 : 1)
                        }
                    }
                }
            }
        });
        } catch (chartErr) {
            console.error('[Matriz] Erro ao renderizar gráfico:', chartErr);
        }
    }

    window.renderPrioritizationMatrix = renderPrioritizationMatrix;

   // --- Lógica para a página de Diagnóstico (Chart.js) inserido em 07/10/2025----------------------------------
    if (document.getElementById('diagnostico-page')) {
        // VARIÁVEIS GLOBAIS DE DADOS (para Gráficos e Lógica)
        //const reportData = typeof diagnosticReport !== 'undefined' ? diagnosticReport : {};

        const dimList = [
            {id: 1, name: 'Visão Compartilhada (SV)'},
            {id: 2, name: 'Coração e Conexão (HC)'},
            {id: 3, name: 'Estrutura Fluida (FS)'},
            {id: 4, name: 'Aprendizagem em Ação (LA)'},
            {id: 5, name: 'Arquitetura Digital (DA)'}
        ];

        const domList = [
            {id: 1, name: 'Estratégia Digital (ds)'},
            {id: 2, name: 'Modelo de Negócio Digital (bm)'},
            {id: 3, name: 'Cultura de Inovação (ic)'},
            {id: 4, name: 'Cultura de Dados (dc)'},
            {id: 5, name: 'Cultura de Colaboração (cc)'},
            {id: 6, name: 'Governança Digital (dg)'},
            {id: 7, name: 'Plataformas Digitais (dp)'},
            {id: 8, name: 'Capacidades Digitais (dc)'},
            {id: 9, name: 'Métricas Digitais (dm)'}
        ];

        // Função auxiliar para extrair o score numérico ou 0, tratando strings e nulls
        const getNumericScore = (score) => {
            const num = parseFloat(score);
            return isNaN(num) ? 0 : num;
        };

        // Função para extrair o ponto médio do benchmark (Range)
        const getMidPoint = (rangeString) => {
            if (!rangeString) return 0;
            try {
                const cleanRange = rangeString.replace(/[\[\]\(\)]/g, '');
                const [min, max] = cleanRange.split(',').map(Number);
                return (min + max) / 2;
            } catch (e) {
                return 0;
            }
        };


        const DIAG_CHART = {
            realidade: { bg: 'rgba(124, 45, 18, 0.32)', border: '#7c2d12', point: '#7c2d12' },
            gapLine: '#b91c1c',
            ambicao: { bg: 'rgba(108, 92, 231, 0.28)', border: '#6c5ce7', point: '#6c5ce7' },
            educacao: { bg: 'rgba(217, 119, 6, 0.28)', border: '#d97706', point: '#d97706' },
            font: { family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", size: 11 },
            grid: 'rgba(74, 46, 128, 0.08)',
            tick: '#64748b'
        };

        function diagBarFill(color) {
            return color.bg.replace(/[\d.]+\)$/, '0.88)');
        }

        function computeFocusedScale(scores, minSpan = 1.4) {
            const vals = scores.filter((v) => Number.isFinite(v));
            if (!vals.length) return { min: 0, max: 5 };

            const dataMin = Math.min(...vals);
            const dataMax = Math.max(...vals);
            const pad = Math.max((dataMax - dataMin) * 0.18, 0.25);
            let min = Math.max(0, dataMin - pad);
            let max = Math.min(5, dataMax + pad);

            if (max - min < minSpan) {
                const mid = (dataMin + dataMax) / 2;
                min = Math.max(0, mid - minSpan / 2);
                max = Math.min(5, mid + minSpan / 2);
            }

            return {
                min: Math.floor(min * 10) / 10,
                max: Math.ceil(max * 10) / 10
            };
        }

        function createDiagGapPlugin(items, mode) {
            return {
                id: `diagGap_${mode}_${Math.random().toString(36).slice(2, 8)}`,
                afterDraw(chart) {
                    const xScale = chart.scales.x;
                    const yScale = chart.scales.y;
                    if (!xScale || !yScale || !items.length) return;

                    const { ctx, chartArea } = chart;
                    ctx.save();
                    ctx.beginPath();
                    ctx.rect(chartArea.left, chartArea.top, chartArea.right - chartArea.left, chartArea.bottom - chartArea.top);
                    ctx.clip();

                    items.forEach((item) => {
                        const gapVal = Number.isFinite(item.gap) ? item.gap : (item.fut - item.pres);
                        if (!Number.isFinite(gapVal) || gapVal <= 0.001) return;

                        const x1 = xScale.getPixelForValue(item.pres);
                        const x2 = xScale.getPixelForValue(item.fut);

                        let y1;
                        let y2;
                        if (mode === 'grouped') {
                            const label = chart.data.labels[item.index];
                            const yCenter = yScale.getPixelForValue(label);
                            const band = chart.data.labels.length ? (yScale.bottom - yScale.top) / chart.data.labels.length : 24;
                            y1 = yCenter - band * 0.18;
                            y2 = yCenter + band * 0.18;
                        } else {
                            y1 = yScale.getPixelForValue('Real.');
                            y2 = yScale.getPixelForValue('Amb.');
                        }

                        ctx.strokeStyle = DIAG_CHART.gapLine;
                        ctx.lineWidth = 3;
                        ctx.setLineDash([5, 4]);
                        ctx.beginPath();
                        ctx.moveTo(x1, y1);
                        ctx.lineTo(x2, y2);
                        ctx.stroke();
                        ctx.setLineDash([]);

                        const midX = (x1 + x2) / 2;
                        const midY = (y1 + y2) / 2;
                        const text = `Δ ${gapVal.toFixed(1)}`;
                        ctx.font = 'bold 10px Segoe UI, Tahoma, sans-serif';
                        const textW = ctx.measureText(text).width;
                        const boxW = textW + 10;
                        const boxH = 16;

                        ctx.fillStyle = DIAG_CHART.gapLine;
                        ctx.fillRect(midX - boxW / 2, midY - boxH / 2, boxW, boxH);
                        ctx.fillStyle = '#fff';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = 'middle';
                        ctx.fillText(text, midX, midY);
                    });

                    ctx.restore();
                }
            };
        }

        function updateDomainGapBadge(canvas, gap) {
            const card = canvas?.closest('.diag-domain-card');
            const head = card?.querySelector('.diag-domain-card__head');
            if (!head) return;

            let badge = head.querySelector('.diag-domain-card__gap');
            if (gap <= 0.001) {
                if (badge) badge.remove();
                return;
            }

            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'diag-domain-card__gap';
                head.appendChild(badge);
            }
            badge.textContent = `Δ ${gap.toFixed(1)}`;
        }

        function destroyDiagChart(canvas) {
            if (!canvas || typeof Chart === 'undefined') return;
            const existing = Chart.getChart(canvas);
            if (existing) existing.destroy();
        }

        const DIM_SHORT = { 1: 'SV', 2: 'HC', 3: 'FS', 4: 'LA', 5: 'DA' };

        // --- FUNÇÃO 1: GRÁFICO DE DIMENSÕES (BARRAS HORIZONTAIS) ---
        function renderDimensionChart(report) {
            const ctx = document.getElementById('dimensaoChart');
            destroyDiagChart(ctx);

            const scores_detalhe_pres = report.scores_detalhe_presente || {};
            const scores_detalhe_fut = report.scores_detalhe_futuro || {};
            const scores_educacao = report.score_educacao || {};
            const scores_educacao_pres = scores_educacao.detalhe_pres || {};
            const pdim_scores_edu = scores_educacao_pres.pdim || {};

            if (!ctx || Object.keys(scores_detalhe_pres.pdim_scores || {}).length === 0) {
                if (ctx) ctx.closest('.diag-chart-panel')?.classList.add('is-empty');
                return;
            }

            const pdim_scores_pres = scores_detalhe_pres.pdim_scores || {};
            const pdim_scores_fut = scores_detalhe_fut.pdim_scores || {};
            const pdim_scores_gap = (report.scores_detalhe_gap || {}).pdim_scores || {};
            const labels = [];
            const dimNames = [];
            const clientScoresPresente = [];
            const clientScoresFuturo = [];
            const educationScores = [];
            const gapItems = [];

            for (const dim of dimList) {
                const id_dime = dim.id.toString();
                labels.push(DIM_SHORT[dim.id] || dim.name);
                dimNames.push(dim.name);
                const pres = getNumericScore(pdim_scores_pres[id_dime]);
                const fut = getNumericScore(pdim_scores_fut[id_dime]);
                const gap = getNumericScore(pdim_scores_gap[id_dime]) || Math.max(0, fut - pres);
                clientScoresPresente.push(pres);
                clientScoresFuturo.push(fut);
                educationScores.push(getNumericScore(pdim_scores_edu[id_dime]));
                gapItems.push({ pres, fut, gap, index: gapItems.length });
            }

            const xScale = computeFocusedScale([
                ...clientScoresPresente,
                ...clientScoresFuturo,
                ...educationScores
            ]);

            new Chart(ctx, {
                type: 'bar',
                plugins: [createDiagGapPlugin(gapItems.filter((g) => g.gap > 0.001), 'grouped')],
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Realidade',
                        data: clientScoresPresente,
                        backgroundColor: diagBarFill(DIAG_CHART.realidade),
                        borderColor: DIAG_CHART.realidade.border,
                        borderWidth: 2,
                        borderRadius: 4,
                        borderSkipped: false
                    }, {
                        label: 'Ambição',
                        data: clientScoresFuturo,
                        backgroundColor: diagBarFill(DIAG_CHART.ambicao),
                        borderColor: DIAG_CHART.ambicao.border,
                        borderWidth: 2,
                        borderRadius: 4,
                        borderSkipped: false
                    }, {
                        label: 'Setor Educação',
                        data: educationScores,
                        backgroundColor: diagBarFill(DIAG_CHART.educacao),
                        borderColor: DIAG_CHART.educacao.border,
                        borderWidth: 2,
                        borderRadius: 4,
                        borderSkipped: false
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: false,
                    scales: {
                        x: {
                            min: xScale.min,
                            max: xScale.max,
                            ticks: {
                                stepSize: 0.5,
                                font: DIAG_CHART.font,
                                color: DIAG_CHART.tick
                            },
                            grid: { color: DIAG_CHART.grid }
                        },
                        y: {
                            ticks: {
                                font: { ...DIAG_CHART.font, weight: '700' },
                                color: '#4A2E80'
                            },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        title: { display: false },
                        tooltip: {
                            callbacks: {
                                title: (items) => dimNames[items[0].dataIndex] || items[0].label,
                                label: (item) => `${item.dataset.label}: ${Number(item.raw).toFixed(2)}`,
                                afterBody: (items) => {
                                    const idx = items[0].dataIndex;
                                    const gapVal = gapItems[idx].gap;
                                    return gapVal > 0.001 ? [`Lacuna: ${gapVal.toFixed(2)}`] : [];
                                }
                            }
                        }
                    }
                }
            });
        }

        // --- FUNÇÃO 2: GRÁFICOS DE DOMÍNIOS (BARRAS) ---
        function renderDomainCharts(report) {
            const scores_detalhe_pres = report.scores_detalhe_presente || {};
            const scores_detalhe_fut = report.scores_detalhe_futuro || {};
            const scores_educacao = report.score_educacao || {};
            const scores_educacao_pres = scores_educacao.detalhe_pres || {};
            const pdom_scores_edu = scores_educacao_pres.pdom || {};
            const pdom_scores_pres = scores_detalhe_pres.pdom_scores || {};
            const pdom_scores_fut = scores_detalhe_fut.pdom_scores || {};
            const pdom_scores_gap = (report.scores_detalhe_gap || {}).pdom_scores || {};

            domList.forEach(dom => {
                const ctx = document.getElementById(`domainChart_${dom.id}`);
                destroyDiagChart(ctx);
                if (!ctx) return;

                const id_doma = dom.id.toString();
                const scorePres = getNumericScore(pdom_scores_pres[id_doma]);
                const scoreFut = getNumericScore(pdom_scores_fut[id_doma]);
                const scoreEdu = getNumericScore(pdom_scores_edu[id_doma]);
                const gap = getNumericScore(pdom_scores_gap[id_doma]) || Math.max(0, scoreFut - scorePres);
                const xScale = computeFocusedScale([scorePres, scoreFut, scoreEdu], 1.0);
                const gapBarData = gap > 0.001
                    ? [[Math.min(scorePres, scoreFut), Math.max(scorePres, scoreFut)], null, null]
                    : [null, null, null];

                updateDomainGapBadge(ctx, gap);

                new Chart(ctx, {
                    type: 'bar',
                    plugins: [createDiagGapPlugin([{ pres: scorePres, fut: scoreFut, gap }], 'rows')],
                    data: {
                        labels: ['Real.', 'Amb.', 'Edu.'],
                        datasets: [{
                            label: 'Lacuna',
                            data: gapBarData,
                            backgroundColor: 'rgba(185, 28, 28, 0.55)',
                            borderColor: DIAG_CHART.gapLine,
                            borderWidth: 2,
                            borderRadius: 3,
                            borderSkipped: false,
                            barThickness: 9,
                            order: 2
                        }, {
                            label: 'Nota',
                            data: [scorePres, scoreFut, scoreEdu],
                            backgroundColor: [
                                diagBarFill(DIAG_CHART.realidade),
                                diagBarFill(DIAG_CHART.ambicao),
                                diagBarFill(DIAG_CHART.educacao)
                            ],
                            borderColor: [
                                DIAG_CHART.realidade.border,
                                DIAG_CHART.ambicao.border,
                                DIAG_CHART.educacao.border
                            ],
                            borderWidth: 2,
                            borderRadius: 6,
                            borderSkipped: false,
                            order: 1
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: false,
                        animation: false,
                        scales: {
                            x: {
                                min: xScale.min,
                                max: xScale.max,
                                ticks: {
                                    stepSize: 0.5,
                                    font: { ...DIAG_CHART.font, size: 9 },
                                    color: DIAG_CHART.tick,
                                    maxTicksLimit: 5
                                },
                                grid: { color: DIAG_CHART.grid }
                            },
                            y: {
                                ticks: {
                                    font: { ...DIAG_CHART.font, weight: '700', size: 10 },
                                    color: '#4A2E80'
                                },
                                grid: { display: false }
                            }
                        },
                        plugins: {
                            legend: { display: false },
                            title: { display: false },
                            tooltip: {
                                filter: (item) => item.dataset.label !== 'Lacuna',
                                callbacks: {
                                    title: (items) => {
                                        const map = { 'Real.': 'Realidade', 'Amb.': 'Ambição', 'Edu.': 'Setor Educação' };
                                        return map[items[0].label] || items[0].label;
                                    },
                                    label: (item) => {
                                        const lines = [`Nota: ${Number(item.raw).toFixed(2)}`];
                                        if (item.label === 'Amb.' && gap > 0.001) {
                                            lines.push(`Lacuna: ${gap.toFixed(2)}`);
                                        }
                                        return lines;
                                    }
                                }
                            }
                        }
                    }
                });
            });
        }

        // Dispara a renderização dos gráficos ao carregar a página
        if (document.getElementById('diagnostico-page')) {
            initSprintPriorityCards();

            if (Object.keys(reportData).length > 0) {
                renderDimensionChart(reportData);
                renderDomainCharts(reportData);
                renderPrioritizationMatrix(reportData);
            }
        }

        function initSprintPriorityCards() {
            if (window.PanelRelatorioBlocos && typeof window.PanelRelatorioBlocos.initDiagnosticoPage === 'function') {
                window.PanelRelatorioBlocos.initDiagnosticoPage();
            }
        }

        // --- Lógica de Exportação para PDF --- Atualizado em 22/10/2025
        const exportPdfBtn = document.getElementById('exportPdfBtn');

        if (exportPdfBtn && reportData.id_matu) {
                exportPdfBtn.addEventListener('click', async () => {


                    // --- CORREÇÃO CRÍTICA: DEFINIÇÃO DE VARIÁVEIS DE DADOS AQUI ---
                    // Acessa o objeto global injetado pelo EJS.
                    const reportData = window.diagnosticReport || {};
                    const finalEmail = reportData.email_cliente;

                    // Validação de segurança
                    if (!reportData.id_matu) {
                        console.error("DIAGNÓSTICO: ID de Maturidade ausente. Exportação indisponível.");
                        return; // Sai se não houver dados válidos
                    }
                    // -----------------------------------------------------------
                    // 1. DEBUG DO ID DE MATURIDADE
                    console.log("DEBUG FLUXO: reportData.id_matu (Início):", reportData.id_matu);
                    // -----------------------------------------------------------

                    const input = document.getElementById('diagnostico-page'); //Aqui foi criado

                    // 1. MENSAGEM DE FEEDBACK E PREPARAÇÃO
                    exportPdfBtn.textContent = 'Gerando PDF Localmente...';
                    exportPdfBtn.disabled = true;

                    try {
                        // Fonte de Email: Usa o email do relatório
                        //const finalEmail = reportData.email_cliente
                        const reportData = window.diagnosticReport || {};
                        // -----------------------------------------------------------
                        // 2. DEBUG DO E-MAIL FINAL
                        //console.log("DEBUG FLUXO: finalEmail (Extraído):", finalEmail);
                        // -----------------------------------------------------------

                        // Validação final de segurança para o e-mail antes de enviar----------------------------------
                        //if (!finalEmail || finalEmail.length < 5 || finalEmail.indexOf('@') === -1) {
                                //throw new Error("O e-mail do cliente não foi encontrado no relatório. Login necessário.");
                        //}
                        // --------------------------------------------------------------------------------------------

                        // 2. GERAÇÃO DO PDF NA MEMÓRIA (html2canvas e jsPDF)
                        exportPdfBtn.style.display = 'none'; // Oculta botão durante a renderização

                        // Usamos a escala mais segura para garantir que o PDF seja gerado
                        const canvas = await html2canvas(input, {
                            scale: 1.0, // Escala 1.0 para manter a resolução de tela
                            useCORS: true,
                            allowTaint: true,
                        });

                        const { jsPDF } = window.jspdf;
                        const pdf = new jsPDF('p', 'mm', 'a4');
                        const imgData = canvas.toDataURL('image/jpeg', 0.8); // JPEG 0.8 para boa qualidade/tamanho

                        // Lógica de Paginação (seu código anterior)
                        const imgWidth = 210;
                        const pageHeight = 295;
                        const imgHeight = canvas.height * imgWidth / canvas.width;
                        let heightLeft = imgHeight;
                        let position = 0;

                        pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
                        heightLeft -= pageHeight;
                        while (heightLeft >= -50) {
                            position = heightLeft - imgHeight;
                            pdf.addPage();
                            pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
                            heightLeft -= pageHeight;
                        }

                        // 1. Dispara o salvamento local
                        const fileName = `Diagnostico_Maturidade_ID_${reportData.id_matu}.pdf`;
                        pdf.save(fileName);

                        // 2. Usamos setTimeout para atrasar o alerta por um micro-período,
                        // o que permite que a UI do download comece.

                        setTimeout(() => {
                            alert(`Salve o relatório em seu computador!`);
                        }, 100); // Atraso de 200 milissegundos

                    } catch (error) {
                        console.error('Erro CRÍTICO na exportação:', error);
                        //alert(`Falha na comunicação. Verifique o console. Detalhe: ${error.message}`);
                        alert(`Falha ao gerar o PDF. Verifique o console. Detalhe: ${error.message}`);
                    } finally {
                        // 4. Garante que o botão seja restaurado
                        exportPdfBtn.textContent = 'Exportar Relatório para PDF';
                        exportPdfBtn.disabled = false;
                        exportPdfBtn.style.display = 'block';

                        // Opção 1: Se você quiser que o botão retorne à página inicial ou continue no relatório:
                        //window.location.href = '/';
                    }
                });
            }
    }

    async function initDashboardMatrix() {
        const section = document.getElementById('dashboard-matrix-section');
        if (!section || typeof renderPrioritizationMatrix !== 'function') return;

        const idMatu = section.getAttribute('data-id-matu');
        const loadingEl = document.getElementById('dashboard-matrix-loading');
        let report = window.dashboardDiagnosticoReport;

        const hasScores = report
            && report.scores_detalhe_presente
            && report.scores_detalhe_presente.pdom_scores
            && Object.keys(report.scores_detalhe_presente.pdom_scores).length > 0;

        if (!hasScores && idMatu) {
            try {
                const res = await fetch('/api/diagnostico/' + idMatu);
                if (res.ok) {
                    report = await res.json();
                    window.dashboardDiagnosticoReport = report;
                } else if (loadingEl) {
                    loadingEl.textContent = 'Não foi possível carregar a matriz. Tente atualizar a página.';
                    return;
                }
            } catch (err) {
                console.error('[Dashboard] Falha ao carregar matriz:', err);
                if (loadingEl) {
                    loadingEl.textContent = 'Erro de conexão ao carregar a matriz.';
                }
                return;
            }
        }

        if (report && report.scores_detalhe_presente) {
            renderPrioritizationMatrix(report, 'dashboardPrioritizationMatrix');
            if (loadingEl) loadingEl.classList.add('is-hidden');
        } else if (loadingEl) {
            loadingEl.textContent = 'Dados do diagnóstico ainda não disponíveis.';
        }
    }

    initDashboardMatrix();

// ==================================================================
// 🧠 UNIFICAÇÃO DO BARRAMENTO DE CAPTURA DE LEADS (ORQUESTRADOR DE DUAS TABELAS)
// ==================================================================
if (document.getElementById('lead-capture-page')) {
    const form = document.getElementById('leadCaptureForm');
    const statusMessage = document.getElementById('leadStatusMessage');

    // Verifica se o listener já foi anexado ao formulário para evitar duplicação assíncrona
    if (form && !form.dataset.listenerAttached) {
        form.dataset.listenerAttached = 'true';

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            // Proteção estrita contra duplo clique no botão de envio
            const submitBtn = document.querySelector('#leadCaptureForm button[type="submit"]');
            let textoOriginalBotao = "Finalizar Solicitação e Enviar";

            if (submitBtn) {
                textoOriginalBotao = submitBtn.innerText;
                submitBtn.disabled = true;
                submitBtn.textContent = 'Processando Solicitação...';
                submitBtn.style.opacity = "0.6";
                submitBtn.style.cursor = "not-allowed";
            }

            // Ativa o container de feedback sob a paleta sóbria do ecossistema
            statusMessage.style.display = "block";
            statusMessage.textContent = 'Estabelecendo comunicação segura com o ecossistema...';
            statusMessage.style.color = '#4A2E80';
            statusMessage.style.borderColor = '#E2D9FF';
            statusMessage.style.background = '#FDFCFF';

            // Extração dos estados dinâmicos das abas (Empresa vs Inovador)
            const perfilValue = document.getElementById('perfil_lead') ? document.getElementById('perfil_lead').value : 'EMPRESA';
            let empresaValue = document.getElementById('empresa_clie') ? document.getElementById('empresa_clie').value : '';
            let docuValue = document.getElementById('docu_clie') ? document.getElementById('docu_clie').value : '';
            let zipnValue = document.getElementById('zipn_clie') ? document.getElementById('zipn_clie').value : '';
            let adreValue = document.getElementById('adre_clie') ? document.getElementById('adre_clie').value : '';

            // Inteligência de Sandbox: Se for Inovador Solo, preenchemos os campos obrigatórios da tabela principal
            if (perfilValue === 'INOVADOR') {
                empresaValue = "Da Vinci Sandbox (Solo)";
                docuValue = "00.000.000/0001-00"; // Passa liso pela restrição NOT NULL de docu_clie
                zipnValue = "";
                adreValue = "";
            }

            // 🔥 FILTRO DE RELAÇÃO: Enviamos estritamente as colunas físicas da tabela ctdi_clie.
            // Removemos 'FUNC_LEAD' e 'PERFIL_LEAD' pois não existem em nenhuma das duas tabelas,
            // impedindo a quebra de LINE 1 do gerador dinâmico do Python.
            const formData = {
                NOME_CLIE: document.getElementById('nome_clie').value,
                MAIL_CLIE: document.getElementById('mail_clie').value,
                FONE_CLIE: (document.getElementById('fone_clie') ? document.getElementById('fone_clie').value : "") || "",
                EMPRESA_CLIE: empresaValue,
                DOCU_CLIE: docuValue,
                ZIPN_CLIE: zipnValue,
                ADRE_CLIE: adreValue
            };

            console.log("🚀 [scripts.js] Payload limpo enviado ao Flask:", formData);

            try {
                const response = await fetch(`${API_BASE_URL}/ctdi_clie`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });

                let mensagemRetorno = "";
                const contentType = response.headers.get("content-type");

                if (contentType && contentType.includes("application/json")) {
                    const resultJson = await response.json();
                    mensagemRetorno = resultJson.message || resultJson.error || "";
                } else {
                    mensagemRetorno = await response.text();
                }

                if (response.ok) {
                    // SUCESSO PREMIUM UNIFICADO (Black & Lilac)
                    statusMessage.style.color = '#111827';
                    statusMessage.style.borderColor = '#4A2E80';
                    statusMessage.textContent = "Sucesso absoluto! Sua solicitação foi registrada e o código de acesso enviado para o seu e-mail.";

                    form.reset();
                    if (submitBtn) {
                        submitBtn.textContent = 'Solicitação Concluída';
                        submitBtn.style.opacity = "0.5";
                    }
                } else {
                    // TRATAMENTO DE EXCEÇÕES DE BANCO OU DUPLICIDADE
                    statusMessage.style.color = '#000000';
                    statusMessage.style.borderColor = '#e5e7eb';

                    if (mensagemRetorno.trim().toLowerCase().startsWith('\x3C!doctype') || mensagemRetorno.includes('\x3Chtml')) {
                        statusMessage.textContent = "Aviso operacional: Não foi possível gravar os dados. Certifique-se de que este CNPJ ou E-mail já não estão cadastrados.";
                    } else {
                        statusMessage.textContent = `Aviso operacional: ${mensagemRetorno}`;
                    }

                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.textContent = textoOriginalBotao;
                        submitBtn.style.opacity = "1";
                        submitBtn.style.cursor = "pointer";
                    }
                }
            } catch (error) {
                console.error('❌ Erro crítico no barramento:', error);
                statusMessage.style.color = '#000000';
                statusMessage.style.borderColor = '#e5e7eb';
                statusMessage.textContent = 'Erro de conexão: Não foi possível contatar o barramento de serviços.';

                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = textoOriginalBotao;
                    submitBtn.style.opacity = "1";
                    submitBtn.style.cursor = "pointer";
                }
            }
        });
    }
}

// --- Lógica para a página de Acesso/Login ---
if (document.getElementById('acesso-page')) {
    const form = document.getElementById('loginForm');
    const statusMessage = document.getElementById('loginStatusMessage');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        statusMessage.textContent = 'Verificando credenciais...';
        statusMessage.style.color = 'blue';

        const email = form.email.value;
        const codigo = form.codigo.value;

        try {

            // CORREÇÃO: Usamos window.location.origin para garantir que o fetch
            // use o host e a porta CORRETOS do Frontend (Ex: http://localhost:3001)
            const loginUrl = window.location.origin + '/login';
            // Chama a rota POST /login no seu próprio servidor Express (server.js)

            const response = await fetch(loginUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email, codigo: codigo })
            });

            // const result = await response.json();
            const text = await response.text();
            console.log("Resposta do servidor:", text); // Vai mostrar se é HTML de erro
            const result = JSON.parse(text); // Tenta converter depois


            if (response.ok && result.success) {
                statusMessage.textContent = 'Acesso concedido! Redirecionando...';
                statusMessage.style.color = 'green';
                // Redireciona o usuário para a página de avaliação (Fase 5)
                window.location.href = result.redirect;
            } else {
                statusMessage.textContent = result.message || 'Erro de autenticação.';
                statusMessage.style.color = 'red';
            }
        } catch (error) {
            console.error('Erro na submissão de login:', error);
            statusMessage.textContent = 'Erro de conexão.';
            statusMessage.style.color = 'red';
        }
    });
}

});

function parseQuestionGrad(rawValue) {
    if (rawValue === 'na' || rawValue === null || rawValue === undefined || rawValue === '') {
        return null;
    }
    const n = Number(rawValue);
    return Number.isNaN(n) ? null : n;
}
window.parseQuestionGrad = parseQuestionGrad;

async function finalizarEGerarDiagnosticoInicial(idMatu, btnEl) {
    console.log("[PONTO DE CONTROLE 1] Iniciando processamento para ID:", idMatu);

    const pre = window.panelDxAssessment?.getPresurveyState?.();
    if (pre && !pre.complete) {
        alert(
            `Faltam ${pre.total - pre.answered} questão(ões) na 1ª aba. ` +
            `Complete todas as ${pre.total} questões do diagnóstico inicial antes de gerar o relatório preliminar.`
        );
        return;
    }

    const btn = btnEl || (typeof event !== 'undefined' && event.target
        ? event.target.closest('button')
        : null);
    if (!btn) {
        alert('Não foi possível iniciar o processamento. Recarregue a página e tente novamente.');
        return;
    }
    const originalText = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando Análise...';

    try {
        const items = [...document.querySelectorAll('#step-0 .question-item')];
        if (!items.length) {
            throw new Error('Nenhuma questão encontrada na 1ª aba. Abra o modo detalhado.');
        }

        const answers = [];
        const missingLabels = [];

        for (const div of items) {
            const qId = div.dataset.questionId;
            const prefu = (div.dataset.prefu || 'P').toUpperCase();
            const selected = div.querySelector(`input[name="question-${qId}"]:checked`);
            const title = div.querySelector('h4')?.textContent?.trim().slice(0, 48) || `Q${qId}`;

            if (!selected) {
                missingLabels.push(`${prefu === 'F' ? 'Futuro' : 'Presente'} — ${title}`);
                continue;
            }

            const ta = div.querySelector('.quali-textarea');
            const payload = {
                id_matu: parseInt(idMatu, 10),
                id_ques: parseInt(qId, 10),
                grad_ques: parseQuestionGrad(selected.value),
                quali_ques: ta ? ta.value.trim() : '',
                id_dime: parseInt(div.dataset.dimId, 10),
                id_doma: parseInt(div.dataset.domaId, 10),
                prefu_ques: prefu,
            };

            const partialRes = await fetch(`${API_BASE_URL}/ctdi_surv/partial`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!partialRes.ok) {
                throw new Error(`Falha ao salvar questão ${qId} (${prefu}).`);
            }

            answers.push({
                id_ques: payload.id_ques,
                grad_ques: payload.grad_ques,
                quali_ques: payload.quali_ques,
                id_dime: payload.id_dime,
                id_doma: payload.id_doma,
                prefu_ques: payload.prefu_ques,
            });
        }

        if (missingLabels.length) {
            throw new Error(
                'Faltam respostas em:\n• ' + missingLabels.slice(0, 6).join('\n• ') +
                (missingLabels.length > 6 ? `\n… e mais ${missingLabels.length - 6}.` : '')
            );
        }

        const futuro = answers.filter(a => a.prefu_ques === 'F');
        const futuroComNota = futuro.filter(a => a.grad_ques !== null && a.grad_ques > 0);
        console.log('[PRESURVEY] Salvo — Presente:', answers.filter(a => a.prefu_ques === 'P').length,
            '| Futuro:', futuro.length, '| Futuro com nota > 0:', futuroComNota.length);

        if (futuro.length > 0 && futuroComNota.length === 0) {
            const prosseguir = window.confirm(
                'Todas as questões de FUTURO estão com nota 0 («Sem Previsão»). ' +
                'Se você marcou outras opções, volte ao modo detalhado e confira antes de continuar.\n\n' +
                'Gerar o relatório assim mesmo?'
            );
            if (!prosseguir) {
                btn.disabled = false;
                btn.innerHTML = originalText;
                return;
            }
        }

        console.log("[PONTO DE CONTROLE 2] Respostas sincronizadas:", answers.length, "questões.");

        const saveRes = await fetch(`${API_BASE_URL}/ctdi_surv`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_matu: parseInt(idMatu, 10), answers: answers, finalize: false })
        });
        if (!saveRes.ok) {
            throw new Error('Falha ao consolidar respostas antes do cálculo do relatório.');
        }

        // AQUI ESTÁ O TRABALHO DE INVESTIGAÇÃO
        console.log("[PONTO DE CONTROLE 3] Solicitando cálculo ao Flask via Node...");

        // Chamada relativa usando o prefixo do Node para garantir o recebimento no server.js
        const res = await fetch('/node/client/processar-presurvey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id_matu: idMatu })
        });

        const result = await res.json();

        // LOG CRÍTICO: O que o Flask respondeu após o cálculo?
        console.log("[PONTO DE CONTROLE 4] Resultado do processamento:", result);

        if (res.ok && result.success) {
            console.log("[PONTO DE CONTROLE 5] Sucesso! Redirecionando para o relatório...");
            // Pequeno delay para garantir que o banco persistiu antes do redirecionamento
            setTimeout(() => {
                window.location.href = `/diagnostico-inicial/${idMatu}`;
            }, 500);
        } else {
            throw new Error(result.error || "Falha no cálculo do Flask");
        }

    } catch (err) {
        console.error("[PONTO DE CONTROLE ERRO] Detalhes:", err);
        alert("Erro ao gerar diagnóstico: " + err.message);
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

