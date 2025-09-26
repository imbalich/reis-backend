#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：fastapi-base-backend
@File    ：__init__.py.py
@IDE     ：PyCharm
@Author  ：imbalich
@Date    ：2024/12/25 16:39
"""

from fastapi import APIRouter

from backend.app.datamanage.api.v1.datamanage.despatch import router as despatch_router
from backend.app.datamanage.api.v1.datamanage.ebom import router as ebom_router
from backend.app.datamanage.api.v1.datamanage.failure import router as failure_router
from backend.app.datamanage.api.v1.datamanage.product import router as product_router
from backend.app.datamanage.api.v1.datamanage.repair import router as repair_router
from backend.app.datamanage.api.v1.datamanage.replace import router as replace_router
from backend.app.datamanage.api.v1.datamanage.configuration import (
    router as configuration_router,
)
from backend.app.datamanage.api.v1.datamanage.pc import router as pc_router
from backend.app.datamanage.api.v1.datamanage.overhaul import router as overhaul_router
from backend.app.datamanage.api.v1.datamanage.warehouse import (
    router as warehouse_router,
)
from backend.app.datamanage.api.v1.datamanage.warehouse_inventory import (
    router as warehouse_inventory_router,
)
from backend.app.datamanage.api.v1.datamanage.part_spare_mapping import (
    router as part_spare_mapping_router,
)
from backend.app.datamanage.api.v1.datamanage.allotment import (
    router as allotment_router,
)

router = APIRouter(prefix="/datamanage")

router.include_router(despatch_router, prefix='/despatch', tags=['发运数据'])
router.include_router(failure_router, prefix='/failure', tags=['故障数据'])
router.include_router(ebom_router, prefix='/ebom', tags=['ebom数据'])
router.include_router(product_router, prefix='/product', tags=['产品信息数据'])
router.include_router(repair_router, prefix='/repair', tags=['造修阶段数据'])
router.include_router(replace_router, prefix='/replace', tags=['必换件数据'])
router.include_router(configuration_router, prefix='/configuration', tags=['配置数据'])
router.include_router(pc_router, prefix='/pc', tags=['pc数据'])
router.include_router(overhaul_router, prefix='/overhaul', tags=['维修数据'])
router.include_router(despatch_router, prefix="/despatch", tags=["发运数据"])
router.include_router(failure_router, prefix="/failure", tags=["故障数据"])
router.include_router(ebom_router, prefix="/ebom", tags=["ebom数据"])
router.include_router(product_router, prefix="/product", tags=["产品信息数据"])
router.include_router(repair_router, prefix="/repair", tags=["造修阶段数据"])
router.include_router(replace_router, prefix="/replace", tags=["必换件数据"])
router.include_router(configuration_router, prefix="/configuration", tags=["配置数据"])
router.include_router(pc_router, prefix="/pc", tags=["pc数据"])
router.include_router(warehouse_router, prefix="/warehouse", tags=["仓库数据"])
router.include_router(
    warehouse_inventory_router, prefix="/warehouse-inventory", tags=["库房备品清单数据"]
)
router.include_router(
    part_spare_mapping_router,
    prefix="/part-spare-mapping",
    tags=["部件与备品对应关系数据"],
)
router.include_router(
    allotment_router,
    prefix="/allotment",
    tags=["产品配属数据"],
)
