import pytest
from .connection import db
from sqlalchemy.engine import Engine

@pytest.mark.skip(reason="Interação com o Banco")
def test_connect_db():
    assert db.get_engine() is None
    
    db.connect_to_db()
    db_engine = db.get_engine()

    assert db.get_engine() is not None
    assert isinstance(db_engine, Engine)