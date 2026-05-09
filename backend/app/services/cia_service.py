"""CIA 统一认证服务封装"""
import requests
import urllib3
from typing import Dict, Any
from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger()

# 禁用 SSL 警告（CIA 线上环境证书问题）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CIAError(Exception):
    """CIA 认证错误"""
    pass


class CIAService:
    """CIA 统一认证服务封装"""

    ERROR_CODES = {
        "invalid_request": "请求参数错误",
        "invalid_client": "客户端认证失败",
        "invalid_grant": "授权码无效或已过期",
        "unauthorized_client": "客户端未授权",
        "access_denied": "访问被拒绝",
        "unsupported_response_type": "不支持的响应类型",
        "invalid_scope": "无效的权限范围",
        "server_error": "CIA 服务端错误",
        "temporarily_unavailable": "服务暂时不可用",
    }

    def __init__(self):
        self.base_url = settings.CIA_URL.rstrip("/")
        self.client_id = settings.CIA_ACCESS_CLIENT_ID
        self.client_secret = settings.CIA_CLIENT_SECRET
        self.app_key = settings.CIA_APP_KEY
        self.app_secret = settings.CIA_APP_SECRET

    def _get_error_message(self, error_code: str) -> str:
        """获取错误码对应的中文描述"""
        return self.ERROR_CODES.get(error_code, f"未知错误 ({error_code})")

    def code_to_token(self, code: str, auth_code: str) -> Dict[str, Any]:
        """
        用 code + auth_code 换取 access_token
        接口：POST /internal_api/authenticationByCodeAndAuthCode
        """
        url = f"{self.base_url}/internal_api/authenticationByCodeAndAuthCode"
        # Fallback: if auth_code is empty, try using code as authCode
        effective_auth_code = auth_code or code
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "authCode": effective_auth_code,
            "code": code,
        }
        try:
            response = requests.post(url, data=data, timeout=30, verify=False)
            result = response.json()
            if not result.get("result"):
                error_code = result.get("errorCode", "unknown")
                logger.warning(f"CIA code_to_token failed: {error_code}")
                return {
                    "result": False,
                    "errorCode": error_code,
                    "message": self._get_error_message(error_code),
                }
            return {
                "result": True,
                "access_token": result.get("access_token", ""),
            }
        except Exception as e:
            logger.error(f"CIA code_to_token request failed: {e}")
            return {"result": False, "errorCode": "request_failed", "message": str(e)}

    def code_login(self, code: str) -> Dict[str, Any]:
        """
        备选方案：用 code 直接登录（ CIA SDK 内部使用的 codeLogin API ）
        接口：GET https://sso.example.com/auth?code=xxx
        """
        url = "https://sso.example.com/auth"
        params = {"code": code}
        try:
            response = requests.get(url, params=params, timeout=30, verify=False)
            result = response.json()
            if not result.get("result"):
                error_code = result.get("errorCode", "unknown")
                logger.warning(f"CIA code_login failed: {error_code}")
                return {
                    "result": False,
                    "errorCode": error_code,
                    "message": result.get("errorMessage", self._get_error_message(error_code)),
                }
            return {
                "result": True,
                "access_token": result.get("access_token", ""),
            }
        except Exception as e:
            logger.error(f"CIA code_login request failed: {e}")
            return {"result": False, "errorCode": "request_failed", "message": str(e)}

    def get_user_info(self, access_token: str, user_identify: str = "") -> Dict[str, Any]:
        """
        通过 findUserWithToken 获取 CIA 用户信息
        接口：GET /special_api/v1/findUserWithToken
        参数：appKey, appSecret, access_token, userIdentify
        """
        url = f"{self.base_url}/special_api/v1/findUserWithToken"
        params = {
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "access_token": access_token,
            "userIdentify": user_identify,
        }
        try:
            response = requests.get(url, params=params, timeout=30, verify=False)
            result = response.json()
            if not result.get("result"):
                error_code = result.get("errorCode", "unknown")
                logger.warning(f"CIA findUserWithToken failed: {error_code}")
                return {}
            data = result.get("value", {})
            return {
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "mobile": data.get("mobile", ""),
                "headPicture": data.get("headPicture", ""),
                "userId": data.get("userId", ""),
                "nickName": data.get("nickName", ""),
                "username": data.get("username", ""),
                "orgId": data.get("orgId", ""),
                "orgName": data.get("orgName", ""),
                "departmentName": data.get("departmentName", ""),
            }
        except Exception as e:
            logger.error(f"CIA get_user_info request failed: {e}")
            return {}

    def logout(self, access_token: str) -> bool:
        """
        通知 CIA 服务端使 token 失效
        接口：GET /internal_api/internal_logout
        """
        url = f"{self.base_url}/internal_api/internal_logout"
        params = {"client_id": self.client_id, "access_token": access_token}
        try:
            response = requests.get(url, params=params, timeout=10, verify=False)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"CIA logout failed: {e}")
            return False


# 全局服务实例
_cia_service: CIAService = None


def get_cia_service() -> CIAService:
    """获取 CIA 服务实例（单例）"""
    global _cia_service
    if _cia_service is None:
        _cia_service = CIAService()
    return _cia_service
