"""usuarios, sessoes e tentativas_login

Revision ID: 0001_usuarios_sessoes
Revises:
Create Date: 2026-11-02
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_usuarios_sessoes"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario", sa.String(80), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("ultimo_acesso_em", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("usuario", name="uq_usuarios_usuario"),
        sa.CheckConstraint("papel IN ('dono','operador','somente_leitura')", name="ck_usuarios_papel"),
        sa.CheckConstraint("usuario = lower(usuario)", name="ck_usuarios_usuario_minusculo"),
    )
    op.create_table(
        "sessoes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column(
            "usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ultimo_uso_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True)),
        sa.Column("cliente", sa.String(80)),
        sa.UniqueConstraint("token_hash", name="uq_sessoes_token_hash"),
    )
    op.create_index("ix_sessoes_expira_em", "sessoes", ["expira_em"])
    op.create_table(
        "tentativas_login",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario", sa.String(80), nullable=False),
        sa.Column("cliente", sa.String(80), nullable=False),
        sa.Column("sucesso", sa.Boolean(), nullable=False),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_tentativas_login_usuario_em", "tentativas_login", ["usuario", "criada_em"])


def downgrade() -> None:
    op.drop_index("ix_tentativas_login_usuario_em", table_name="tentativas_login")
    op.drop_table("tentativas_login")
    op.drop_index("ix_sessoes_expira_em", table_name="sessoes")
    op.drop_table("sessoes")
    op.drop_table("usuarios")
