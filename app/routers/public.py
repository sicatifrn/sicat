from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import FichaCatalografica, StatusFicha, Biblioteca
from app.schemas import BibliotecaResponse
from fastapi.responses import Response

router = APIRouter()

@router.get("/validar/{id_curto}")
def validar_ficha(id_curto: str, db: Session = Depends(get_db)):
    ficha = db.query(FichaCatalografica).filter(
        FichaCatalografica.id_curto == id_curto,
        FichaCatalografica.status == StatusFicha.aprovado
    ).first()
    
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não aprovada"
        )
    
    return {
        "valido": True,
        "id_curto": ficha.id_curto,
        "data_criacao": ficha.data_criacao.isoformat(),
        "data_revisao": ficha.data_revisao.isoformat() if ficha.data_revisao else None,
        "revisor_nome": ficha.revisor_nome
    }

@router.get("/validar/{id_curto}/imagem")
def validar_ficha_imagem(id_curto: str, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    ficha = db.query(FichaCatalografica).filter(
        FichaCatalografica.id_curto == id_curto,
        FichaCatalografica.status == StatusFicha.aprovado
    ).first()
    
    if not ficha or not ficha.imagem_png:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não aprovada"
        )
    
    PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
    img_path_str = str(ficha.imagem_png)
    img_path = PUBLIC_DIR / img_path_str
    
    if not img_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo de imagem não encontrado no servidor: {img_path}"
        )
    
    return FileResponse(
        path=str(img_path),
        media_type="image/png"
    )

@router.get("/bibliotecas", response_model=List[BibliotecaResponse])
def listar_bibliotecas(db: Session = Depends(get_db)):
    bibliotecas = db.query(Biblioteca).all()
    return bibliotecas

