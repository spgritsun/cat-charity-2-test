"""Add check constraints on amounts

Revision ID: 0e1e8a0fefab
Revises: 644300b5a1d7
Create Date: 2026-08-12 00:00:00.000000

Ограничения на суммы описаны в схемах Pydantic, но база до сих пор
принимала и отрицательную требуемую сумму, и вложенную больше требуемой.
Добавляем проверки на уровне БД.

В SQLite нет `ALTER TABLE ADD CONSTRAINT`, поэтому используется
`batch_alter_table`: Alembic создаёт новую таблицу с нужной схемой,
переливает данные, удаляет старую и переименовывает новую.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '0e1e8a0fefab'
down_revision = '644300b5a1d7'
branch_labels = None
depends_on = None

TABLES = ('charityproject', 'donation')

CONSTRAINTS = (
    ('full_amount_positive', 'full_amount > 0'),
    ('invested_amount_range', 'invested_amount BETWEEN 0 AND full_amount'),
)


def upgrade():
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            for name, condition in CONSTRAINTS:
                batch_op.create_check_constraint(name, condition)


def downgrade():
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            for name, _ in CONSTRAINTS:
                batch_op.drop_constraint(name, type_='check')
