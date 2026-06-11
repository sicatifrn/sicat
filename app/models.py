from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base
import enum

def generate_uuid():
    return uuid.uuid4().hex

class TipoUsuario(str, enum.Enum):
    default = "default"
    admin = "admin"
    bibliotecario = "bibliotecario"

class StatusFicha(str, enum.Enum):
    aguardando_autorizacao = "aguardando_autorizacao"
    aprovado = "aprovado"
    negado = "negado"

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    cpf = Column(String(11), nullable=False)
    matricula = Column(String(50), unique=True, nullable=False)
    nome_completo = Column(String(255), nullable=False)
    senha = Column(String(255), nullable=False)
    tipo = Column(Enum(TipoUsuario), default=TipoUsuario.default, nullable=False)
    data_registro = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_edicao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    fichas = relationship("FichaCatalografica", back_populates="usuario", foreign_keys="FichaCatalografica.usuario_id")
    fichas_revisadas = relationship("FichaCatalografica", back_populates="revisor", foreign_keys="FichaCatalografica.revisor_id")
    tokens = relationship("JWTAuth", back_populates="usuario")
    bibliotecas = relationship("BibliotecarioBiblioteca", back_populates="usuario")

class FichaCatalografica(Base):
    __tablename__ = "fichas_catalograficas"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    id_curto = Column(String(50), unique=True, nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    
    autor_nome_completo = Column(String(255), nullable=False)
    autor_sobrenome = Column(String(255), nullable=False)
    autor_nome_sem_ultimo_sobrenome = Column(String(255), nullable=False)
    autor_ultimo_sobrenome = Column(String(255), nullable=False)
    
    orientador_nome_completo = Column(String(255), nullable=True)
    orientador_sobrenome = Column(String(255), nullable=True)
    orientador_nome_sem_ultimo_sobrenome = Column(String(255), nullable=True)
    orientador_ultimo_sobrenome = Column(String(255), nullable=True)
    
    coorientador_nome_completo = Column(String(255), nullable=True)
    coorientador_sobrenome = Column(String(255), nullable=True)
    coorientador_nome_sem_ultimo_sobrenome = Column(String(255), nullable=True)
    coorientador_ultimo_sobrenome = Column(String(255), nullable=True)
    
    titulo = Column(String(500), nullable=False)
    subtitulo = Column(String(500), nullable=True)
    data_dia = Column(String(2), nullable=False)
    data_mes = Column(String(2), nullable=False)
    data_ano = Column(String(4), nullable=False)
    cidade = Column(String(255), nullable=False)
    campus = Column(String(255), nullable=False)
    programa = Column(String(255), nullable=False)
    nivel_ensino = Column(String(100), nullable=False)
    curso = Column(String(255), nullable=False)
    palavras_chave = Column(Text, nullable=False)
    tipo_trabalho = Column(String(100), nullable=False)
    
    status = Column(Enum(StatusFicha), default=StatusFicha.aguardando_autorizacao, nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    imagem_png = Column(String(500), nullable=True)  
    biblioteca_id = Column(String(36), ForeignKey("bibliotecas.id"), nullable=True)
    pdf_tcc = Column(String(500), nullable=True)  
    revisor_id = Column(String(36), ForeignKey("usuarios.id"), nullable=True)
    data_revisao = Column(DateTime, nullable=True)
    
    usuario = relationship("Usuario", back_populates="fichas", foreign_keys=[usuario_id])
    revisor = relationship("Usuario", back_populates="fichas_revisadas", foreign_keys=[revisor_id])
    biblioteca = relationship("Biblioteca", back_populates="fichas")
    logs = relationship("FichaCatalograficaLog", back_populates="ficha")

    @property
    def revisor_nome(self):
        return self.revisor.nome_completo if self.revisor else None

    @property
    def revisor_matricula(self):
        return self.revisor.matricula if self.revisor else None

    @property
    def revisor_cpf(self):
        return self.revisor.cpf if self.revisor else None

class JWTAuth(Base):
    __tablename__ = "jwt_auth"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    token = Column(Text, nullable=False)
    expiracao = Column(DateTime, nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    usuario = relationship("Usuario", back_populates="tokens")

class Biblioteca(Base):
    __tablename__ = "bibliotecas"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    nome = Column(String(255), nullable=False)
    campus = Column(String(255), nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    data_edicao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    bibliotecarios = relationship("BibliotecarioBiblioteca", back_populates="biblioteca")
    fichas = relationship("FichaCatalografica", back_populates="biblioteca")

class BibliotecarioBiblioteca(Base):
    __tablename__ = "bibliotecarios_bibliotecas"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    biblioteca_id = Column(String(36), ForeignKey("bibliotecas.id"), nullable=False)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    usuario = relationship("Usuario", back_populates="bibliotecas")
    biblioteca = relationship("Biblioteca", back_populates="bibliotecarios")

class FichaCatalograficaLog(Base):
    __tablename__ = "fichas_catalograficas_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ficha_id = Column(String(36), ForeignKey("fichas_catalograficas.id"), nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    acao = Column(String(50), nullable=False)
    status_anterior = Column(String(50), nullable=True)
    status_novo = Column(String(50), nullable=True)
    observacao = Column(Text, nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow, nullable=False)

    ficha = relationship("FichaCatalografica", back_populates="logs")
    usuario = relationship("Usuario")

    @property
    def usuario_nome(self):
        return self.usuario.nome_completo if self.usuario else None

