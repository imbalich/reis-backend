#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Any

from fast_captcha import text_captcha
from fastapi import BackgroundTasks, Request, Response

from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.schema.token import GetLoginToken
from backend.app.admin.schema.user import AddOAuth2UserParam
from backend.app.admin.service.login_log_service import login_log_service
from backend.common.enums import LoginLogStatusType, UserSocialType
from backend.common.i18n import t
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
        async with async_db_session.begin() as db:
            # OA平台返回格式：{"ret":"0","msg":"","uid":"用户工号"}
            # 已在oa_platform.py中转换为统一格式
            sid = user.get("id") or user.get("uuid")
            username = user.get("username")
            nickname = user.get("nickname")
            email = user.get("email", "")
            avatar = user.get("avatar_url", "")

            # 检查社交账号是否已绑定
            user_social = await user_social_dao.get_by_sid(
                db, str(sid), str(UserSocialType.oa_platform.value)
            )
            if user_social:
                # 已绑定，直接使用已存在的用户
                sys_user = await user_dao.get(db, user_social.user_id)
                # 更新用户头像
                if not sys_user.avatar and avatar:
                    await user_dao.update_avatar(db, sys_user.id, avatar)
            else:
                # 未绑定，查找或创建用户
                sys_user = None

                # 检测系统用户是否已存在（通过邮箱）
                # 注意：如果用户没有邮箱，email会是空字符串，if email会返回False，跳过此检查
                if email and email.strip():
                    sys_user = await user_dao.check_email(db, email)

                # 对于OA平台，如果username（工号）已存在，直接使用已存在的用户
                # 因为工号通常是唯一的，如果系统中已有该工号的用户，说明是同一人
                if not sys_user and username:
                    sys_user = await user_dao.get_by_username(db, username)

                # 如果用户不存在，创建新用户
                if not sys_user:
                    # 确保username存在（OA平台应该总是有工号，但为了安全起见）
                    if not username:
                        username = f"oa_user_{text_captcha(8)}"

                    # 处理username冲突（防止并发情况下的冲突）
                    # 注意：前面已经通过get_by_username检查过，正常情况下username不存在
                    # 但在高并发场景下，两个请求可能同时发现username不存在并尝试创建
                    # 因此保留此检查作为安全措施
                    original_username = username
                    existing_user = await user_dao.get_by_username(db, username)
                    if existing_user:
                        # 如果确实存在（并发冲突），添加随机后缀
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

                # 绑定社交账号
                new_user_social = CreateUserSocialParam(
                    sid=str(sid),
                    source=UserSocialType.oa_platform.value,
                    user_id=sys_user.id,
                )
                await user_social_dao.create(db, new_user_social)

            # 创建 token
            access_token = await jwt.create_access_token(
                sys_user.id,
                sys_user.is_multi_login,
                # extra info
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
            return data


oa_platform_service: OAPlatformService = OAPlatformService()
