from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import Settings


class DingTalkOAuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DingTalkProfile:
    subject: str
    avatar_url: str | None = None
    corp_id: str | None = None
    corp_name: str | None = None
    display_name: str | None = None
    email: str | None = None
    open_id: str | None = None
    union_id: str | None = None

    def identity_profile(self) -> dict[str, Any]:
        return {
            "avatar_url": self.avatar_url,
            "corp_id": self.corp_id,
            "corp_name": self.corp_name,
            "display_name": self.display_name,
            "email": self.email,
            "open_id": self.open_id,
            "union_id": self.union_id,
        }


class DingTalkOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_authorize_url(self, *, redirect_uri: str, state: str) -> str:
        params = {
            "client_id": self.settings.dingtalk_client_id,
            "prompt": "consent",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid corpid",
            "state": state,
        }
        return f"{self.settings.dingtalk_auth_url}?{urlencode(params)}"

    def exchange_code_for_profile(self, code: str) -> DingTalkProfile:
        token_payload = self._post_json(
            self.settings.dingtalk_token_url,
            {
                "clientId": self.settings.dingtalk_client_id,
                "clientSecret": self.settings.dingtalk_client_secret_value,
                "code": code,
                "grantType": "authorization_code",
            },
        )
        access_token = token_payload.get("accessToken") or token_payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise DingTalkOAuthError("DINGTALK_TOKEN_EXCHANGE_FAILED", "DingTalk token missing")
        user_payload = self._get_json(
            self.settings.dingtalk_userinfo_url,
            headers={"x-acs-dingtalk-access-token": access_token},
        )
        return self._profile_from_payload({**token_payload, **user_payload})

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._request_json(request)

    def _get_json(self, url: str, *, headers: dict[str, str]) -> dict[str, Any]:
        request = Request(url, headers=headers, method="GET")
        return self._request_json(request)

    def _request_json(self, request: Request) -> dict[str, Any]:
        try:
            with urlopen(request, timeout=10) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - exercised through fake client in tests
            raise DingTalkOAuthError("DINGTALK_UPSTREAM_ERROR", "DingTalk upstream failed") from exc
        if not isinstance(payload, dict):
            raise DingTalkOAuthError("DINGTALK_UPSTREAM_ERROR", "DingTalk response invalid")
        return payload

    def _profile_from_payload(self, payload: dict[str, Any]) -> DingTalkProfile:
        union_id = _first_text(payload, "unionId", "union_id", "unionid")
        open_id = _first_text(payload, "openId", "open_id", "openid")
        subject = union_id or open_id
        if not subject:
            raise DingTalkOAuthError("DINGTALK_PROFILE_INCOMPLETE", "DingTalk subject missing")
        corp_id = _first_text(payload, "corpId", "corp_id", "corpIdList")
        corp_name = _first_text(
            payload,
            "corpName",
            "corp_name",
            "companyName",
            "organizationName",
            "orgName",
            "tenantName",
        )
        return DingTalkProfile(
            avatar_url=_first_text(payload, "avatarUrl", "avatar_url", "avatar"),
            corp_id=corp_id,
            corp_name=corp_name or self.settings.dingtalk_corp_name_map.get(corp_id or ""),
            display_name=_first_text(payload, "nick", "name", "displayName", "display_name"),
            email=_first_text(payload, "email"),
            open_id=open_id,
            subject=subject,
            union_id=union_id,
        )


def _first_text(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value and isinstance(value[0], str) and value[0].strip():
            return value[0].strip()
    return None
