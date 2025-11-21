#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from fastapi_limiter.depends import RateLimiter
from starlette.responses import RedirectResponse

from backend.common.log import log
from backend.common.response.response_schema import ResponseSchemaModel, response_base
from backend.core.conf import settings
from backend.database.redis import redis_client
from backend.plugin.oauth2.service.oa_platform_service import oa_platform_service

router = APIRouter()

# Redis key前缀
OA_PLATFORM_STATE_REDIS_PREFIX = "fba:oauth2:oa_platform:state"
OA_PLATFORM_STATE_EXPIRE_SECONDS = 60 * 5  # 5分钟过期


@router.get("", summary="获取 OA平台 授权链接")
async def get_oa_platform_oauth2_url(request: Request) -> ResponseSchemaModel[str]:
    """
    生成授权链接并重定向到OA平台进行登录认证

    :param request: FastAPI 请求对象
    :return: 授权链接
    """
    # 生成随机state字符串
    state = secrets.token_urlsafe(32)

    # 将state存储到Redis，设置5分钟过期
    await redis_client.setex(
        f"{OA_PLATFORM_STATE_REDIS_PREFIX}:{state}",
        OA_PLATFORM_STATE_EXPIRE_SECONDS,
        "1",
    )

    # 构建回调地址
    callback_url = f"{request.url}/callback"

    # 构建授权URL参数
    params = {
        "client_id": settings.OAUTH2_OA_PLATFORM_CLIENT_ID,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "read",
        "state": state,
    }

    # 构建完整的授权URL
    authorize_url = f"{settings.OAUTH2_OA_PLATFORM_BASE_URL}/sso/oauth2/authorize?{urlencode(params)}"

    return response_base.success(data=authorize_url)


@router.get(
    "/callback",
    summary="OA平台 授权自动重定向",
    description="OA平台授权后，自动重定向到当前地址并获取用户信息，通过用户信息自动创建系统用户",
    dependencies=[Depends(RateLimiter(times=5, minutes=1))],
)
async def oa_platform_oauth2_callback(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态参数"),
) -> RedirectResponse:
    """
    OA平台OAuth2回调处理

    :param request: FastAPI 请求对象
    :param response: FastAPI 响应对象
    :param background_tasks: FastAPI 后台任务
    :param code: 授权码
    :param state: 状态参数
    :return: 重定向响应
    """
    log.info(
        f"OA callback start: code={code} state={state} ip={getattr(request.client, 'host', None)}"
    )

    # 验证state参数
    state_key = f"{OA_PLATFORM_STATE_REDIS_PREFIX}:{state}"
    stored_state = await redis_client.get(state_key)
    if not stored_state:
        # state无效或已过期
        log.warning(
            f"OA callback invalid state: state={state} ip={getattr(request.client, 'host', None)}"
        )
        return RedirectResponse(
            url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error=invalid_state"
        )

    # 验证通过后删除state（一次性使用）
    await redis_client.delete(state_key)

    try:
        log.info(f"OA token exchange start: code={code}")

        # 第二步：用code换取access_token
        token_url = f"{settings.OAUTH2_OA_PLATFORM_BASE_URL}/sso/oauth2/token"
        token_data = {
            "code": code,
            "client_id": settings.OAUTH2_OA_PLATFORM_CLIENT_ID,
            "client_secret": settings.OAUTH2_OA_PLATFORM_CLIENT_SECRET,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            token_response.raise_for_status()
            token_result = token_response.json()
            log.info(f"OA token response: {token_result}")

            # 检查是否有错误
            if "error" in token_result:
                log.error(f"OA token response contains error: {token_result}")
                return RedirectResponse(
                    url=f'{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error={token_result.get("error_description", "token_error")}'
                )

            access_token = token_result.get("access_token")
            if not access_token:
                log.error("OA token response missing access_token")
                return RedirectResponse(
                    url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error=no_access_token"
                )

            # 第三步：用access_token获取用户信息
            userinfo_url = f"{settings.OAUTH2_OA_PLATFORM_BASE_URL}/sso/oauth2/userInfo"
            userinfo_data = {
                "access_token": access_token,
                "client_id": settings.OAUTH2_OA_PLATFORM_CLIENT_ID,
            }

            userinfo_response = await client.post(
                userinfo_url,
                data=userinfo_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
            userinfo_response.raise_for_status()
            userinfo_result = userinfo_response.json()
            log.info(f"OA userinfo response: {userinfo_result}")

            # 检查返回结果
            ret_value = userinfo_result.get("ret")
            if str(ret_value) != "0":
                error_msg = userinfo_result.get("msg", "获取用户信息失败")
                log.error(f"OA userinfo ret invalid: {userinfo_result}")
                return RedirectResponse(
                    url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error={error_msg}"
                )

            # 将OA平台的用户信息转换为统一格式
            # 根据文档，返回格式：{"ret":"0","msg":"","uid":"用户工号"}
            # 需要根据实际返回的字段调整
            user = {
                "id": userinfo_result.get("uid", ""),
                "uuid": userinfo_result.get("uid", ""),
                "username": userinfo_result.get("uid", ""),
                "nickname": userinfo_result.get(
                    "name",
                    userinfo_result.get("loginName", userinfo_result.get("uid", "")),
                ),
                # "email": userinfo_result.get("email", ""),
                # "avatar_url": userinfo_result.get("avatar", ""),
            }

            log.info(f"OA create_with_login start for user: {user}")

            # 调用service创建用户并登录
            data = await oa_platform_service.create_with_login(
                request=request,
                response=response,
                background_tasks=background_tasks,
                user=user,
            )

            if not data:
                log.error(f"OA create_with_login returned None, user={user}")
                return RedirectResponse(
                    url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error=login_failed"
                )

            success_url = (
                f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}"
                f"?access_token={data.access_token}&session_uuid={data.session_uuid}"
            )
            log.info(f"OA success redirect url: {success_url}")
            return RedirectResponse(url=success_url)

    except httpx.HTTPError as e:
        # HTTP请求错误
        log.exception("OA callback HTTP error")
        return RedirectResponse(
            url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error=http_error"
        )
    except Exception as e:
        # 其他错误
        log.exception("OA callback unknown error")
        return RedirectResponse(
            url=f"{settings.OAUTH2_FRONTEND_REDIRECT_URI}?error=unknown_error"
        )
