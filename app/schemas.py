from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import datetime, date
from app.models import TipoUsuario, StatusFicha

NIVEIS_ENSINO = {
    "tecnico": "Técnico",
    "graduacao": "Graduação",
    "superior": "Graduação",
    "especializacao": "Especialização",
    "pos_graduacao": "Especialização",
    "mestrado": "Mestrado",
    "doutorado": "Doutorado",
}

TIPOS_TRABALHO = {
    "tcc": "TCC",
    "monografia": "Monografia",
    "dissertacao": "Dissertação",
    "tese": "Tese",
    "artigo": "Artigo",
    "anais": "Anais",
    "livro_fisico": "Livro físico",
    "ebook": "E-book",
    "e_book": "E-book",
    "produto_educacional": "Produto educacional",
}

class UsuarioBase(BaseModel):
    cpf: str
    matricula: str
    nome_completo: str

class UsuarioCreate(UsuarioBase):
    senha: str
    confirmar_senha: str

class RegistroRequest(BaseModel):
    matricula: str
    senha_suap: str
    nova_senha: str
    confirmar_senha: str

class UsuarioResponse(UsuarioBase):
    id: str
    tipo: TipoUsuario
    data_registro: datetime
    data_edicao: datetime
    biblioteca: Optional[dict] = None  
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    matricula: str
    senha: str

class LoginResponse(BaseModel):
    token: str
    tipo: TipoUsuario

class RecuperarAcessoRequest(BaseModel):
    matricula: str
    senha_suap: str
    nova_senha: str
    confirmar_senha: str

class FichaCatalograficaBase(BaseModel):
    autor_nome_completo: str
    autor_sobrenome: Optional[str] = None
    autor_nome_sem_ultimo_sobrenome: Optional[str] = None
    autor_ultimo_sobrenome: Optional[str] = None
    orientador_nome_completo: Optional[str] = None
    orientador_sobrenome: Optional[str] = None
    orientador_nome_sem_ultimo_sobrenome: Optional[str] = None
    orientador_ultimo_sobrenome: Optional[str] = None
    coorientador_nome_completo: Optional[str] = None
    coorientador_sobrenome: Optional[str] = None
    coorientador_nome_sem_ultimo_sobrenome: Optional[str] = None
    coorientador_ultimo_sobrenome: Optional[str] = None
    titulo: str
    subtitulo: Optional[str] = None
    data_dia: str
    data_mes: str
    data_ano: str
    cidade: str
    campus: str
    programa: str
    nivel_ensino: str
    curso: str
    palavras_chave: str
    tipo_trabalho: str

    @field_validator(
        "autor_nome_completo",
        "orientador_nome_completo",
        "coorientador_nome_completo",
        "titulo",
        "subtitulo",
        "cidade",
        "campus",
        "programa",
        "curso",
        "palavras_chave",
        mode="before",
    )
    @classmethod
    def limpar_texto(cls, value):
        if value is None:
            return value
        value = str(value).strip()
        return value or None

    @field_validator("nivel_ensino", mode="before")
    @classmethod
    def validar_nivel(cls, value):
        value = (str(value or "").strip())
        chave = value.lower().replace("ç", "c").replace("ã", "a").replace("é", "e").replace("í", "i").replace("ó", "o")
        chave = chave.replace("-", "_").replace(" ", "_")
        if chave not in NIVEIS_ENSINO:
            raise ValueError("Selecione um nível de ensino válido")
        return NIVEIS_ENSINO[chave]

    @field_validator("tipo_trabalho", mode="before")
    @classmethod
    def validar_tipo_trabalho(cls, value):
        value = (str(value or "").strip())
        chave = value.lower().replace("ç", "c").replace("ã", "a").replace("é", "e").replace("í", "i").replace("ó", "o")
        chave = chave.replace("-", "_").replace(" ", "_")
        if chave not in TIPOS_TRABALHO:
            raise ValueError("Selecione um tipo de trabalho válido")
        return TIPOS_TRABALHO[chave]

    @model_validator(mode="after")
    def normalizar_ficha(self):
        self.autor_sobrenome, self.autor_nome_sem_ultimo_sobrenome, self.autor_ultimo_sobrenome = dividir_nome(
            self.autor_nome_completo
        )

        if self.orientador_nome_completo:
            (
                self.orientador_sobrenome,
                self.orientador_nome_sem_ultimo_sobrenome,
                self.orientador_ultimo_sobrenome,
            ) = dividir_nome(self.orientador_nome_completo)
        else:
            self.orientador_sobrenome = None
            self.orientador_nome_sem_ultimo_sobrenome = None
            self.orientador_ultimo_sobrenome = None

        if self.coorientador_nome_completo:
            (
                self.coorientador_sobrenome,
                self.coorientador_nome_sem_ultimo_sobrenome,
                self.coorientador_ultimo_sobrenome,
            ) = dividir_nome(self.coorientador_nome_completo)
        else:
            self.coorientador_sobrenome = None
            self.coorientador_nome_sem_ultimo_sobrenome = None
            self.coorientador_ultimo_sobrenome = None

        try:
            dia = int(str(self.data_dia).strip())
            mes = int(str(self.data_mes).strip())
            ano = int(str(self.data_ano).strip())
            if ano < 1900 or ano > datetime.utcnow().year + 1:
                raise ValueError
            date(ano, mes, dia)
        except ValueError:
            raise ValueError("Informe uma data válida")

        self.data_dia = f"{dia:02d}"
        self.data_mes = f"{mes:02d}"
        self.data_ano = f"{ano:04d}"
        return self

