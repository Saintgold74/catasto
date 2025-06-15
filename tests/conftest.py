# File di configurazione pytest - versione semplificata per iniziare
import pytest
import sys
import os

# Aggiungi la directory principale al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def mock_db_manager():
    """Mock semplice del database manager per iniziare"""
    from unittest.mock import Mock
    
    mock = Mock()
    mock.schema = 'catasto'
    mock.get_all_comuni.return_value = []
    mock.get_possessori_by_comune.return_value = []
    mock.get_partite_by_comune.return_value = []
    
    return mock
