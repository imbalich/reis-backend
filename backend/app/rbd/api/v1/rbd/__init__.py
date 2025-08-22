# backend/app/rbd/api/v1/rbd/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.rbd.api.v1.rbd.projects import router as projects_router

router = APIRouter(prefix='/rbd')

router.include_router(projects_router, prefix='/projects', tags=['RBD项目'])