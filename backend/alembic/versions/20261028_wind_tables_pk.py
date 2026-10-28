#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : 20261028_wind_tables_pk.py
@Desc    : 风电外部同步表(dm_jl_failure/dm_jl_product)补自增主键pk
           评审PR#3意见#5: 不手工ALTER生产库, 以迁移正式加主键;
           已与数据同步方确认: 同步按列名写入, 追加列位不影响刷新
"""
from alembic import op

revision = '20261028_wind_tables_pk'
down_revision = 'ad58201ee0c7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE dm_jl_failure '
        'ADD COLUMN pk BIGINT NOT NULL AUTO_INCREMENT, ADD PRIMARY KEY (pk)'
    )
    op.execute(
        'ALTER TABLE dm_jl_product '
        'ADD COLUMN pk BIGINT NOT NULL AUTO_INCREMENT, ADD PRIMARY KEY (pk)'
    )


def downgrade():
    op.execute('ALTER TABLE dm_jl_failure DROP PRIMARY KEY, DROP COLUMN pk')
    op.execute('ALTER TABLE dm_jl_product DROP PRIMARY KEY, DROP COLUMN pk')
