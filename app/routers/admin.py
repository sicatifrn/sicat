from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import Usuario, FichaCatalografica, TipoUsuario, Biblioteca, BibliotecarioBiblioteca
from app.schemas import (
    FichaCatalograficaLogResponse, FichaCatalograficaResponse, UsuarioResponse, AprovarNegarRequest, ModificarTipoRequest,
    BibliotecaCreate, BibliotecaResponse, AdicionarBibliotecarioRequest, BibliotecarioBibliotecaResponse
)
from app.auth_utils import get_admin_user
from app.ficha_service import decidir_ficha

router = APIRouter()

@router.get("/fichas", response_model=List[FichaCatalograficaResponse])
def ver_todas_fichas(
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    fichas = db.query(FichaCatalografica).options(
        joinedload(FichaCatalografica.revisor)
    ).all()
    return fichas

@router.post("/fichas/{ficha_id}/aprovacao")
def aprovar_negar_ficha(
    ficha_id: str,
    acao: AprovarNegarRequest,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    ficha = db.query(FichaCatalografica).options(
        joinedload(FichaCatalografica.biblioteca),
        joinedload(FichaCatalografica.usuario),
        joinedload(FichaCatalografica.revisor),
    ).filter(FichaCatalografica.id == ficha_id).first()
    
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada"
        )
    
    ficha = decidir_ficha(db, ficha, admin, acao.aprovado, acao.observacao)
    
    return {"message": "Status atualizado com sucesso", "ficha": ficha}

@router.get("/fichas/{ficha_id}/logs", response_model=List[FichaCatalograficaLogResponse])
def listar_logs_ficha(
    ficha_id: str,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    ficha = db.query(FichaCatalografica).filter(FichaCatalografica.id == ficha_id).first()

    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada"
        )

    return sorted(ficha.logs, key=lambda log: log.data_criacao, reverse=True)

@router.get("/usuarios")
def ver_todos_usuarios(
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    usuarios = db.query(Usuario).all()
    resultado = []
    for usuario in usuarios:
        usuario_dict = {
            "id": usuario.id,
            "cpf": usuario.cpf,
            "matricula": usuario.matricula,
            "nome_completo": usuario.nome_completo,
            "tipo": usuario.tipo,
            "data_registro": usuario.data_registro,
            "data_edicao": usuario.data_edicao
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
                    usuario_dict["biblioteca"] = {
                        "id": biblioteca.id,
                        "nome": biblioteca.nome,
                        "campus": biblioteca.campus
                    }
        resultado.append(usuario_dict)
    return resultado

@router.get("/usuarios/{usuario_id}/fichas", response_model=List[FichaCatalograficaResponse])
def ver_fichas_por_usuario(
    usuario_id: str,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    fichas = db.query(FichaCatalografica).filter(
        FichaCatalografica.usuario_id == usuario_id
    ).all()
    return fichas

@router.patch("/usuarios/{usuario_id}/tipo")
def modificar_tipo_usuario(
    usuario_id: str,
    request: ModificarTipoRequest,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    if admin.id == usuario_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível alterar seu próprio tipo"
        )
    
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    usuario.tipo = request.tipo
    db.commit()
    
    return {"message": "Tipo de usuário alterado com sucesso", "usuario": usuario}

@router.post("/bibliotecas", response_model=BibliotecaResponse, status_code=status.HTTP_201_CREATED)
def criar_biblioteca(
    biblioteca_data: BibliotecaCreate,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    nova_biblioteca = Biblioteca(**biblioteca_data.model_dump())
    db.add(nova_biblioteca)
    db.commit()
    db.refresh(nova_biblioteca)
    return nova_biblioteca

@router.get("/bibliotecas", response_model=List[BibliotecaResponse])
def listar_bibliotecas(
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    bibliotecas = db.query(Biblioteca).all()
    return bibliotecas

@router.post("/bibliotecas/adicionar-bibliotecario", response_model=BibliotecarioBibliotecaResponse, status_code=status.HTTP_201_CREATED)
def adicionar_bibliotecario(
    request: AdicionarBibliotecarioRequest,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    usuario = db.query(Usuario).filter(Usuario.id == request.usuario_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    biblioteca = db.query(Biblioteca).filter(Biblioteca.id == request.biblioteca_id).first()
    if not biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biblioteca não encontrada"
        )
    
    if usuario.tipo != TipoUsuario.bibliotecario:
        usuario.tipo = TipoUsuario.bibliotecario
        db.add(usuario)
    
    bibliotecario_biblioteca = BibliotecarioBiblioteca(
        usuario_id=request.usuario_id,
        biblioteca_id=request.biblioteca_id
    )
    
    db.add(bibliotecario_biblioteca)
    db.commit()
    db.refresh(usuario)
    db.refresh(bibliotecario_biblioteca)
    
    return bibliotecario_biblioteca

@router.get("/bibliotecas/{biblioteca_id}/bibliotecarios", response_model=List[UsuarioResponse])
def listar_bibliotecarios_biblioteca(
    biblioteca_id: str,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    biblioteca = db.query(Biblioteca).filter(Biblioteca.id == biblioteca_id).first()
    if not biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biblioteca não encontrada"
        )
    
    bibliotecarios_ids = [
        bb.usuario_id for bb in db.query(BibliotecarioBiblioteca).filter(
            BibliotecarioBiblioteca.biblioteca_id == biblioteca_id
        ).all()
    ]
    
    bibliotecarios = db.query(Usuario).filter(Usuario.id.in_(bibliotecarios_ids)).all()
    return bibliotecarios

@router.patch("/bibliotecas/{biblioteca_id}", response_model=BibliotecaResponse)
def editar_biblioteca(
    biblioteca_id: str,
    biblioteca_data: BibliotecaCreate,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    biblioteca = db.query(Biblioteca).filter(Biblioteca.id == biblioteca_id).first()
    if not biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biblioteca não encontrada"
        )
    
    biblioteca.nome = biblioteca_data.nome
    biblioteca.campus = biblioteca_data.campus
    biblioteca.data_edicao = datetime.utcnow()
    
    db.commit()
    db.refresh(biblioteca)
    
    return biblioteca

@router.delete("/bibliotecas/{biblioteca_id}/bibliotecarios/{usuario_id}")
def remover_bibliotecario(
    biblioteca_id: str,
    usuario_id: str,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    bibliotecario_biblioteca = db.query(BibliotecarioBiblioteca).filter(
        BibliotecarioBiblioteca.biblioteca_id == biblioteca_id,
        BibliotecarioBiblioteca.usuario_id == usuario_id
    ).first()
    
    if not bibliotecario_biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bibliotecário não encontrado nesta biblioteca"
        )
    
    db.delete(bibliotecario_biblioteca)
    db.commit()
    
    return {"message": "Bibliotecário removido da biblioteca com sucesso"}

@router.delete("/bibliotecas/{biblioteca_id}")
def deletar_biblioteca(
    biblioteca_id: str,
    admin: Usuario = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    biblioteca = db.query(Biblioteca).filter(Biblioteca.id == biblioteca_id).first()
    if not biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biblioteca não encontrada"
        )
    
    fichas_count = db.query(FichaCatalografica).filter(
        FichaCatalografica.biblioteca_id == biblioteca_id
    ).count()
    
    if fichas_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível deletar a biblioteca. Existem {fichas_count} ficha(s) associada(s) a ela."
        )
    
    db.query(BibliotecarioBiblioteca).filter(
        BibliotecarioBiblioteca.biblioteca_id == biblioteca_id
    ).delete()
    
    db.delete(biblioteca)
    db.commit()
    
    return {"message": "Biblioteca deletada com sucesso"}
