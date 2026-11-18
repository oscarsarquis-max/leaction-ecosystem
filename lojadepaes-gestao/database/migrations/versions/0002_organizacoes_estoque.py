"""organizacoes, membros e estoque (ingredientes, itens, lotes, movimentos, entradas)

Revision ID: 0002_organizacoes_estoque
Revises: 0001_usuarios_sessoes
Create Date: 2026-11-02

- O usuário `oscar` passa a ser `admin_plataforma`, sem organização.
- O papel sai de `usuarios` e passa a viver em `membros` (um por organização).
- Toda tabela operacional tem `organizacao_id NOT NULL`.
- `movimentos` é imutável: um trigger recusa UPDATE e DELETE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002_organizacoes_estoque"
down_revision: Union[str, None] = "0001_usuarios_sessoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _org() -> sa.Column:
    return sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False)


def _agora(nome: str = "criado_em") -> sa.Column:
    return sa.Column(nome, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "organizacoes",
        _pk(),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("nome_curto", sa.String(40), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("fonte_loja", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("email_contato", sa.String(200)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        _agora(),
        sa.UniqueConstraint("nome_curto", name="uq_organizacoes_nome_curto"),
        sa.UniqueConstraint("cnpj", name="uq_organizacoes_cnpj"),
        sa.CheckConstraint("cnpj ~ '^[0-9A-Z]{12}[0-9]{2}$'", name="ck_organizacoes_cnpj"),
        sa.CheckConstraint("nome_curto = lower(nome_curto)", name="ck_organizacoes_nome_curto"),
    )
    op.create_table(
        "membros",
        _pk(),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False),
        _org(),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        _agora(),
        sa.UniqueConstraint("usuario_id", "organizacao_id", name="uq_membros_usuario_org"),
        sa.CheckConstraint("papel IN ('dono','operador','somente_leitura')", name="ck_membros_papel"),
    )
    op.create_index("ix_membros_organizacao_id", "membros", ["organizacao_id"])

    # usuários: papel sai, admin_plataforma e contato entram
    op.add_column("usuarios", sa.Column("admin_plataforma", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("usuarios", sa.Column("email_contato", sa.String(200)))
    op.execute("UPDATE usuarios SET admin_plataforma = true WHERE usuario = 'oscar'")
    op.drop_constraint("ck_usuarios_papel", "usuarios", type_="check")
    op.drop_column("usuarios", "papel")

    op.add_column("sessoes", sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id")))

    op.create_table(
        "locais",
        _pk(),
        _org(),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("nome_normalizado", sa.String(80), nullable=False),
        sa.Column("padrao", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        _agora(),
        sa.UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_locais_org_nome"),
    )
    op.create_index("ix_locais_organizacao_id", "locais", ["organizacao_id"])
    op.create_index(
        "uq_locais_um_padrao_por_org", "locais", ["organizacao_id"], unique=True, postgresql_where=sa.text("padrao")
    )

    op.create_table(
        "ingredientes",
        _pk(),
        _org(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("nome_normalizado", sa.String(120), nullable=False),
        sa.Column("unidade_base", sa.String(2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("juntado_em_id", sa.Uuid(), sa.ForeignKey("ingredientes.id")),
        _agora(),
        _agora("atualizado_em"),
        sa.UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_ingredientes_org_nome"),
        sa.CheckConstraint("unidade_base IN ('g','ml','un')", name="ck_ingredientes_unidade_base"),
    )
    op.create_index("ix_ingredientes_organizacao_id", "ingredientes", ["organizacao_id"])

    op.create_table(
        "itens_estoque",
        _pk(),
        _org(),
        sa.Column("ingrediente_id", sa.Uuid(), sa.ForeignKey("ingredientes.id"), nullable=False),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("nome_normalizado", sa.String(160), nullable=False),
        sa.Column("marca", sa.String(80), nullable=False, server_default=""),
        sa.Column("marca_normalizada", sa.String(80), nullable=False, server_default=""),
        sa.Column("unidade_controle", sa.String(12), nullable=False),
        sa.Column("conteudo_embalagem", sa.Numeric(18, 4)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        _agora(),
        sa.UniqueConstraint(
            "organizacao_id", "nome_normalizado", "marca_normalizada", name="uq_itens_org_nome_marca"
        ),
        sa.CheckConstraint("unidade_controle IN ('massa','volume','embalagem')", name="ck_itens_controle"),
        sa.CheckConstraint(
            "(unidade_controle = 'embalagem' AND conteudo_embalagem > 0)"
            " OR (unidade_controle <> 'embalagem' AND conteudo_embalagem IS NULL)",
            name="ck_itens_conteudo",
        ),
    )
    op.create_index("ix_itens_estoque_organizacao_id", "itens_estoque", ["organizacao_id"])
    op.create_index("ix_itens_estoque_ingrediente_id", "itens_estoque", ["ingrediente_id"])

    op.create_table(
        "lotes",
        _pk(),
        _org(),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("itens_estoque.id"), nullable=False),
        sa.Column("local_id", sa.Uuid(), sa.ForeignKey("locais.id"), nullable=False),
        sa.Column("codigo", sa.String(40), nullable=False),
        sa.Column("validade", sa.Date()),
        sa.Column("sem_validade", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("custo_unidade_base", sa.Numeric(18, 8)),
        _agora(),
        sa.UniqueConstraint("organizacao_id", "item_id", "codigo", name="uq_lotes_org_item_codigo"),
        sa.CheckConstraint("NOT (validade IS NOT NULL AND sem_validade)", name="ck_lotes_validade"),
    )
    op.create_index("ix_lotes_organizacao_id", "lotes", ["organizacao_id"])
    op.create_index("ix_lotes_item_id", "lotes", ["item_id"])

    op.create_table(
        "entradas",
        _pk(),
        _org(),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("local_id", sa.Uuid(), sa.ForeignKey("locais.id"), nullable=False),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("motivo", sa.String(20), nullable=False),
        sa.Column("motivo_detalhe", sa.String(200)),
        sa.Column("fornecedor", sa.String(160)),
        sa.Column("observacao", sa.Text()),
        sa.Column("lancada_por", sa.Uuid(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("chave_idempotencia", sa.String(64), nullable=False),
        _agora("criada_em"),
        sa.UniqueConstraint("organizacao_id", "chave_idempotencia", name="uq_entradas_org_chave"),
        sa.CheckConstraint("tipo IN ('sem_nota','com_nota')", name="ck_entradas_tipo"),
        sa.CheckConstraint(
            "motivo IN ('contagem','compra_sem_nota','bonificacao','outro')", name="ck_entradas_motivo"
        ),
    )
    op.create_index("ix_entradas_organizacao_id", "entradas", ["organizacao_id"])
    op.create_index("ix_entradas_data", "entradas", ["data"])

    op.create_table(
        "movimentos",
        _pk(),
        _org(),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("itens_estoque.id")),
        sa.Column("lote_id", sa.Uuid(), sa.ForeignKey("lotes.id")),
        sa.Column("quantidade_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("motivo", sa.Text()),
        sa.Column("entrada_id", sa.Uuid(), sa.ForeignKey("entradas.id")),
        sa.Column("ingrediente_origem_id", sa.Uuid(), sa.ForeignKey("ingredientes.id")),
        sa.Column("ingrediente_destino_id", sa.Uuid(), sa.ForeignKey("ingredientes.id")),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id"), nullable=False),
        _agora(),
        sa.CheckConstraint("tipo IN ('entrada','ajuste','juncao')", name="ck_movimentos_tipo"),
        sa.CheckConstraint(
            "(tipo = 'juncao' AND quantidade_base = 0"
            " AND ingrediente_origem_id IS NOT NULL AND ingrediente_destino_id IS NOT NULL)"
            " OR (tipo <> 'juncao' AND quantidade_base <> 0 AND lote_id IS NOT NULL AND item_id IS NOT NULL)",
            name="ck_movimentos_forma",
        ),
    )
    op.create_index("ix_movimentos_organizacao_id", "movimentos", ["organizacao_id"])
    op.create_index("ix_movimentos_lote", "movimentos", ["lote_id"])
    op.create_index("ix_movimentos_item", "movimentos", ["item_id"])

    op.create_table(
        "entrada_linhas",
        _pk(),
        _org(),
        sa.Column("entrada_id", sa.Uuid(), sa.ForeignKey("entradas.id"), nullable=False),
        sa.Column("posicao", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("itens_estoque.id"), nullable=False),
        sa.Column("lote_id", sa.Uuid(), sa.ForeignKey("lotes.id"), nullable=False),
        sa.Column("movimento_id", sa.Uuid(), sa.ForeignKey("movimentos.id"), nullable=False),
        sa.Column("quantidade", sa.Numeric(18, 4), nullable=False),
        sa.Column("unidade", sa.String(12), nullable=False),
        sa.Column("quantidade_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("custo_informado", sa.Numeric(14, 4)),
        sa.Column("custo_por", sa.String(12)),
        sa.Column("valor_total", sa.Numeric(14, 2)),
        sa.UniqueConstraint("entrada_id", "posicao", name="uq_entrada_linhas_posicao"),
    )
    op.create_index("ix_entrada_linhas_organizacao_id", "entrada_linhas", ["organizacao_id"])
    op.create_index("ix_entrada_linhas_entrada_id", "entrada_linhas", ["entrada_id"])

    op.create_table(
        "parecidos_distintos",
        _pk(),
        _org(),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("id_menor", sa.Uuid(), nullable=False),
        sa.Column("id_maior", sa.Uuid(), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id"), nullable=False),
        _agora(),
        sa.UniqueConstraint("organizacao_id", "tipo", "id_menor", "id_maior", name="uq_parecidos_par"),
        sa.CheckConstraint("tipo IN ('ingrediente','item')", name="ck_parecidos_tipo"),
    )
    op.create_index("ix_parecidos_distintos_organizacao_id", "parecidos_distintos", ["organizacao_id"])

    # Ledger imutável: corrige-se com um movimento contrário, nunca editando ou apagando.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION gestao_movimentos_imutaveis() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'append_only: movimentos não podem ser alterados nem apagados'
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER movimentos_imutaveis
        BEFORE UPDATE OR DELETE ON movimentos
        FOR EACH ROW EXECUTE FUNCTION gestao_movimentos_imutaveis()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS movimentos_imutaveis ON movimentos")
    op.execute("DROP FUNCTION IF EXISTS gestao_movimentos_imutaveis()")
    for tabela in (
        "parecidos_distintos",
        "entrada_linhas",
        "movimentos",
        "entradas",
        "lotes",
        "itens_estoque",
        "ingredientes",
        "locais",
    ):
        op.drop_table(tabela)
    op.drop_column("sessoes", "organizacao_id")
    # O papel volta para usuarios com o valor de uma das organizações (ou 'somente_leitura').
    op.add_column("usuarios", sa.Column("papel", sa.String(20), nullable=False, server_default="somente_leitura"))
    op.execute(
        "UPDATE usuarios u SET papel = m.papel FROM "
        "(SELECT DISTINCT ON (usuario_id) usuario_id, papel FROM membros ORDER BY usuario_id, criado_em) m "
        "WHERE m.usuario_id = u.id"
    )
    op.execute("UPDATE usuarios SET papel = 'dono' WHERE admin_plataforma")
    op.alter_column("usuarios", "papel", server_default=None)
    op.create_check_constraint(
        "ck_usuarios_papel", "usuarios", "papel IN ('dono','operador','somente_leitura')"
    )
    op.drop_column("usuarios", "email_contato")
    op.drop_column("usuarios", "admin_plataforma")
    op.drop_table("membros")
    op.drop_table("organizacoes")
