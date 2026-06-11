from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
from pathlib import Path
from app.database import get_db
from app.models import Usuario, FichaCatalografica, BibliotecarioBiblioteca, StatusFicha
from app.schemas import FichaCatalograficaLogResponse, FichaCatalograficaResponse, AprovarNegarRequest
from app.auth_utils import get_bibliotecario_user, get_current_user
from app.ficha_service import decidir_ficha

router = APIRouter()

PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
PDF_DIR = PUBLIC_DIR / "pdfs"

def get_biblioteca_do_bibliotecario(bibliotecario: Usuario, db: Session):
    bibliotecario_biblioteca = db.query(BibliotecarioBiblioteca).filter(
        BibliotecarioBiblioteca.usuario_id == bibliotecario.id
    ).first()
    
    if not bibliotecario_biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bibliotecário não está associado a nenhuma biblioteca"
        )
    
    return bibliotecario_biblioteca.biblioteca_id

@router.get("/solicitacoes", response_model=List[FichaCatalograficaResponse])
def ver_solicitacoes(
    bibliotecario: Usuario = Depends(get_bibliotecario_user),
    db: Session = Depends(get_db)
):
    biblioteca_id = get_biblioteca_do_bibliotecario(bibliotecario, db)
    
    fichas = db.query(FichaCatalografica).options(
        joinedload(FichaCatalografica.revisor)
    ).filter(
        FichaCatalografica.biblioteca_id == biblioteca_id
    ).order_by(FichaCatalografica.data_criacao.desc()).all()
    
    return fichas

@router.post("/solicitacoes/{ficha_id}/aprovacao")
def aprovar_negar_solicitacao(
    ficha_id: str,
    acao: AprovarNegarRequest,
    bibliotecario: Usuario = Depends(get_bibliotecario_user),
    db: Session = Depends(get_db)
):
    biblioteca_id = get_biblioteca_do_bibliotecario(bibliotecario, db)
    
    ficha = db.query(FichaCatalografica).options(
        joinedload(FichaCatalografica.biblioteca),
        joinedload(FichaCatalografica.usuario),
        joinedload(FichaCatalografica.revisor),
    ).filter(
        FichaCatalografica.id == ficha_id,
        FichaCatalografica.biblioteca_id == biblioteca_id
    ).first()
    
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não pertence à sua biblioteca"
        )
    
    ficha = decidir_ficha(db, ficha, bibliotecario, acao.aprovado, acao.observacao)
    
    return {"message": "Status atualizado com sucesso", "ficha": ficha}

@router.get("/solicitacoes/{ficha_id}/logs", response_model=List[FichaCatalograficaLogResponse])
def listar_logs_solicitacao(
    ficha_id: str,
    bibliotecario: Usuario = Depends(get_bibliotecario_user),
    db: Session = Depends(get_db)
):
    biblioteca_id = get_biblioteca_do_bibliotecario(bibliotecario, db)

    ficha = db.query(FichaCatalografica).filter(
        FichaCatalografica.id == ficha_id,
        FichaCatalografica.biblioteca_id == biblioteca_id
    ).first()

    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não pertence à sua biblioteca"
        )

    return sorted(ficha.logs, key=lambda log: log.data_criacao, reverse=True)

@router.get("/solicitacoes/{ficha_id}/pdf")
def visualizar_pdf(
    ficha_id: str,
    bibliotecario: Usuario = Depends(get_bibliotecario_user),
    db: Session = Depends(get_db)
):
    biblioteca_id = get_biblioteca_do_bibliotecario(bibliotecario, db)
    
    ficha = db.query(FichaCatalografica).filter(
        FichaCatalografica.id == ficha_id,
        FichaCatalografica.biblioteca_id == biblioteca_id
    ).first()
    
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não pertence à sua biblioteca"
        )
    
    if not ficha.pdf_tcc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF não disponível para esta ficha"
        )
    
    pdf_path_str = str(ficha.pdf_tcc)
    pdf_path = PUBLIC_DIR / pdf_path_str
    
    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo PDF não encontrado no servidor: {pdf_path}"
        )
    
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"tcc_{ficha.id_curto}.pdf"
    )


