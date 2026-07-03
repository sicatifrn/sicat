import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth_utils import create_access_token, get_current_user, get_password_hash
from app.database import get_db, matriculas_admin_configuradas, settings
from app.models import Biblioteca, BibliotecarioBiblioteca, JWTAuth, TipoUsuario, Usuario
from app.suap_client import SUAPClient

router = APIRouter()
suap_client = SUAPClient()


def _frontend_login_url(**params: str) -> str:
    base = settings.frontend_url.rstrip("/")
    query = urlencode(params) if params else ""
    return f"{base}/login{'?' + query if query else ''}"


def _provisionar_usuario(suap_data: dict, db: Session) -> Usuario:
    cpf_raw = suap_data.get("cpf", "") or ""
    cpf_limpo = cpf_raw.replace(".", "").replace("-", "").replace(" ", "")
    matricula_final = (suap_data.get("matricula", "") or "").strip()

    if not matricula_final:
        campos = suap_data.get("_campos_suap")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Matrícula não retornada pelo SUAP. Campos recebidos: {campos}",
        )

    usuario = db.query(Usuario).filter(Usuario.matricula == matricula_final).first()
    admins = matriculas_admin_configuradas()
    tipo = TipoUsuario.admin if matricula_final in admins else TipoUsuario.default

    if usuario:
        usuario.nome_completo = suap_data.get("nome_completo", usuario.nome_completo)
        if cpf_limpo:
            usuario.cpf = cpf_limpo
        if matricula_final in admins and usuario.tipo == TipoUsuario.default:
            usuario.tipo = TipoUsuario.admin
        usuario.data_edicao = datetime.utcnow()
    else:
        usuario = Usuario(
            cpf=cpf_limpo or "00000000000",
            matricula=matricula_final,
            nome_completo=suap_data.get("nome_completo", ""),
            senha=get_password_hash(secrets.token_urlsafe(32)),
            tipo=tipo,
        )
        db.add(usuario)

    db.commit()
    db.refresh(usuario)
    return usuario


def _emitir_token(usuario: Usuario, db: Session) -> str:
    access_token_expires = timedelta(hours=settings.access_token_expire_hours)
    access_token = create_access_token(
        data={"sub": usuario.id, "tipo": usuario.tipo.value},
        expires_delta=access_token_expires,
    )

    token_db = JWTAuth(
        usuario_id=usuario.id,
        token=access_token,
        expiracao=datetime.utcnow() + access_token_expires,
    )
    db.add(token_db)
    db.commit()
    return access_token


@router.get("/suap/login")
def suap_login():
    if not settings.suap_client_id or not settings.suap_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth do SUAP não configurado no servidor",
        )

    state = suap_client.criar_state()
    return RedirectResponse(url=suap_client.url_autorizacao(state), status_code=302)


@router.get("/suap/callback")
def suap_callback(code: str = "", state: str = "", error: str = "", db: Session = Depends(get_db)):
    if error:
        return RedirectResponse(
            url=_frontend_login_url(error="Acesso cancelado no SUAP"),
            status_code=302,
        )

    if not code or not state or not suap_client.validar_state(state):
        return RedirectResponse(
            url=_frontend_login_url(error="Resposta inválida do SUAP"),
            status_code=302,
        )

    token_data = suap_client.trocar_codigo_por_token(code)
    if not token_data or "error" in token_data:
        mensagem = token_data.get("error", "Erro ao autenticar com o SUAP") if token_data else "Erro ao autenticar com o SUAP"
        return RedirectResponse(
            url=_frontend_login_url(error=mensagem),
            status_code=302,
        )

    suap_data = suap_client.buscar_usuario(token_data["access_token"])
    if not suap_data or "error" in suap_data:
        mensagem = suap_data.get("error", "Erro ao buscar perfil no SUAP") if suap_data else "Erro ao buscar perfil no SUAP"
        return RedirectResponse(
            url=_frontend_login_url(error=mensagem),
            status_code=302,
        )

    try:
        usuario = _provisionar_usuario(suap_data, db)
        access_token = _emitir_token(usuario, db)
    except HTTPException as exc:
        return RedirectResponse(
            url=_frontend_login_url(error=str(exc.detail)),
            status_code=302,
        )

    return RedirectResponse(
        url=_frontend_login_url(token=access_token, tipo=usuario.tipo.value),
        status_code=302,
    )


@router.get("/perfil")
def ver_perfil(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    response_data = {
        "id": usuario.id,
        "cpf": usuario.cpf,
        "matricula": usuario.matricula,
        "nome_completo": usuario.nome_completo,
        "tipo": usuario.tipo,
        "data_registro": usuario.data_registro,
        "data_edicao": usuario.data_edicao,
        "biblioteca": None,
    }

    if usuario.tipo == TipoUsuario.bibliotecario:
        bibliotecario_biblioteca = db.query(BibliotecarioBiblioteca).filter(
            BibliotecarioBiblioteca.usuario_id == usuario.id
        ).first()
        if bibliotecario_biblioteca:
            biblioteca = db.query(Biblioteca).filter(
                Biblioteca.id == bibliotecario_biblioteca.biblioteca_id
            ).first()
            if biblioteca:
                response_data["biblioteca"] = {
                    "id": biblioteca.id,
                    "nome": biblioteca.nome,
                    "campus": biblioteca.campus,
                }

    return response_data
