from sqlalchemy import inspect, text
import logging

logger = logging.getLogger(__name__)

async def verify_database_schema(engine):
    """Weryfikuje poprawność schematu bazy danych."""
    async with engine.connect() as conn:
        # Sprawdź tabele
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        if not tables:
            logger.error("Brak tabel w bazie danych!")
            return False
        
        # Sprawdź sekwencje
        result = await conn.execute(text("""
            SELECT sequence_name 
            FROM information_schema.sequences
            WHERE sequence_schema = 'public'
        """))
        sequences = result.fetchall()
        
        # Sprawdź indeksy
        for table in tables:
            result = await conn.execute(text(f"""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename = '{table}'
            """))
            indexes = result.fetchall()
            if not indexes:
                logger.warning(f"Tabela {table} nie ma żadnych indeksów!")
        
        return True 