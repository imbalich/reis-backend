#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : 20261028_fit_result_industry.py
@Desc    : 拟合结果表增加数据产业字段(评审PR#3意见#4)
           回填规则: 历史数据全部为铁路; 机型命中风电产品表的行回填为 wind
           幂等(评审B7): 列已存在(如测试库曾手工加列)时跳过, 任何环境可重复执行
"""
import sqlalchemy as sa
from alembic import op

revision = '20261028_fit_industry'
down_revision = '20261028_wind_tables_pk'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col['name'] for col in inspector.get_columns(table_name)}


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _add_industry_if_missing(table_name: str) -> None:
    if not _table_exists(table_name):
        return
    if _column_exists(table_name, 'industry'):
        return
    op.add_column(
        table_name,
        sa.Column('industry', sa.String(20), nullable=False,
                  server_default='railway', comment='数据产业(railway/wind)'),
    )
    op.create_index(f'ix_{table_name}_industry', table_name, ['industry'])


def upgrade():
    _add_industry_if_missing('fit_part')
    _add_industry_if_missing('fit_product')
    # 回填: 机型命中风电产品表 → wind (其余保持 server_default 的 railway)
    if _table_exists('fit_part') and _table_exists('dm_jl_product'):
        op.execute(
            "UPDATE fit_part fp JOIN dm_jl_product jl ON TRIM(jl.MODEL) = TRIM(fp.model) "
            "SET fp.industry = 'wind'"
        )
    if _table_exists('fit_product') and _table_exists('dm_jl_product'):
        op.execute(
            "UPDATE fit_product fp JOIN dm_jl_product jl ON TRIM(jl.MODEL) = TRIM(fp.model) "
            "SET fp.industry = 'wind'"
        )


def downgrade():
    for table_name in ('fit_product', 'fit_part'):
        if _table_exists(table_name) and _column_exists(table_name, 'industry'):
            op.drop_index(f'ix_{table_name}_industry', table_name=table_name)
            op.drop_column(table_name, 'industry')
