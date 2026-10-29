#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : 20261028_wind_tables_pk.py
@Desc    : 风电外部同步表(dm_jl_failure/dm_jl_product)补自增主键pk
           评审PR#3意见#5(B5): 不手工ALTER生产库, 以迁移正式加主键;
           已与数据同步方确认: 同步按列名写入, 追加列位不影响刷新。
           幂等(评审B5验收要求): 表不存在或 pk 列已存在时跳过, 任何环境可重复执行。
"""
import sqlalchemy as sa
from alembic import op

revision = '20261028_wind_tables_pk'
down_revision = '20260511_science_warehouse_push'
branch_labels = None
depends_on = None

_TABLES = ('dm_jl_failure', 'dm_jl_product')


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return column_name in {col['name'] for col in inspector.get_columns(table_name)}


def upgrade():
    # dm_jl_* 为外部数据同步建表: 表尚未创建(全新环境/生产未同步)或已加过主键时跳过
    for table in _TABLES:
        if not _table_exists(table):
            continue
        if _column_exists(table, 'pk'):
            continue
        op.execute(
            f'ALTER TABLE {table} '
            'ADD COLUMN pk BIGINT NOT NULL AUTO_INCREMENT, ADD PRIMARY KEY (pk)'
        )


def downgrade():
    for table in _TABLES:
        if _column_exists(table, 'pk'):
            op.execute(f'ALTER TABLE {table} DROP PRIMARY KEY, DROP COLUMN pk')
