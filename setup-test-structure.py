#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per creare la struttura di test nel progetto
File: setup_test_structure.py
"""

import os
import sys
from pathlib import Path

def create_test_structure():
    """Crea la struttura delle directory e file di test"""
    
    # Directory base del progetto (dove si trova questo script)
    base_dir = Path.cwd()
    tests_dir = base_dir / "tests"
    
    print(f"📁 Creazione struttura test in: {base_dir}")
    
    # Crea directory principali
    directories = [
        tests_dir,
        tests_dir / "unit",
        tests_dir / "integration",
        tests_dir / "fixtures",
        tests_dir / "reports"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Creata directory: {directory.relative_to(base_dir)}")
    
    # Crea __init__.py files
    init_files = [
        tests_dir / "__init__.py",
        tests_dir / "unit" / "__init__.py",
        tests_dir / "integration" / "__init__.py"
    ]
    
    for init_file in init_files:
        init_file.touch()
        print(f"✅ Creato: {init_file.relative_to(base_dir)}")
    
    # Contenuto dei file di test principali
    files_content = {
        "conftest.py": '''# File di configurazione pytest - versione semplificata per iniziare
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
''',

        "test_basic.py": '''"""Test base per verificare il setup"""
import pytest

def test_import_modules():
    """Test che i moduli principali siano importabili"""
    try:
        import catasto_db_manager
        assert True
    except ImportError:
        pytest.skip("catasto_db_manager non trovato")
    
    try:
        import gui_widgets
        assert True
    except ImportError:
        pytest.skip("gui_widgets non trovato")

def test_basic_math():
    """Test semplice per verificare che pytest funzioni"""
    assert 2 + 2 == 4
    assert 3 * 3 == 9

class TestBasicSetup:
    """Test classe base"""
    
    def test_pytest_is_working(self):
        """Verifica che pytest stia funzionando"""
        assert True
    
    def test_fixture_access(self, mock_db_manager):
        """Verifica accesso alle fixture"""
        assert mock_db_manager is not None
        assert hasattr(mock_db_manager, 'schema')
''',

        "run_tests.py": '''#!/usr/bin/env python3
"""Runner semplificato per i test"""
import sys
import os
import pytest

# Aggiungi la directory principale al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    """Esegui i test"""
    print("🧪 Esecuzione test Catasto Storico...")
    print(f"📁 Directory corrente: {os.getcwd()}")
    
    # Determina cosa eseguire
    if len(sys.argv) > 1 and sys.argv[1] == 'basic':
        # Esegui solo test base
        exit_code = pytest.main(['tests/test_basic.py', '-v'])
    else:
        # Esegui tutti i test
        exit_code = pytest.main(['tests/', '-v'])
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
''',

        "requirements-test.txt": '''# Dipendenze minime per iniziare i test
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-timeout>=2.1.0

# Mock per test senza dipendenze complete
pytest-mock>=3.10.0

# Database (se disponibile)
psycopg2-binary>=2.9.0

# GUI (opzionale per ora)
# PyQt5>=5.15.0
# pytest-qt>=4.2.0
'''
    }
    
    # Crea i file
    for filename, content in files_content.items():
        filepath = tests_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Creato: {filepath.relative_to(base_dir)}")
    
    # Crea anche pytest.ini nella root del progetto
    pytest_ini = base_dir / "pytest.ini"
    pytest_ini_content = '''[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
'''
    
    with open(pytest_ini, 'w', encoding='utf-8') as f:
        f.write(pytest_ini_content)
    print(f"✅ Creato: pytest.ini")
    
    print("\n✨ Struttura test creata con successo!")
    print("\n📋 Prossimi passi:")
    print("1. Installa pytest: pip install pytest pytest-mock")
    print("2. Esegui test base: python tests/run_tests.py basic")
    print("3. Esegui tutti i test: python tests/run_tests.py")
    
    return True

if __name__ == "__main__":
    success = create_test_structure()
    if success:
        print("\n🎉 Setup completato!")
    else:
        print("\n❌ Errore durante il setup")
        sys.exit(1)