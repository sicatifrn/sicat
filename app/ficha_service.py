from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.ficha_utils import gerar_imagem_png
from app.models import FichaCatalografica, FichaCatalograficaLog, StatusFicha, Usuario


def limpar_cpf(cpf: str | None) -> str:
    return "".join(ch for ch in str(cpf or "") if ch.isdigit())


def validar_revisor(ficha: FichaCatalografica, usuario: Usuario):
    if limpar_cpf(ficha.usuario.cpf) and limpar_cpf(ficha.usuario.cpf) == limpar_cpf(usuario.cpf):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não pode revisar uma ficha vinculada ao seu próprio CPF",
        )


def registrar_log(
    db: Session,
    ficha: FichaCatalografica,
    usuario: Usuario,
    acao: str,
    status_anterior: str | None,
    status_novo: str | None,
    observacao: str | None = None,
):
    db.add(
        FichaCatalograficaLog(
            ficha_id=ficha.id,
            usuario_id=usuario.id,
            acao=acao,
            status_anterior=status_anterior,
            status_novo=status_novo,
            observacao=(observacao or "").strip() or None,
        )
    )


def decidir_ficha(db: Session, ficha: FichaCatalografica, usuario: Usuario, aprovado: bool, observacao: str | None = None):
    validar_revisor(ficha, usuario)

    if ficha.status != StatusFicha.aguardando_autorizacao:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta ficha já foi analisada",
        )

    status_anterior = ficha.status.value
    ficha.status = StatusFicha.aprovado if aprovado else StatusFicha.negado
    ficha.revisor = usuario
    ficha.revisor_id = usuario.id
    ficha.data_revisao = datetime.utcnow()

    if aprovado:
        try:
            ficha.imagem_png = gerar_imagem_png(ficha)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível gerar a imagem da ficha",
            )

    registrar_log(
        db=db,
        ficha=ficha,
        usuario=usuario,
        acao="aprovacao" if aprovado else "negacao",
        status_anterior=status_anterior,
        status_novo=ficha.status.value,
        observacao=observacao,
    )

    db.commit()
    db.refresh(ficha)
    return ficha
