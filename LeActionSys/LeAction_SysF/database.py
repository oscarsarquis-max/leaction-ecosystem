import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor, execute_batch
import psycopg2.errors
import sys
from psycopg2.extras import NumericRange
import random
import string
import traceback


def generate_random_code(length=6):
    """Gera um código alfanumérico aleatório de 6 caracteres."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for i in range(length))


# -----------------------------------------------------------------------------------------
class LeactionCRUD:
    def __init__(self, dbname, user, password, host, port, sslmode=None):
        self.db_config = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port,
            'sslmode': sslmode
        }
        # self.conn não existe mais.

        self.join_definitions = {
            # ... (Suas definições de join mantidas) ...
            'ctdi_matu': {
                'joins': [
                    {'table': 'ctdi_clie', 'on_pk': 'id_clie', 'on_fk': 'id_clie'}
                ],
                'extra_selects': ['ctdi_clie_j.nome_clie AS nome_clie_text']
            },
            'leaf_bloc': {
                'joins': [
                    {'table': 'leaf_dime', 'on_pk': 'id_dime', 'on_fk': 'id_dime'},
                    {'table': 'leaf_doma', 'on_pk': 'id_doma', 'on_fk': 'id_doma'}
                ],
                'extra_selects': [
                    'leaf_dime_j.name_dime AS name_dime_text',
                    'leaf_doma_j.name_doma AS name_doma_text'
                ]
            },
            'ctdi_sprn': {
                'joins': [
                    {'table': 'leaf_bloc', 'on_pk': 'id_bloc', 'on_fk': 'id_bloc'}
                ],
                'extra_selects': ['leaf_bloc_j.name_bloc AS name_bloc_text']
            },
            'ctdi_surv': {
                'joins': [
                    {'table': 'ctdi_matu', 'on_pk': 'id_matu', 'on_fk': 'id_matu'},
                    {'table': 'ctdi_clie', 'on_pk': 'id_clie', 'on_fk': 'id_clie', 'via_table': 'ctdi_matu'},
                    {'table': 'leaf_dime', 'on_pk': 'id_dime', 'on_fk': 'id_dime'},
                    {'table': 'leaf_doma', 'on_pk': 'id_doma', 'on_fk': 'id_doma'},
                    {'table': 'ctdi_quest', 'on_pk': 'id_ques', 'on_fk': 'id_ques'}
                ],
                'extra_selects': [
                    'ctdi_clie_j.nome_clie AS nome_clie_text_from_matu',
                    'leaf_dime_j.name_dime AS name_dime_text',
                    'leaf_doma_j.name_doma AS name_doma_text',
                    'ctdi_quest_j.desc_ques AS desc_ques_text'
                ]
            },
            'ctdi_roun': {
                'joins': [
                    {'table': 'leaf_dime', 'on_pk': 'id_dime', 'on_fk': 'id_dime'}
                ],
                'extra_selects': ['leaf_dime_j.name_dime AS name_dime_text']
            },
            'bloc_derv': {
                'joins': [
                    {'table': 'leaf_bloc', 'on_pk': 'id_bloc', 'on_fk': 'id_bloc'},
                    {'table': 'leaf_derv', 'on_pk': 'id_derv', 'on_fk': 'id_derv'},
                    {'table': 'ctdi_movi', 'on_pk': 'id_movi', 'on_fk': 'id_movi'}

                ],
                'extra_selects': [
                    'leaf_bloc_j.name_bloc AS name_bloc_text',
                    'leaf_derv_j.name_derv AS name_derv_text',
                    'ctdi_movi_j.name_mov AS name_mov_text'
                ]
            },
            'ctdi_quest': {
                'joins': [
                    {'table': 'leaf_dime', 'on_pk': 'id_dime', 'on_fk': 'id_dime'},
                    {'table': 'leaf_doma', 'on_pk': 'id_doma', 'on_fk': 'id_doma'},
                    {'table': 'ctdi_bussola', 'on_pk': 'id_ques', 'on_fk': 'id_ques'}  # Adicione este Join
                ],
                'extra_selects': [
                    'leaf_dime_j.name_dime AS name_dime_text',
                    'leaf_doma_j.name_doma AS name_doma_text',
                    'ctdi_bussola_j.insight_chave',  # Traz o insight
                    'ctdi_bussola_j.target_context'  # Traz o context
                ]
            }
        }
        self.table_columns_cache = {}


    # 17/02/2026 Este método substitui o antigo connect da linha 12 é o que deve ser chamado
    # pelo app.py.
    def _connect_db(self):

        # try:
        #     # Tenta a conexão usando os dados do seu dicionário
        #     return psycopg2.connect(
        #         host=self.db_config.get('host') or "127.0.0.1",
        #         port=self.db_config.get('port') or "5432",
        #         database=self.db_config.get('dbname') or "LeAction_SysF",
        #         user=self.db_config.get('user') or "postgres",
        #         password=self.db_config.get('password'),
        #         sslmode=self.db_config.get('sslmode') or "prefer",
        #         connect_timeout=5,
        #         options="-c search_path=public -c lc_messages=en_US.UTF-8"
        #     )
        try:
            # Prioridade 1: Variável de ambiente (AWS)
            # Prioridade 2: Dicionário interno
            # Prioridade 3: Fallback (mas nunca 127.0.0.1 na nuvem!)
            import os
            db_host = os.getenv('DB_HOST') or self.db_config.get('host')

            return psycopg2.connect(
                host=db_host,
                port=os.getenv('DB_PORT') or self.db_config.get('port') or "5432",
                database=os.getenv('DB_NAME') or self.db_config.get('dbname') or "LeAction_SysF",
                user=os.getenv('DB_USER') or self.db_config.get('user') or "postgres",
                password=os.getenv('DB_PASS') or self.db_config.get('password'),
                sslmode=self.db_config.get('sslmode') or "prefer",
                connect_timeout=10,
                options="-c search_path=public -c lc_messages=en_US.UTF-8"
            )

        except Exception as e:
        # Pega a mensagem de erro de forma bruta (bytes) para evitar o crash do UTF-8

            try:
                # Tenta converter o erro para string ignorando o que não for UTF-8
                # Usamos o 'repr(e)' ou 'args' porque o 'str(e)' é o que causa o erro de codec
                msg_bruta = e.args[0] if e.args else str(e)

                if isinstance(msg_bruta, bytes):
                    msg_limpa = msg_bruta.decode('ascii', 'ignore')
                else:
                    msg_limpa = str(msg_bruta).encode('ascii', 'ignore').decode('ascii')
            except:
                msg_limpa = "Erro de conexao: Falha na autenticacao ou Banco inacessivel"

            print("\n" + "!" * 50)
            print(f"🚨 ERRO REAL DO POSTGRES: {msg_limpa}")
            print(f"📍 TENTATIVA EM: {self.db_config.get('host')}:{self.db_config.get('port')}")
            print("!" * 50 + "\n")

            raise ConnectionError(f"Falha ao conectar: {msg_limpa}")

    # --- Método Auxiliar para Conversão ---
    def _convert_record_to_serializable(self, record):
        """Converte tipos não serializáveis (como NumericRange) para strings."""
        if not record:
            return record

        if isinstance(record, dict):
            mutable_record = record
        elif hasattr(record, '__dict__'):
            mutable_record = record.__dict__
        else:
            mutable_record = dict(record)

        for key, value in mutable_record.items():
            if isinstance(value, NumericRange):
                mutable_record[key] = str(value)

        return mutable_record

    def convert_record_to_json_safe(self, record):
        """
        Método público para serializar registros do DB (JSONB, NumericRange, Decimal)
        antes de enviar ao Flask/Frontend.
        """
        return self._convert_record_to_serializable(record)

    # Assume-se que a assinatura do método é, por exemplo:
    # def get_table_columns(self, conn, table_name):

    def get_table_columns(self, conn, table_name):
        """
        Obtém os nomes das colunas de uma tabela e armazena em cache.
        Este método deve ser usado para operações de leitura.
        """

        # [REMOVIDO] O bloco 'if not self.conn: return []' é removido.
        # Confiamos que o Flask (get_db_conn) garantirá que 'conn' é uma conexão válida.

        # Verificação de cache:
        if table_name in self.table_columns_cache:
            return self.table_columns_cache[table_name]

        try:
            # AQUI É ONDE USAMOS O 'conn' RECEBIDO
            with conn.cursor() as cur:
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s;", (table_name,))
                columns = [row[0] for row in cur.fetchall()]
                self.table_columns_cache[table_name] = columns
                return columns

        except (Exception, psycopg2.Error) as error:
            # Nota: Não há commit/rollback necessário aqui, pois é uma operação SELECT.
            print(f"Erro ao obter colunas da tabela {table_name}:", error, file=sys.stderr)
            return []

        # Nota: O fechamento da conexão (conn.close()) é tratado pelo @app.teardown_request do Flask.

    def _build_select_query(self, table_name, base_alias='main'):
        select_parts = [f"{base_alias}.*"]
        join_parts = []
        table_joins = self.join_definitions.get(table_name, {})
        current_aliases = {table_name: base_alias}

        for join_def in table_joins.get('joins', []):
            join_table = join_def['table']
            on_pk = join_def['on_pk']
            on_fk = join_def['on_fk']
            via_table = join_def.get('via_table')

            join_alias = f"{join_table}_j"
            current_aliases[join_table] = join_alias

            from_alias = base_alias
            if via_table and via_table in current_aliases:
                from_alias = current_aliases[via_table]

            join_parts.append(f"LEFT JOIN {join_table} AS {join_alias} ON {from_alias}.{on_fk} = {join_alias}.{on_pk}")

        select_parts.extend(table_joins.get('extra_selects', []))
        return f"SELECT {', '.join(select_parts)} FROM {table_name} AS {base_alias} {' '.join(join_parts)}", current_aliases

    def _get_pk_column(self, table_name):
        """Método auxiliar para obter o nome da coluna da chave primária de forma mais robusta."""
        if table_name == 'ctdi_quest':
            return 'id_ques'
        else:
            return f"id_{table_name.split('_')[-1].lower()}"

    def read_all_records(self, conn, table_name):
        """
        Lê todos os registros de uma tabela, incluindo JOINS se definidos.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """

        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido,
        # pois a conexão 'conn' é garantida pelo app.py.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. USAR A CONEXÃO RECEBIDA (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query_str, _ = self._build_select_query(table_name)
            cur.execute(query_str)
            records = cur.fetchall()

            return [self._convert_record_to_serializable(r) for r in records]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao ler todos os registros da tabela {table_name}:", error, file=sys.stderr)
            # [REMOVIDO] conn.rollback() é removido, pois SELECTs não alteram o estado transacional.
            return []

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def search_records(self, conn, table_name, search_query):
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try
        try:
            # 1. USAR A CONEXÃO RECEBIDA (conn) para obter o cursor
            cur = conn.cursor(cursor_factory=RealDictCursor)

            base_query_str, _ = self._build_select_query(table_name)

            # 2. FIX CRÍTICO: PASSAR 'conn' para o método auxiliar.
            # (Se _get_table_columns faz um SELECT, ele precisa da conexão ativa)
            table_columns = self.get_table_columns(conn, table_name)

            search_target_columns = [
                f"main.{col}" for col in table_columns
            ]

            # ... (restante da lógica de construção de query, que é complexa e está correta) ...

            table_joins = self.join_definitions.get(table_name, {})
            for select_expr in table_joins.get('extra_selects', []):
                col_ref = select_expr.split(' AS ')[0].strip()
                search_target_columns.append(col_ref)

            search_conditions = [
                f"CAST({col_ref} AS TEXT) ILIKE %s" for col_ref in search_target_columns
            ]

            sql_params = [f"%{search_query}%"] * len(search_conditions)

            if search_conditions:
                query_str = f"{base_query_str} WHERE {' OR '.join(search_conditions)};"
            else:
                query_str = f"{base_query_str};"

            cur.execute(query_str, sql_params)
            records = cur.fetchall()

            return [self._convert_record_to_serializable(r) for r in records]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao buscar registros na tabela {table_name}:", error, file=sys.stderr)

            # 3. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT/SEARCH.
            return []

        finally:
            if cur: cur.close()

    def create_record(self, conn, table_name, data):
        """
        Cria um registro genérico na tabela especificada.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        cur = None
        try:
            # USAR A CONEXÃO RECEBIDA
            cur = conn.cursor()

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))

            # _get_pk_column é apenas um helper de texto, não acessa o banco.
            pk_col = self._get_pk_column(table_name)

            # get_table_columns acessa o banco, então PRECISA do conn.
            all_columns = self.get_table_columns(conn, table_name)

            if pk_col in all_columns:
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING {pk_col};"
            else:
                query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"

            cur.execute(query, tuple(data.values()))

            new_id = None
            if cur.description:
                new_id = cur.fetchone()[0]

            # Commit na conexão recebida
            conn.commit()

            return new_id

        # except (Exception, psycopg2.Error) as error:
        #     print(f"Erro ao criar registro na tabela {table_name}:", error, file=sys.stderr)
        #
        #     # Rollback na conexão recebida
        #     conn.rollback()
        #     return None
        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao criar registro na tabela {table_name}:", error, file=sys.stderr)

            # Rollback na conexão recebida
            conn.rollback()

            # O SEGREDO ESTÁ AQUI:
            # O 'raise' faz o erro continuar subindo para o arquivo principal
            raise error

        finally:
            if cur: cur.close()

    # Fluxo para que a inserção de dados do questionário seja feita em massa (BULK INSERT),
    # dentro de uma única transação. 1 único COMMIT.
    def create_multiple_survey_records(self, conn, answers_data):
        """
        Insere múltiplos registros na tabela ctdi_surv em uma única transação (bulk insert).
        Agora suporta o campo PREFU_QUES ('P' ou 'F').
        """
        cursor = None
        try:
            cursor = conn.cursor()

            # 2. Monta a lista de tuplas de valores (AGORA INCLUI PREFU_QUES)
            values_list = []
            for answer in answers_data:
                # O get() é usado para segurança, embora o Front-end deva garantir o envio.

                values_list.append((
                    answer['ID_MATU'],
                    answer['ID_QUES'],
                    answer['ID_DIME'],
                    answer['ID_DOMA'],
                    answer['GRAD_QUES'],
                ))

            # 3. Query de Inserção
            query = """
                INSERT INTO ctdi_surv (ID_MATU, ID_QUES, ID_DIME, ID_DOMA, GRAD_QUES)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ID_MATU, ID_QUES) DO UPDATE
                SET 
                    GRAD_QUES = EXCLUDED.GRAD_QUES,
                    ID_DIME = EXCLUDED.ID_DIME,
                    ID_DOMA = EXCLUDED.ID_DOMA;
                """

            # 4. Executa a inserção em massa
            psycopg2.extras.execute_batch(cursor, query, values_list)

            conn.commit()

            return True

        except Exception as e:
            conn.rollback()

            print("--- ERRO CRÍTICO NA INSERÇÃO (DB MANAGER) ---", file=sys.stderr)
            print(f"Erro de DB: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)  # Imprime o erro detalhado

            # É crucial ver o erro real no log do servidor
            print(f"Erro ao criar múltiplos registros em ctdi_surv (com PREFU_QUES): {e}", file=sys.stderr)
            return False
        finally:
            if cursor:
                cursor.close()

    def read_record_by_id(self, conn, table_name, record_id):
        """
        Lê um único registro de uma tabela usando a chave primária.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. USAR A CONEXÃO RECEBIDA (conn) para obter o cursor
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # 2. FIX CRÍTICO: Passar 'conn' para o método auxiliar (se necessário)
            # Assumindo que _get_pk_column precisa de conn:
            pk_col = self._get_pk_column(table_name)

            # Assume-se que _build_select_query não precisa de conn se usa cache local
            base_query_str, _ = self._build_select_query(table_name)

            query_str = f"{base_query_str} WHERE main.{pk_col} = %s;"

            cur.execute(query_str, (record_id,))
            record = cur.fetchone()

            return self._convert_record_to_serializable(record)

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao ler registro na tabela {table_name} com ID {record_id}:", error, file=sys.stderr)

            # 3. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT.
            # A exceção deve ser levantada para ser tratada pelo Flask.
            raise

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def update_record(self, conn, table_name, record_id, data):
        """
        Atualiza um registro genérico na tabela especificada.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. Cursor é obtido da conexão recebida
            cur = conn.cursor()

            if table_name == 'ctdi_movi' and 'INTV_MOVI' in data:
                pass  # Lógica de negócio mantida

            set_clauses = [f"{key} = %s" for key in data.keys()]

            # 2. FIX CRÍTICO: Passar 'conn' para o método auxiliar
            pk_col = self._get_pk_column(table_name)

            query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {pk_col} = %s;"
            values = list(data.values()) + [record_id]

            cur.execute(query, tuple(values))

            # 3. MUDANÇA: Commit na conexão recebida
            conn.commit()

            return cur.rowcount > 0

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao atualizar registro {record_id} na tabela {table_name}:", error, file=sys.stderr)

            # 4. Rollback na conexão recebida (Correto para transações)
            conn.rollback()
            return False

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def delete_record(self, conn, table_name, record_id):
        """
        Deleta um registro na tabela especificada.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. Cursor é obtido da conexão recebida
            cur = conn.cursor()

            pk_col = self._get_pk_column(table_name)

            query = f"DELETE FROM {table_name} WHERE {pk_col} = %s;"
            cur.execute(query, (record_id,))

            if cur.rowcount > 0:
                # 3. MUDANÇA: Commit na conexão recebida
                conn.commit()
                return True
            else:
                # Rollback se a deleção não afetou linhas (não é estritamente necessário, mas limpa o estado)
                conn.rollback()
                return False

        except psycopg2.errors.ForeignKeyViolation:
            # 4. Rollback na conexão recebida
            conn.rollback()
            # Levanta a exceção novamente para ser tratada pela rota
            raise

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao deletar registro {record_id} na tabela {table_name}:", error, file=sys.stderr)
            # 5. Rollback na conexão recebida
            conn.rollback()
            # Levanta a exceção novamente
            raise

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def create_maturity_record(self, conn, id_clie):
        """
        Cria o registro em ctdi_matu, inicializando os 9 scores Gerais e os 9 Scores Setoriais.
        Retorna o ID da nova maturidade.
        """
        cur = None
        try:
            cur = conn.cursor()

            # 1. Verificação de Cliente
            query_check_client = "SELECT COUNT(*) FROM ctdi_clie WHERE ID_CLIE = %s;"
            cur.execute(query_check_client, (id_clie,))
            if cur.fetchone()[0] == 0:
                raise ValueError("O ID_CLIE fornecido não existe.")

            # 2. Inserção com os novos campos (Setoriais)
            insert_query = """
                           INSERT INTO ctdi_matu (id_clie,
                               -- SCORES GERAIS \
                                                  pdom_pres, pdim_pres, pgen_pres, \
                                                  pdom_fut, pdim_fut, pgen_fut, \
                                                  pdom_gap, pdim_gap, pgen_gap,
                               -- SCORES SETORIAIS (EDUCAÇÃO) \
                                                  pdom_sect_pres, pdim_sect_pres, pgen_sect_pres, \
                                                  pdom_sect_fut, pdim_sect_fut, pgen_sect_fut, \
                                                  pdom_sect_gap, pdim_sect_gap, pgen_sect_gap)
                           VALUES (%s,
                                      -- Inicialização Geral \
                                   '{}'::JSONB, '{}'::JSONB, 0.00, \
                                   '{}'::JSONB, '{}'::JSONB, 0.00, \
                                   '{}'::JSONB, '{}'::JSONB, 0.00,
                                      -- Inicialização Setorial \
                                   '{}'::JSONB, '{}'::JSONB, 0.00, \
                                   '{}'::JSONB, '{}'::JSONB, 0.00, \
                                   '{}'::JSONB, '{}'::JSONB, 0.00) RETURNING id_matu; \
                           """

            cur.execute(insert_query, (id_clie,))
            new_id = cur.fetchone()[0]

            conn.commit()
            return new_id

        except psycopg2.errors.ForeignKeyViolation as e:
            conn.rollback()
            raise e
        except Exception as e:
            conn.rollback()
            print(f"Erro ao criar registro de maturidade: {e}", file=sys.stderr)
            return None
        finally:
            if cur: cur.close()
    # -----------------------------------------------------------------------------------------
    # MÉTODOS DE LEAD CAPTURE E AUTENTICAÇÃO (FASE 3 & 6)
    # -----------------------------------------------------------------------------------------

    def create_lead_client_maturity(self, conn, lead_data):
        """
        Cria o registro em CTDI_CLIE, CTDI_MATU (TRAVADO) e CTDI_LEAD_ACCESS.
        Todos os campos e status em MAIÚSCULAS.
        """
        cur = None
        try:
            cur = conn.cursor()

            # 1. Gerar Código de Acesso
            access_code = generate_random_code()

            # 2. Inserir na CTDI_CLIE
            query_client = """
                           INSERT INTO CTDI_CLIE (NOME_CLIE, MAIL_CLIE, DOCU_CLIE, FONE_CLIE, EMPRESA_CLIE)
                           VALUES (%s, %s, %s, %s, %s) \
                           RETURNING ID_CLIE;
                           """
            cur.execute(query_client, (
                lead_data.get('NOME_CLIE'),
                lead_data.get('MAIL_CLIE'),
                lead_data.get('DOCU_CLIE'),
                lead_data.get('FONE_CLIE'),
                lead_data.get('EMPRESA_CLIE')
            ))
            id_clie = cur.fetchone()[0]

            # 3. Inserir na CTDI_MATU (STATUS_IA COMO 'AGUARDANDO CONTEXTO')
            # Mantendo as colunas de scores conforme sua tabela
            query_matu = """
                         INSERT INTO CTDI_MATU (ID_CLIE, \
                                                STATUS_IA, \
                                                PDOM_PRES, PDIM_PRES, PGEN_PRES, \
                                                PDOM_FUT, PDIM_FUT, PGEN_FUT, \
                                                PDOM_GAP, PDIM_GAP, PGEN_GAP)
                         VALUES (%s, %s, '{}'::JSONB, '{}'::JSONB, 0.00, '{}'::JSONB, '{}'::JSONB, 0.00, '{}'::JSONB, \
                                 '{}'::JSONB, 0.00)
                         RETURNING ID_MATU;
                         """
            # Valor de status em MAIÚSCULAS para o Worker ignorar
            cur.execute(query_matu, (id_clie, 'AGUARDANDO CONTEXTO'))
            id_matu = cur.fetchone()[0]

            # 4. Inserir na CTDI_LEAD_ACCESS
            query_access = """
                           INSERT INTO CTDI_LEAD_ACCESS (ID_CLIE, ACCESS_CODE)
                           VALUES (%s, %s);
                           """
            cur.execute(query_access, (id_clie, access_code))

            conn.commit()
            return id_clie, access_code

        except psycopg2.Error as e:
            if conn: conn.rollback()
            print(f"ERRO SQL EM CREATE_LEAD_CLIENT_MATURITY: {e}")
            raise Exception(f"FALHA NA TRANSAÇÃO DE CRIAÇÃO DE LEAD: {e}")
        finally:
            if cur: cur.close()

    def read_client_by_email_and_code(self, conn, email, access_code):
        """
        Verifica se existe um cliente com o email e código de acesso ativo,
        e retorna seus dados (ID_CLIE e ID_MATU).
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # Busca o cliente e o ID_MATU associado ao código de acesso.
            query = """
                    SELECT c.ID_CLIE, m.ID_MATU, c.NOME_CLIE
                    FROM CTDI_CLIE AS c
                             JOIN CTDI_LEAD_ACCESS AS a ON c.ID_CLIE = a.ID_CLIE
                             JOIN CTDI_MATU AS m ON c.ID_CLIE = m.ID_CLIE
    
                    -- CORREÇÃO FINAL: Força a comparação de minúsculas
                    WHERE LOWER(c.MAIL_CLIE) = LOWER(%s)
                      AND LOWER(a.ACCESS_CODE) = LOWER(%s)
    
                    ORDER BY a.CREATED_AT DESC LIMIT 1;
                    """

            cur.execute(query, (email.lower(), access_code.lower()))
            record = cur.fetchone()

            return self._convert_record_to_serializable(record)

        except Exception as e:
            print(f"Erro ao buscar cliente por e-mail e código: {e}", file=sys.stderr)
            # 2. [REMOVIDO] Não é necessário rollback em SELECT
            return None
        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def read_questions_structured_for_evaluation(self, conn):
        """
        Lê todas as questões estruturadas e anexa as rubricas (0 a 5) a cada uma.
        Busca o insight_chave diretamente da tabela ctdi_bussola.
        """
        cur = None
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 1. Busca as questões com Joins de Dimensão, Domínio e Bússola
            # MUDANÇA: Adicionado o LEFT JOIN com ctdi_bussola para pegar o insight_chave
            query_ques = """
                         SELECT q.id_ques,
                                q.desc_ques,
                                q.id_dime,
                                q.id_doma,
                                q.prefu_ques,
                                q.setor_ques,
                                q.presurvey_ques,
                                q.quali_ques,
                                b.insight_chave,
                                dime.name_dime,
                                doma.name_doma
                         FROM ctdi_quest AS q
                                  LEFT JOIN leaf_dime AS dime ON q.id_dime = dime.id_dime
                                  LEFT JOIN leaf_doma AS doma ON q.id_doma = doma.id_doma
                                  LEFT JOIN ctdi_bussola AS b ON q.id_ques = b.id_ques
                         ORDER BY q.id_ques;
                         """
            cur.execute(query_ques)
            questions = cur.fetchall()

            if not questions:
                return []

            # 2. Busca TODAS as rubricas dessas questões em UMA única query
            ids_ques = tuple(q['id_ques'] for q in questions)
            query_rubr = """
                         SELECT id_ques, grad_rubr, label_rubr, desc_rubr
                         FROM public.ctdi_rubricas
                         WHERE id_ques IN %s
                         ORDER BY id_ques, grad_rubr ASC; \
                         """
            cur.execute(query_rubr, (ids_ques,))
            all_rubrics = cur.fetchall()

            # 3. Agrupa as rubricas por ID da questão
            rubrics_map = {}
            for r in all_rubrics:
                qid = r['id_ques']
                if qid not in rubrics_map:
                    rubrics_map[qid] = []
                rubrics_map[qid].append(r)

            # 4. Injeta as rubricas dentro de cada objeto questão
            for q in questions:
                q['rubricas'] = rubrics_map.get(q['id_ques'], [])

            return questions

        except (Exception, psycopg2.Error) as error:
            print("Erro ao ler as questões com rubricas e bússola:", error, file=sys.stderr)
            return []
        finally:
            if cur: cur.close()

    # Método para buscar notas salvas
    def read_surveys_by_maturity(self, conn, id_matu):
        """
        Lê todas as notas de questionário (survey records) para uma dada maturidade,
        incluindo o campo prefu_ques da tabela de questões para segregação (Presente/Futuro).
        """
        cur = None
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)

            # MUDANÇA CRÍTICA: Uso de JOIN para obter o campo prefu_ques da ctdi_quest
            query = """
                    SELECT s.id_ques, \
                           s.grad_ques, \
                           s.id_dime, \
                           s.id_doma, \
                           q.prefu_ques -- <--- CAMPO CRÍTICO ADICIONADO AQUI
                    FROM ctdi_surv s
                             JOIN ctdi_quest q ON s.id_ques = q.id_ques
                    WHERE s.id_matu = %s;
                    """
            cur.execute(query, (id_matu,))
            records = cur.fetchall()

            return records

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao ler notas para a maturidade {id_matu}: {error}", file=sys.stderr)
            return []

        finally:
            if cur: cur.close()

    def get_movement_by_score(self, conn, score):
        """
        Busca o Movimento (ctdi_movi) cujo intervalo (intv_movi) inclui o score geral.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT *
                    FROM ctdi_movi
                    WHERE intv_movi @> %s::numeric
                    LIMIT 1;
                    """

            # Converte o score para um tipo compatível com o operador @> (contains)
            cur.execute(query, (score,))
            record = cur.fetchone()

            # O _convert_record_to_serializable garante que o NumericRange seja tratado
            return self._convert_record_to_serializable(record)

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao buscar movimento pelo score {score}:", error, file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT.
            return None

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def get_benchmark_by_sector(self, conn, sector_name):
        """
        Busca todos os dados de benchmarking (ctdi_refb) para um setor específico.
        Corrigido para fazer JOIN com ctdi_movi e retornar o nome do estágio.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT ref.id_dime,
                           ref.id_doma,
                           ref.grad_refb,
                           d.name_dime,
                           dm.name_doma,
                           m.name_movi AS estagio_refb
                    FROM ctdi_refb AS ref
                             JOIN leaf_dime AS d ON ref.id_dime = d.id_dime
                             JOIN leaf_doma AS dm ON ref.id_doma = dm.id_doma
                             JOIN ctdi_movi AS m ON ref.id_movi = m.id_movi
                    WHERE ref.setr_refb = %s;
                    """
            cur.execute(query, (sector_name,))
            records = cur.fetchall()

            return [self._convert_record_to_serializable(record) for record in records]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao buscar benchmark para o setor {sector_name}:", error, file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT.
            return None

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def get_all_blocks_mapping(self, conn):
        """
        Busca todos os Blocos e suas associações (id_dime, id_doma).
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT ID_BLOC, NAME_BLOC, DESC_BLOC, ID_DIME, ID_DOMA
                    FROM LEAF_BLOC;
                    """
            cur.execute(query)
            records = cur.fetchall()

            return [self._convert_record_to_serializable(r) for r in records]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao buscar o mapeamento de blocos:", error, file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT.
            return []

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def get_all_benchmark_ranges_by_domain(self, conn, id_doma):
        """
        Busca todos os intervalos de benchmark (grad_refb) associados a um Domínio específico.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT grad_refb
                    FROM ctdi_refb
                    WHERE id_doma = %s;
                    """
            cur.execute(query, (id_doma,))
            records = cur.fetchall()

            return [r['grad_refb'] for r in records if r.get('grad_refb')]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao buscar ranges para o Domínio {id_doma}:", error, file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Rollback é desnecessário em operações SELECT.
            return []

        finally:
            # Garante que o cursor seja fechado
            if cur: cur.close()

    def read_all_maturities_with_client_name(self, conn):
        """
        Lê todos os registros de maturidade e faz JOIN com clientes
        para retornar o nome e o e-mail do cliente. Usado para a lista de Admin.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cursor = None  # Inicializa para o finally
        try:
            # 1. MUDANÇA CRÍTICA: Inicializa o cursor DENTRO do try usando 'conn'
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT t1.*,
                           t2.nome_clie,
                           t2.mail_clie AS mail_clie_text
                    FROM ctdi_matu t1
                             JOIN ctdi_clie t2 ON t1.id_clie = t2.id_clie
                    ORDER BY t1.id_matu DESC;
                    """
            cursor.execute(query)
            records = cursor.fetchall()

            # Garante que os registros sejam serializáveis
            serialized_records = [self._convert_record_to_serializable(record) for record in records]

            return serialized_records

        except Exception as e:
            print(f"Erro ao buscar todas as maturidades com nome do cliente: {e}", file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Desnecessário em SELECT.
            return []
        finally:
            # Garante que o cursor seja fechado
            if cursor: cursor.close()


    # --- [ATENÇÃO] Métodos específicos para o microsserviço de cálculo [ATENÇÃO]---
    # --- [ATENÇÃO] Métodos específicos para o microsserviço de cálculo [ATENÇÃO]---
    # --- [ATENÇÃO] Métodos específicos para o microsserviço de cálculo [ATENÇÃO]---
    # --- [ATENÇÃO] Métodos específicos para o microsserviço de cálculo [ATENÇÃO]---

    def execute_query(self, conn, query, params=None):
        """
        Método genérico para executar uma consulta SELECT.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

        except (Exception, psycopg2.Error) as error:
            print("Erro ao executar query:", error, file=sys.stderr)
            # 2. [REMOVIDO] conn.rollback() - Rollback é desnecessário em SELECT.
            return None

    def execute_update(self, conn, query, params=None):
        """
        Método genérico para executar UPDATE/INSERT/DELETE.
        Usa a conexão (conn) fornecida pelo escopo da requisição do Flask.
        """
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        try:
            # 1. Cursor é obtido da conexão recebida (correto)
            with conn.cursor() as cur:
                cur.execute(query, params)

                # 2. MUDANÇA: Commit na conexão recebida (conn)
                conn.commit()

                print(f"[DB UPDATE] Linhas afetadas: {cur.rowcount}", file=sys.stderr)
                return cur.rowcount > 0

        except (Exception, psycopg2.Error) as error:
            print("Erro ao executar update:", error, file=sys.stderr)
            # 3. Rollback na conexão recebida (Correto)
            conn.rollback()
            return False

    def get_survey_answers_by_maturity_id(self, conn, id_matu):
        # MUDANÇA 1: Adicionar 'conn' à assinatura

        query = "SELECT id_ques, grad_ques, id_dime, id_doma FROM ctdi_surv WHERE id_matu = %s;"

        # MUDANÇA 2: Passar 'conn' para o método auxiliar
        return self.execute_query(conn, query, (id_matu,))

    # Adicionar outras dependências necessárias
    def update_maturity_scores(self, conn, id_matu,
                               # SCORES GERAIS (Existentes)
                               pdom_pres, pdim_pres, pgen_pres,
                               pdom_fut, pdim_fut, pgen_fut,
                               pdom_gap, pdim_gap, pgen_gap,
                               # SCORES SETORIAIS / EDUCAÇÃO (Novos)
                               pdom_sect_pres, pdim_sect_pres, pgen_sect_pres,
                               pdom_sect_fut, pdim_sect_fut, pgen_sect_fut,
                               pdom_sect_gap, pdim_sect_gap, pgen_sect_gap):
        """
        Atualiza todos os 18 scores (Geral + Setorial) e sinaliza para o Worker que um novo diagnóstico é necessário.
        """

        # GARANTIA DE CONVERSÃO: Converte id_matu para int
        id_matu_int = int(id_matu) if isinstance(id_matu, (str, float)) else id_matu

        # 1. ATUALIZAMOS A QUERY PARA INCLUIR OS CAMPOS SETORIAIS E O STATUS_IA
        query = """
                UPDATE ctdi_matu
                SET
                    -- GERAL: Scores de PRESENTE
                    pdom_pres          = %s,
                    pdim_pres          = %s,
                    pgen_pres          = %s,
                    -- GERAL: Scores de FUTURO
                    pdom_fut           = %s,
                    pdim_fut           = %s,
                    pgen_fut           = %s,
                    -- GERAL: Scores de GAP
                    pdom_gap           = %s,
                    pdim_gap           = %s,
                    pgen_gap           = %s,

                    -- SETORIAL: Scores de PRESENTE (Novos)
                    pdom_sect_pres     = %s,
                    pdim_sect_pres     = %s,
                    pgen_sect_pres     = %s,
                    -- SETORIAL: Scores de FUTURO (Novos)
                    pdom_sect_fut      = %s,
                    pdim_sect_fut      = %s,
                    pgen_sect_fut      = %s,
                    -- SETORIAL: Scores de GAP (Novos)
                    pdom_sect_gap      = %s,
                    pdim_sect_gap      = %s,
                    pgen_sect_gap      = %s,

                    -- GATILHO PARA O WORKER DA IA
                    status_ia          = 'AVALIACAO OK', 
                    txt_diagnostico_ia = 'Aguardando Ativação (ActionHub)',
                    dt_fim_ia          = NOW() -- É bom atualizar a data de modificação
                WHERE id_matu = %s;
                """

        # 2. Tupla de parâmetros atualizada (18 scores + ID)
        params = (
            # Geral
            pdom_pres, pdim_pres, pgen_pres,
            pdom_fut, pdim_fut, pgen_fut,
            pdom_gap, pdim_gap, pgen_gap,
            # Setorial
            pdom_sect_pres, pdim_sect_pres, pgen_sect_pres,
            pdom_sect_fut, pdim_sect_fut, pgen_sect_fut,
            pdom_sect_gap, pdim_sect_gap, pgen_sect_gap,
            # ID (Where clause)
            id_matu_int
        )

        # 3. Execução via método da classe (Mantendo seu padrão)
        return self.execute_update(conn, query, params)


    def check_maturity_record_exists(self, conn, id_matu):
        """Verifica se um registro de maturidade existe."""
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        try:
            # A conexão 'conn' é usada corretamente no bloco 'with'
            with conn.cursor() as cur:
                query = "SELECT EXISTS(SELECT 1 FROM ctdi_matu WHERE id_matu = %s);"
                cur.execute(query, (id_matu,))
                return cur.fetchone()[0]

        except (Exception, psycopg2.Error) as error:
            print(f"Erro ao verificar a existência do registro de maturidade {id_matu}: {error}", file=sys.stderr)
            # [REMOVIDO] conn.rollback() - Rollback é desnecessário em SELECT.
            return False

    def get_questions_mapping(self, conn):  # <--- MUDANÇA 1: Adicionar 'conn'
        query = """
                SELECT q.id_ques, d.name_dime, dm.name_doma
                FROM ctdi_quest AS q
                         JOIN leaf_dime AS d ON q.id_dime = d.id_dime
                         JOIN leaf_doma AS dm ON q.id_doma = dm.id_doma;
                """
        # MUDANÇA 2: Passar 'conn' para o método auxiliar
        records = self.execute_query(conn, query)

        if not records:
            return {}
        return {item['id_ques']: item for item in records}

    def find_full_lead_by_email(self, conn, email):
        """Busca um cliente existente, sua maturidade e seu código de acesso."""
        # [REMOVIDO] O bloco 'if not self.conn: ...' é removido.

        cur = None  # Inicializa o cursor fora do try para o finally
        try:
            # 1. MUDANÇA: Usar a conexão recebida (conn)
            cur = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                    SELECT c.ID_CLIE,
                           m.ID_MATU,
                           a.ACCESS_CODE
                    FROM ctdi_clie c
                             JOIN
                         ctdi_matu m ON c.id_clie = m.id_clie
                             JOIN
                         ctdi_lead_access a ON c.id_clie = a.id_clie
                    WHERE LOWER(c.MAIL_CLIE) = LOWER(%s)
                    ORDER BY a.CREATED_AT DESC LIMIT 1; \
                    """
            cur.execute(query, (email,))
            result = cur.fetchone()

            return result

        except Exception as e:
            # Mantém o comportamento de falha silenciosa (retorna None)
            return None

        finally:
            # 2. MUDANÇA: Garante que o cursor feche, independentemente do sucesso
            if cur: cur.close()

    # =======================================================================================================
    # Tratamento da IA ======================================================================================
    # =======================================================================================================
    # def buscar_dados_para_ia(self, id_matu):
    #     """Busca os gaps de maturidade usando a lógica de conexão da classe."""
    #     conn = self._connect_db()  # Utiliza o seu método existente
    #     try:
    #         # Usando RealDictCursor para retornar dados como dicionário (chave: valor)
    #         with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
    #             query = """
    #                     SELECT dim_nome, blc_nome, matu_as_is, refb_nota
    #                     FROM sua_tabela_real
    #                     WHERE id_matu = %s
    #                     ORDER BY (refb_nota - matu_as_is) DESC LIMIT 3 \
    #                     """
    #             cur.execute(query, (id_matu,))
    #             return cur.fetchall()
    #     finally:
    #         conn.close()  # Garante que a conexão seja fechada
    #         print("Conexão com o banco fechada após busca da IA.")

    def get_survey_pain_points(self, conn, id_matu):
        """
        Busca as questões específicas onde o cliente teve as PIORES notas.
        """
        query = """
                SELECT d.name_doma AS dominio,
                       q.desc_ques AS pergunta_foco,
                       s.grad_ques AS nota_dada
                FROM ctdi_surv s
                         JOIN ctdi_quest q ON s.id_ques = q.id_ques
                         JOIN leaf_doma d ON s.id_doma = d.id_doma
                WHERE s.id_matu = %s
                ORDER BY s.grad_ques ASC LIMIT 10
                """
        try:
            with conn.cursor() as cur:
                cur.execute(query, (id_matu,))
                rows = cur.fetchall()

                if not rows:
                    return "Nenhuma resposta detalhada encontrada."

                pain_points = ""
                for row in rows:
                    dominio = row[0]
                    pergunta = row[1]
                    nota = row[2]
                    pain_points += f"- [Domínio: {dominio}] Questão Crítica: '{pergunta}' (Nota do Cliente: {nota})\n"

                return pain_points

        except Exception as e:
            print(f"⚠️ Erro ao minerar ctdi_surv: {e}")
            return "Dados qualitativos indisponíveis devido a erro técnico."

    #Modificação dos formulários para inclusão de rubricas...06/04/2026
    def read_questions_with_rubrics(self, conn, id_dime=None, setor=None):
        """
        Busca as questões estruturadas e anexa as 5 rubricas de 0 a 5 a cada uma.
        Implementa Eager Loading para performance.
        """
        cur = None
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 1. Busca as questões (Baseado no seu read_questions_structured_for_evaluation)
            query_ques = """
                         SELECT q.id_ques, \
                                q.desc_ques, \
                                q.id_dime, \
                                q.id_doma, \
                                q.prefu_ques, \
                                q.setor_ques,
                                dime.name_dime, \
                                doma.name_doma
                         FROM ctdi_quest AS q
                                  LEFT JOIN leaf_dime AS dime ON q.id_dime = dime.id_dime
                                  LEFT JOIN leaf_doma AS doma ON q.id_doma = doma.id_doma
                         WHERE 1 = 1 \
                         """
            params = []
            if id_dime:
                query_ques += " AND q.id_dime = %s"
                params.append(id_dime)
            if setor:
                query_ques += " AND q.setor_ques = %s"
                params.append(setor)

            query_ques += " ORDER BY q.id_ques"
            cur.execute(query_ques, tuple(params))
            questions = cur.fetchall()

            if not questions:
                return []

            # 2. Busca todas as rubricas para estas questões em uma única query
            ids_ques = tuple(q['id_ques'] for q in questions)
            query_rubr = """
                         SELECT id_ques, grad_rubr, label_rubr, desc_rubr
                         FROM public.ctdi_rubricas
                         WHERE id_ques IN %s
                         ORDER BY id_ques, grad_rubr ASC \
                         """
            cur.execute(query_rubr, (ids_ques,))
            all_rubrics = cur.fetchall()

            # 3. Mapeia as rubricas para as questões
            rubrics_map = {}
            for r in all_rubrics:
                qid = r['id_ques']
                if qid not in rubrics_map:
                    rubrics_map[qid] = []
                rubrics_map[qid].append(r)

            # 4. Injeta as rubricas no dicionário da questão
            for q in questions:
                # Garante que o objeto seja serializável como os outros métodos da classe
                q['rubricas'] = rubrics_map.get(q['id_ques'], [])

            return questions

        except Exception as e:
            print(f"Erro ao buscar questões com rubricas: {e}", file=sys.stderr)
            return []
        finally:
            if cur: cur.close()