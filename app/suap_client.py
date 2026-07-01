import secrets
from typing import Optional, Dict
from urllib.parse import urlencode

import requests
from jose import jwt

from app.database import settings

class SUAPClient:
    def __init__(self):
        self.base_url = settings.suap_api_url.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self.authorize_url = f"{self.base_url}/o/authorize/"
        self.token_url = f"{self.base_url}/o/token/"

    def _parse_user_data(self, user_data: dict, matricula_fallback: str = "") -> Dict:
        matricula = (
            user_data.get("matricula")
            or user_data.get("username")
            or matricula_fallback
            or ""
        ).strip()

        return {
            "cpf": user_data.get("cpf", ""),
            "matricula": matricula,
            "nome_completo": user_data.get("nome_registro") or user_data.get("nome", ""),
            "email": user_data.get("email_preferencial") or user_data.get("email", ""),
            "campus": user_data.get("campus", ""),
            "curso": user_data.get("curso", ""),
            "tipo_usuario": user_data.get("tipo_usuario", ""),
        }

    def criar_state(self) -> str:
        payload = {"nonce": secrets.token_urlsafe(16)}
        return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

    def validar_state(self, state: str) -> bool:
        try:
            jwt.decode(state, settings.secret_key, algorithms=[settings.algorithm])
            return True
        except Exception:
            return False

    def url_autorizacao(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": settings.suap_client_id,
            "redirect_uri": settings.suap_redirect_uri,
            "scope": settings.suap_oauth_scope,
            "state": state,
        }
        return f"{self.authorize_url}?{urlencode(params)}"

    def trocar_codigo_por_token(self, code: str) -> Optional[Dict]:
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.suap_redirect_uri,
                    "client_id": settings.suap_client_id,
                    "client_secret": settings.suap_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )

            if response.status_code != 200:
                return {"error": "Erro ao trocar código de autorização pelo token do SUAP"}

            token_data = response.json()
            access_token = token_data.get("access_token") or token_data.get("access")
            if not access_token:
                return {"error": "Token de acesso não retornado pelo SUAP"}

            return {"access_token": access_token}
        except requests.exceptions.Timeout:
            return {"error": "Timeout ao conectar com o SUAP"}
        except requests.exceptions.ConnectionError:
            return {"error": "Erro de conexão com o SUAP"}
        except requests.exceptions.RequestException as exc:
            return {"error": f"Erro ao conectar com o SUAP: {exc}"}
        except Exception as exc:
            return {"error": f"Erro inesperado: {exc}"}

    def buscar_usuario(self, access_token: str) -> Optional[Dict]:
        try:
            user_response = requests.get(
                f"{self.api_url}/rh/eu/",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )

            if user_response.status_code != 200:
                return {"error": "Erro ao buscar dados do usuário no SUAP"}

            return self._parse_user_data(user_response.json())
        except requests.exceptions.Timeout:
            return {"error": "Timeout ao conectar com o SUAP"}
        except requests.exceptions.ConnectionError:
            return {"error": "Erro de conexão com o SUAP"}
        except requests.exceptions.RequestException as exc:
            return {"error": f"Erro ao conectar com o SUAP: {exc}"}
        except Exception as exc:
            return {"error": f"Erro inesperado: {exc}"}
