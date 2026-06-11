from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, DatabaseError
from typing import List, Optional
from pydantic import ValidationError
from app.database import get_db
from app.models import Usuario, FichaCatalografica, StatusFicha, Biblioteca
from app.schemas import FichaCatalograficaCreate, FichaCatalograficaResponse
from app.auth_utils import get_current_user
from app.ficha_utils import gerar_id_curto, gerar_imagem_png
from datetime import datetime
import json
import traceback
import os
from pathlib import Path

router = APIRouter()

PUBLIC_DIR = Path(__file__).parent.parent.parent / "public"
PUBLIC_DIR.mkdir(exist_ok=True)
PDF_DIR = PUBLIC_DIR / "pdfs"
PDF_DIR.mkdir(exist_ok=True)

@router.post("/", response_model=FichaCatalograficaResponse, status_code=status.HTTP_201_CREATED)
async def criar_ficha(
    ficha_json: str = Form(...),
    pdf_tcc: Optional[UploadFile] = File(None),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        ficha_data_dict = json.loads(ficha_json)
        ficha_data = FichaCatalograficaCreate(**ficha_data_dict)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados da ficha inválidos"
        )
    except ValidationError as e:
        erro = e.errors()[0] if e.errors() else {}
        mensagem = erro.get("msg", "Dados da ficha inválidos")
        if mensagem.startswith("Value error, "):
            mensagem = mensagem.replace("Value error, ", "", 1)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=mensagem
        )
    
    biblioteca = db.query(Biblioteca).filter(Biblioteca.id == ficha_data.biblioteca_id).first()
    if not biblioteca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Biblioteca selecionada não encontrada"
        )
    
    ano_atual = int(ficha_data.data_ano)
    count = db.query(FichaCatalografica).filter(
        FichaCatalografica.data_criacao >= datetime(ano_atual, 1, 1)
    ).count()
    id_curto = gerar_id_curto(ano_atual, count + 1)
    
    pdf_path_str = None
    if pdf_tcc:
        if pdf_tcc.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O arquivo deve ser um PDF"
            )
        
        pdf_bytes = await pdf_tcc.read()
        filename = f"{id_curto}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = PDF_DIR / filename
        pdf_path.write_bytes(pdf_bytes)
        pdf_path_str = f"pdfs/{filename}"
    
    nova_ficha = FichaCatalografica(
        id_curto=id_curto,
        usuario_id=usuario.id,
        pdf_tcc=pdf_path_str,
        **ficha_data.model_dump()
    )
    
    try:
        db.add(nova_ficha)
        db.commit()
        db.refresh(nova_ficha)
    except Exception:
        db.rollback()
        if pdf_path_str:
            pdf_path = PDF_DIR / pdf_path_str.split('/')[-1]
            if pdf_path.exists():
                try:
                    pdf_path.unlink()
                except:
                    pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível criar a ficha. Verifique os dados e tente novamente."
        )
    
    return nova_ficha

@router.get("/minhas", response_model=List[FichaCatalograficaResponse])
def ver_minhas_fichas(
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fichas = db.query(FichaCatalografica).filter(
        FichaCatalografica.usuario_id == usuario.id
    ).all()
    return fichas

@router.get("/{ficha_id}/download")
def baixar_ficha(
    ficha_id: str,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ficha = db.query(FichaCatalografica).filter(
        FichaCatalografica.id == ficha_id,
        FichaCatalografica.usuario_id == usuario.id,
        FichaCatalografica.status == StatusFicha.aprovado
    ).first()
    
    if not ficha:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficha não encontrada ou não aprovada"
        )
    
    if not ficha.imagem_png:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagem não disponível"
        )
    
    img_path_str = str(ficha.imagem_png)
    img_path = PUBLIC_DIR / img_path_str
    
    if not img_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo de imagem não encontrado no servidor: {img_path}"
        )
    
    return FileResponse(
        path=str(img_path),
        media_type="image/png",
        filename=f"ficha_{ficha.id_curto}.png"
    )

