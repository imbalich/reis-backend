#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project : reis-backend
@File    : __init__.py.py
@IDE     : PyCharm
@Author  : imbalich
@Time    : 2025/4/16 14:27
"""
from backend.core.conf import settings

from backend.app.datamanage.model.configuration import Configuration
from backend.app.datamanage.model.despatch import Despatch
from backend.app.datamanage.model.ebom import Ebom
from backend.app.datamanage.model.failure import Failure
from backend.app.datamanage.model.pc import PC
from backend.app.datamanage.model.product import Product
from backend.app.datamanage.model.repair import Repair
from backend.app.datamanage.model.replace import Replace
from backend.app.datamanage.model.overhaul import Overhaul
from backend.app.datamanage.model.warehouse import Warehouse
from backend.app.datamanage.model.allotment import Allotment
from backend.app.datamanage.model.warehouse_inventory import WarehouseInventory
from backend.app.datamanage.model.part_spare_mapping import PartSpareMapping
from backend.app.datamanage.model.lcc import LCC
from backend.app.datamanage.model.unqualify import Unqualify
from backend.app.datamanage.model.repair_interval import RepairInterval
from backend.app.datamanage.model.reliability_index import ReliabilityIndex
from backend.app.datamanage.model.failure_mro_correct import FailureMROCorrect  # 故障信息-来源MRO-修正数据

def get_failure_model():
    if settings.FAILURE_DATA_SOURCE == "mro_correct":
        return FailureMROCorrect
    return Failure

FailureModel = get_failure_model()