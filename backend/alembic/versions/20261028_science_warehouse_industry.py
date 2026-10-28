#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : 20261028_science_warehouse_industry.py
@Desc    : 科学库存结果/推送结果表增加数据产业字段(评审PR#3意见#4)
           回填规则: 存量数据均为铁路时代产出, 统一回填 railway
"""
import sqlalchemy as sa
from alembic import op

revision = '20261028_science_industry'
down_revision = '20261028_fit_industry'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'calcu_science_warehouse_result',
        sa.Column('industry', sa.String(20), nullable=False,
                  server_default='railway', comment='数据产业(railway/wind/mixed)'),
    )
    op.create_index(
        'ix_calcu_science_warehouse_result_industry',
        'calcu_science_warehouse_result', ['industry'],
    )
    op.add_column(
        'calcu_science_warehouse_push_result',
        sa.Column('industry', sa.String(20), nullable=False,
                  server_default='railway', comment='数据产业(railway/wind/mixed)'),
    )
    op.create_index(
        'ix_calcu_science_warehouse_push_result_industry',
        'calcu_science_warehouse_push_result', ['industry'],
    )


def downgrade():
    op.drop_index('ix_calcu_science_warehouse_push_result_industry',
                  table_name='calcu_science_warehouse_push_result')
    op.drop_column('calcu_science_warehouse_push_result', 'industry')
    op.drop_index('ix_calcu_science_warehouse_result_industry',
                  table_name='calcu_science_warehouse_result')
    op.drop_column('calcu_science_warehouse_result', 'industry')
