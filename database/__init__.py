from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Columnas nuevas agregadas a un modelo ya existente en produccion (SQLite):
# db.create_all() solo crea TABLAS faltantes, no columnas nuevas en una
# tabla que ya existe con datos. Se agregan aqui con ALTER TABLE, una sola
# vez cada una (comprueba si ya existen antes de intentarlo).
_NEW_COLUMNS = {
    "companies": [
        ("chain_key", "VARCHAR(255)"),
        ("facebook_url", "VARCHAR(255)"),
        ("linkedin_url", "VARCHAR(255)"),
        ("enrichment_notes", "TEXT"),
        ("enriched_at", "DATETIME"),
    ],
}


def ensure_schema_migrations():
    inspector = db.inspect(db.engine)
    for table_name, columns in _NEW_COLUMNS.items():
        if table_name not in inspector.get_table_names():
            continue
        existing = {col["name"] for col in inspector.get_columns(table_name)}
        for column_name, column_type in columns:
            if column_name not in existing:
                with db.engine.begin() as conn:
                    conn.execute(
                        db.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                    )
