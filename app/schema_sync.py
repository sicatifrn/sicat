from sqlalchemy import inspect, text


def ensure_database_schema(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    if "fichas_catalograficas" in tables:
        columns = {column["name"] for column in inspector.get_columns("fichas_catalograficas")}
        dialect = engine.dialect.name
        ficha_columns = mysql_ficha_columns() if dialect == "mysql" else generic_ficha_columns()

        with engine.begin() as conn:
            for name, definition in ficha_columns.items():
                if name not in columns:
                    conn.execute(text(f"ALTER TABLE fichas_catalograficas ADD COLUMN {name} {definition}"))

    if "usuarios" in tables and engine.dialect.name == "mysql":
        with engine.begin() as conn:
            indexes = conn.execute(
                text("SHOW INDEX FROM usuarios WHERE Column_name = 'cpf' AND Non_unique = 0")
            ).mappings().all()
            for index in indexes:
                key_name = index.get("Key_name")
                if key_name and key_name != "PRIMARY":
                    conn.execute(text(f"ALTER TABLE usuarios DROP INDEX `{key_name}`"))
            conn.execute(text("ALTER TABLE usuarios MODIFY cpf VARCHAR(11) NOT NULL"))


def mysql_ficha_columns():
    return {
        "id_curto": "VARCHAR(50) NULL",
        "usuario_id": "VARCHAR(36) NULL",
        "autor_nome_completo": "VARCHAR(255) NULL",
        "autor_sobrenome": "VARCHAR(255) NULL",
        "autor_nome_sem_ultimo_sobrenome": "VARCHAR(255) NULL",
        "autor_ultimo_sobrenome": "VARCHAR(255) NULL",
        "orientador_nome_completo": "VARCHAR(255) NULL",
        "orientador_sobrenome": "VARCHAR(255) NULL",
        "orientador_nome_sem_ultimo_sobrenome": "VARCHAR(255) NULL",
        "orientador_ultimo_sobrenome": "VARCHAR(255) NULL",
        "coorientador_nome_completo": "VARCHAR(255) NULL",
        "coorientador_sobrenome": "VARCHAR(255) NULL",
        "coorientador_nome_sem_ultimo_sobrenome": "VARCHAR(255) NULL",
        "coorientador_ultimo_sobrenome": "VARCHAR(255) NULL",
        "titulo": "VARCHAR(500) NULL",
        "subtitulo": "VARCHAR(500) NULL",
        "data_dia": "VARCHAR(2) NULL",
        "data_mes": "VARCHAR(2) NULL",
        "data_ano": "VARCHAR(4) NULL",
        "cidade": "VARCHAR(255) NULL",
        "campus": "VARCHAR(255) NULL",
        "programa": "VARCHAR(255) NULL",
        "nivel_ensino": "VARCHAR(100) NULL",
        "curso": "VARCHAR(255) NULL",
        "palavras_chave": "TEXT NULL",
        "tipo_trabalho": "VARCHAR(100) NULL",
        "status": "ENUM('aguardando_autorizacao','aprovado','negado') NULL DEFAULT 'aguardando_autorizacao'",
        "data_criacao": "DATETIME NULL",
        "imagem_png": "VARCHAR(500) NULL",
        "biblioteca_id": "VARCHAR(36) NULL",
        "pdf_tcc": "VARCHAR(500) NULL",
        "revisor_id": "VARCHAR(36) NULL",
        "data_revisao": "DATETIME NULL",
    }


def generic_ficha_columns():
    return {
        "id_curto": "VARCHAR(50)",
        "usuario_id": "VARCHAR(36)",
        "autor_nome_completo": "VARCHAR(255)",
        "autor_sobrenome": "VARCHAR(255)",
        "autor_nome_sem_ultimo_sobrenome": "VARCHAR(255)",
        "autor_ultimo_sobrenome": "VARCHAR(255)",
        "orientador_nome_completo": "VARCHAR(255)",
        "orientador_sobrenome": "VARCHAR(255)",
        "orientador_nome_sem_ultimo_sobrenome": "VARCHAR(255)",
        "orientador_ultimo_sobrenome": "VARCHAR(255)",
        "coorientador_nome_completo": "VARCHAR(255)",
        "coorientador_sobrenome": "VARCHAR(255)",
        "coorientador_nome_sem_ultimo_sobrenome": "VARCHAR(255)",
        "coorientador_ultimo_sobrenome": "VARCHAR(255)",
        "titulo": "VARCHAR(500)",
        "subtitulo": "VARCHAR(500)",
        "data_dia": "VARCHAR(2)",
        "data_mes": "VARCHAR(2)",
        "data_ano": "VARCHAR(4)",
        "cidade": "VARCHAR(255)",
        "campus": "VARCHAR(255)",
        "programa": "VARCHAR(255)",
        "nivel_ensino": "VARCHAR(100)",
        "curso": "VARCHAR(255)",
        "palavras_chave": "TEXT",
        "tipo_trabalho": "VARCHAR(100)",
        "status": "VARCHAR(50)",
        "data_criacao": "DATETIME",
        "imagem_png": "VARCHAR(500)",
        "biblioteca_id": "VARCHAR(36)",
        "pdf_tcc": "VARCHAR(500)",
        "revisor_id": "VARCHAR(36)",
        "data_revisao": "DATETIME",
    }
