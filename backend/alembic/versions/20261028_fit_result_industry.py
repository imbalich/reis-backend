#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : 20261028_fit_result_industry.py
@Desc    : 拟合结果表增加数据产业字段(评审PR#3意见#4)
           回填规则: 历史数据全部为铁路; 机型命中风电产品表的行回填为 wind
"""
import sqlalchemy as sa
from alembic import op

revision = '20261028_fit_industry'
down_revision = '20261028_wind_tables_pk'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'fit_part',
        sa.Column('industry', sa.String(20), nullable=False,
                  server_default='railway', comment='数据产业(railway/wind)'),
    )
    op.create_index('ix_fit_part_industry', 'fit_part', ['industry'])
    op.add_column(
        'fit_product',
        sa.Column('industry', sa.String(20), nullable=False,
                  server_default='railway', comment='数据产业(railway/wind)'),
    )
    op.create_index('ix_fit_product_industry', 'fit_product', ['industry'])
    # 回填: 机型命中风电产品表 → wind (其余保持 server_default 的 railway)
    op.execute(
        "UPDATE fit_part fp JOIN dm_jl_product jl ON TRIM(jl.MODEL) = TRIM(fp.model) "
        "SET fp.industry = 'wind'"
    )
    op.execute(
        "UPDATE fit_product fp JOIN dm_jl_product jl ON TRIM(jl.MODEL) = TRIM(fp.model) "
        "SET fp.industry = 'wind'"
    )


def downgrade():
    op.drop_index('ix_fit_product_industry', table_name='fit_product')
    op.drop_column('fit_product', 'industry')
    op.drop_index('ix_fit_part_industry', table_name='fit_part')
    op.drop_column('fit_part', 'industry')
