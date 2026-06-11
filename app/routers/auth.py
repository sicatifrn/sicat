from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db, matriculas_admin_configuradas
from app.models import Usuario, JWTAuth, TipoUsuario
from app.schemas import (
    UsuarioCreate, UsuarioResponse, LoginRequest, LoginResponse,
    RecuperarAcessoRequest, RegistroRequest
)
from pydantic import BaseModel
from app.auth_utils import (
    verify_password, get_password_hash, create_access_token,
    get_current_user
)
from app.suap_client import SUAPClient
from datetime import datetime, timedelta

router = APIRouter()
suap_client = SUAPClient()

@router.post("/registro", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registro(
    registro_data: RegistroRequest,
    db: Session = Depends(get_db)
):
    suap_data = suap_client.validar_credenciais(registro_data.matricula, registro_data.senha_suap)
    if not suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais do SUAP inválidas ou erro ao conectar com o SUAP"
        )
    
    if "error" in suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=suap_data.get("error", "Erro ao validar credenciais com o SUAP")
        )
    
    cpf_raw = suap_data.get("cpf", "") or ""
    cpf_limpo = cpf_raw.replace(".", "").replace("-", "").replace(" ", "")

    if db.query(Usuario).filter(Usuario.matricula == registro_data.matricula).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Matrícula já cadastrada"
        )
    
    if registro_data.nova_senha != registro_data.confirmar_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senhas não coincidem"
        )

    matricula_final = (suap_data.get("matricula", registro_data.matricula) or "").strip()
    admins = matriculas_admin_configuradas()
    tipo = TipoUsuario.admin if matricula_final in admins else TipoUsuario.default

    novo_usuario = Usuario(
        cpf=cpf_limpo,
        matricula=matricula_final,
        nome_completo=suap_data.get("nome_completo", ""),
        senha=get_password_hash(registro_data.nova_senha),
        tipo=tipo
    )
    
    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)
    
    return novo_usuario

@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.matricula == login_data.matricula).first()
    
    if not usuario or not verify_password(login_data.senha, usuario.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Matrícula ou senha incorretas"
        )

    if usuario.matricula.strip() in matriculas_admin_configuradas() and usuario.tipo == TipoUsuario.default:
        usuario.tipo = TipoUsuario.admin
        usuario.data_edicao = datetime.utcnow()
        db.commit()
        db.refresh(usuario)

    access_token_expires = timedelta(hours=72)
    access_token = create_access_token(
        data={"sub": usuario.id, "tipo": usuario.tipo.value},
        expires_delta=access_token_expires
    )
    
    token_db = JWTAuth(
        usuario_id=usuario.id,
        token=access_token,
        expiracao=datetime.utcnow() + access_token_expires
    )
    db.add(token_db)
    db.commit()
    
    return {"token": access_token, "tipo": usuario.tipo}

class ValidarSuapRequest(BaseModel):
    matricula: str
    senha_suap: str

@router.post("/validar-suap")
def validar_suap(request: ValidarSuapRequest):
    suap_data = suap_client.validar_credenciais(request.matricula, request.senha_suap)
    if not suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais do SUAP inválidas ou erro ao conectar com o SUAP"
        )
    
    if "error" in suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=suap_data.get("error", "Erro ao validar credenciais com o SUAP")
        )
    
    return {
        "valido": True,
        "cpf": suap_data.get("cpf", ""),
        "matricula": suap_data.get("matricula", request.matricula),
        "nome_completo": suap_data.get("nome_completo", ""),
        "email": suap_data.get("email", ""),
        "campus": suap_data.get("campus", ""),
        "curso": suap_data.get("curso", "")
    }

@router.post("/recuperar-acesso", status_code=status.HTTP_200_OK)
def recuperar_acesso(recuperar_data: RecuperarAcessoRequest, db: Session = Depends(get_db)):
    suap_data = suap_client.validar_credenciais(
        recuperar_data.matricula,
        recuperar_data.senha_suap
    )
    if not suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais do SUAP inválidas ou erro ao conectar com o SUAP"
        )
    
    if "error" in suap_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=suap_data.get("error", "Erro ao validar credenciais com o SUAP")
        )
    
    usuario = db.query(Usuario).filter(Usuario.matricula == recuperar_data.matricula).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    if recuperar_data.nova_senha != recuperar_data.confirmar_senha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senhas não coincidem"
        )
    
    usuario.senha = get_password_hash(recuperar_data.nova_senha)
    usuario.data_edicao = datetime.utcnow()
    db.commit()
    
    return {"message": "Senha alterada com sucesso"}

@router.get("/perfil")
def ver_perfil(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import BibliotecarioBiblioteca, Biblioteca, TipoUsuario
    
    response_data = {
        "id": usuario.id,
        "cpf": usuario.cpf,
        "matricula": usuario.matricula,
        "nome_completo": usuario.nome_completo,
        "tipo": usuario.tipo,
        "data_registro": usuario.data_registro,
        "data_edicao": usuario.data_edicao,
        "biblioteca": None
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
                    "campus": biblioteca.campus
                }
    
    return response_data

