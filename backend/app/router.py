#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.admin.api.router import v1 as admin_v1
from backend.app.datamanage.api.router import v1 as datamanage_v1
from backend.app.fit.api.router import v1 as fit_v1
from backend.app.predict.api.router import v1 as predict_v1
from backend.app.sense.api.router import v1 as sense_v1
from backend.app.task.api.router import v1 as task_v1

router = APIRouter()

router.include_router(admin_v1)
router.include_router(task_v1)
router.include_router(datamanage_v1)
router.include_router(fit_v1)
router.include_router(predict_v1)
router.include_router(sense_v1)
