"""remove netcli references

Revision ID: 82ad1e72a7f0
Revises: 60de23d5cd17
Create Date: 2022-12-30 14:42:11.541054+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82ad1e72a7f0'
down_revision = '60de23d5cd17'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(
        'UPDATE account_bsdusers SET bsdusr_shell = "/usr/sbin/nologin" WHERE bsdusr_shell LIKE "%netcli%"'
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
