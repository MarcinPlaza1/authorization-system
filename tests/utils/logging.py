import logging
import sys
from pathlib import Path

def setup_test_logging():
    """Konfiguracja logowania dla testów."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.DEBUG,
        format=log_format,
        handlers=[
            logging.FileHandler(Path(__file__).parent.parent / "tests.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Logowanie SQL
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    # Logowanie testów
    logger = logging.getLogger('pytest')
    logger.setLevel(logging.DEBUG) 