class FichaCatalograficaCreate(FichaCatalograficaBase):
    biblioteca_id: str

class FichaCatalograficaResponse(FichaCatalograficaBase):
    id: str
    id_curto: str
    status: StatusFicha
    data_criacao: datetime
    imagem_png: Optional[str] = None 
    pdf_tcc: Optional[str] = None
    biblioteca_id: Optional[str] = None
    revisor_id: Optional[str] = None
    revisor_nome: Optional[str] = None
    revisor_matricula: Optional[str] = None
    revisor_cpf: Optional[str] = None
    data_revisao: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AprovarNegarRequest(BaseModel):
    aprovado: bool
    observacao: Optional[str] = None

class FichaCatalograficaLogResponse(BaseModel):
    id: str
    ficha_id: str
    usuario_id: str
    usuario_nome: Optional[str] = None
    acao: str
    status_anterior: Optional[str] = None
    status_novo: Optional[str] = None
    observacao: Optional[str] = None
    data_criacao: datetime

    class Config:
        from_attributes = True

class ModificarTipoRequest(BaseModel):
    tipo: TipoUsuario

class BibliotecaBase(BaseModel):
    nome: str
    campus: str

class BibliotecaCreate(BibliotecaBase):
    pass

class BibliotecaResponse(BibliotecaBase):
    id: str
    data_criacao: datetime
    data_edicao: datetime
    
    class Config:
        from_attributes = True

class AdicionarBibliotecarioRequest(BaseModel):
    usuario_id: str
    biblioteca_id: str

class BibliotecarioBibliotecaResponse(BaseModel):
    id: str
    usuario_id: str
    biblioteca_id: str
    data_criacao: datetime
    
    class Config:
        from_attributes = True

def dividir_nome(nome: str) -> tuple[str, str, str]:
    partes = [parte for parte in str(nome or "").strip().split() if parte]
    if not partes:
        raise ValueError("Informe o nome completo")
    if len(partes) == 1:
        return partes[0], partes[0], partes[0]
    sobrenome = " ".join(partes[1:])
    nome_sem_ultimo = " ".join(partes[:-1])
    ultimo_sobrenome = partes[-1]
    return sobrenome, nome_sem_ultimo, ultimo_sobrenome
