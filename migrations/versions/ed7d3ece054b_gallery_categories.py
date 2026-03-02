"""gallery categories

Revision ID: ed7d3ece054b
Revises: 7bcf7cc0e91d
Create Date: 2025-10-30 12:32:05.166437

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy import or_, func
from sqlalchemy.orm import joinedload
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed7d3ece054b'
down_revision = '7bcf7cc0e91d'
branch_labels = None
depends_on = None



def _has_table(bind, name: str) -> bool:
    insp = sa.inspect(bind)
    return name in insp.get_table_names()

def _has_column(bind, table: str, col: str) -> bool:
    insp = sa.inspect(bind)
    return col in [c["name"] for c in insp.get_columns(table)]

def upgrade():
    bind = op.get_bind()

    # 1) أنشئ جدول التصنيفات إذا لم يكن موجودًا
    if not _has_table(bind, "category"):
        op.create_table(
            "category",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("name_en", sa.String(120), nullable=True),
            sa.UniqueConstraint("slug", name="uq_category_slug"),
        )

    # 2) أضف العمود + الـ FK داخل batch مع إعادة إنشاء الجدول (SQLite-safe)
    if not _has_column(bind, "gallery", "category_id"):
        with op.batch_alter_table("gallery", recreate="always") as b:
            b.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
            # IMPORTANT: إنشاء الـ FK داخل batch وباسم صريح
            b.create_foreign_key(
                "fk_gallery_category",
                "category",
                ["category_id"],
                ["id"],
                ondelete="SET NULL",  # SQLite يتجاهلها لكن لا تضر
            )

        # 3) الفهرس على العمود (خارج batch، مع IF NOT EXISTS لسلامة الإعادة)
        op.execute("CREATE INDEX IF NOT EXISTS ix_gallery_category_id ON gallery (category_id)")

def downgrade():
    bind = op.get_bind()

    # إسقاط الـ FK والعمود داخل batch بإعادة الإنشاء
    if _has_column(bind, "gallery", "category_id"):
        with op.batch_alter_table("gallery", recreate="always") as b:
            try:
                b.drop_constraint("fk_gallery_category", type_="foreignkey")
            except Exception:
                # في حال لم يُنشأ القيد لأي سبب، تابع حذف العمود
                pass
            b.drop_column("category_id")

    # حذف الفهرس إن وجد
    op.execute("DROP INDEX IF EXISTS ix_gallery_category_id")

    # إسقاط جدول التصنيفات إن وجد
    if _has_table(bind, "category"):
        op.drop_table("category")
