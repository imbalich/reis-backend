#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any
import traceback

from fast_captcha import text_captcha
from fastapi import BackgroundTasks, Request, Response

from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.schema.token import GetLoginToken
from backend.app.admin.schema.user import AddOAuth2UserParam
from backend.app.admin.service.login_log_service import login_log_service
from backend.common.enums import LoginLogStatusType, UserSocialType
from backend.common.i18n import t
from backend.common.log import log
from backend.common.security import jwt
from backend.core.conf import settings
from backend.database.db import async_db_session
from backend.database.redis import redis_client
from backend.plugin.oauth2.crud.crud_user_social import user_social_dao
from backend.plugin.oauth2.schema.user_social import CreateUserSocialParam
from backend.utils.timezone import timezone


class OAPlatformService:
    """OA平台 OAuth2 认证服务类"""

    @staticmethod
    async def create_with_login(
        *,
        request: Request,
        response: Response,
        background_tasks: BackgroundTasks,
        user: dict[str, Any],
    ) -> GetLoginToken | None:
        """
        创建 OA平台 OAuth2 用户并登录

        :param request: FastAPI 请求对象
        :param response: FastAPI 响应对象
        :param background_tasks: FastAPI 后台任务
        :param user: OA平台用户信息（已转换为统一格式）
        :return:
        """
        log.info(f"OA create_with_login entering with user={user}")
        try:
            async with async_db_session.begin() as db:
                sid = user.get("id") or user.get("uuid")
                username = user.get("username")
                nickname = user.get("nickname")
                email = user.get("email") or None
                avatar = user.get("avatar_url") or None

                user_social = await user_social_dao.get_by_sid(
                    db, str(sid), str(UserSocialType.oa_platform.value)
                )
                if user_social:
                    log.info(
                        f"OA user already bound: sid={sid} user_id={user_social.user_id}"
                    )
                    sys_user = await user_dao.get(db, user_social.user_id)
                    if not sys_user.avatar and avatar:
                        await user_dao.update_avatar(db, sys_user.id, avatar)
                else:
                    sys_user = None

                    if email and email.strip():
                        sys_user = await user_dao.check_email(db, email)

                    if not sys_user and username:
                        sys_user = await user_dao.get_by_username(db, username)

                    if not sys_user:
                        if not username:
                            username = f"oa_user_{text_captcha(8)}"

                        original_username = username
                        existing_user = await user_dao.get_by_username(db, username)
                        if existing_user:
                            while await user_dao.get_by_username(db, username):
                                username = f"{original_username}_{text_captcha(5)}"

                        new_sys_user = AddOAuth2UserParam(
                            username=username,
                            password=None,
                            nickname=nickname,
                            email=email,
                            avatar=avatar,
                        )
                        await user_dao.add_by_oauth2(db, new_sys_user)
                        await db.flush()
                        sys_user = await user_dao.get_by_username(db, username)
                        log.info(
                            f"OA created new user: db_user_id={sys_user.id if sys_user else None} username={username} sid={sid}"
                        )

                    new_user_social = CreateUserSocialParam(
                        sid=str(sid),
                        source=UserSocialType.oa_platform.value,
                        user_id=sys_user.id,
                    )
                    await user_social_dao.create(db, new_user_social)
                    log.info(
                        f"OA bound user social: db_user_id={sys_user.id} sid={sid}"
                    )

                access_token = await jwt.create_access_token(
                    sys_user.id,
                    sys_user.is_multi_login,
                    username=sys_user.username,
                    nickname=sys_user.nickname or f"#{text_captcha(5)}",
                    last_login_time=timezone.to_str(timezone.now()),
                    ip=request.state.ip,
                    os=request.state.os,
                    browser=request.state.browser,
                    device=request.state.device,
                )
                refresh_token = await jwt.create_refresh_token(
                    access_token.session_uuid, sys_user.id, sys_user.is_multi_login
                )
                await user_dao.update_login_time(db, sys_user.username)
                await db.refresh(sys_user)
                login_log = dict(
                    db=db,
                    request=request,
                    user_uuid=sys_user.uuid,
                    username=sys_user.username,
                    login_time=timezone.now(),
                    status=LoginLogStatusType.success.value,
                    msg=t("success.login.oauth2_success"),
                )
                background_tasks.add_task(login_log_service.create, **login_log)
                await redis_client.delete(
                    f"{settings.CAPTCHA_LOGIN_REDIS_PREFIX}:{request.state.ip}"
                )
                response.set_cookie(
                    key=settings.COOKIE_REFRESH_TOKEN_KEY,
                    value=refresh_token.refresh_token,
                    max_age=settings.COOKIE_REFRESH_TOKEN_EXPIRE_SECONDS,
                    expires=timezone.to_utc(refresh_token.refresh_token_expire_time),
                    httponly=True,
                )
                data = GetLoginToken(
                    access_token=access_token.access_token,
                    access_token_expire_time=access_token.access_token_expire_time,
                    session_uuid=access_token.session_uuid,
                    user=sys_user,  # type: ignore
                )
                log.info(
                    f"OA create_with_login success: user_id={sys_user.id} session_uuid={data.session_uuid}"
                )
                return data
        except Exception as e:
            trace = traceback.format_exc()
            log.error(f"OA create_with_login failed for user={user} error={e}\n{trace}")
            raise


oa_platform_service: OAPlatformService = OAPlatformService()
