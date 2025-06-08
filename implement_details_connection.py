#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMPLEMENTAZIONE COLLEGAMENTI AI DETTAGLI
File: implement_details_connection.py
"""

import os
import shutil
from datetime import datetime

def backup_current_files():
    """Crea backup dei file attuali"""
    files_to_backup = [
        "fuzzy_search_widget.py",
        "gui_main.py"
    ]
    
    backups_created = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for file in files_to_backup:
        if os.path.exists(file):
            backup_name = f"{file}_backup_details_{timestamp}"
            shutil.copy2(file, backup_name)
            backups_created.append(backup_name)
            print(f"✅ Backup: {file} → {backup_name}")
    
    return backups_created

def update_gui_main_for_enhanced_widget():
    """Aggiorna gui_main.py per usare il widget potenziato"""
    try:
        with open("gui_main.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Sostituisce l'import
        old_import_patterns = [
            "from fuzzy_search_widget import add_optimized_fuzzy_search_tab_to_main_window as add_fuzzy_search_tab_to_main_window",
            "from fuzzy_search_widget import add_fuzzy_search_tab_to_main_window"
        ]
        
        new_import = "from fuzzy_search_widget import add_enhanced_fuzzy_search_tab_to_main_window as add_fuzzy_search_tab_to_main_window"
        
        content_modified = False
        for old_pattern in old_import_patterns:
            if old_pattern in content:
                content = content.replace(old_pattern, new_import)
                content_modified = True
                break
        
        if content_modified:
            with open("gui_main.py", "w", encoding="utf-8") as f:
                f.write(content)
            print("✅ gui_main.py aggiornato per widget potenziato")
            return True
        else:
            print("⚠️ Pattern import non trovato in gui_main.py")
            return False
            
    except Exception as e:
        print(f"❌ Errore aggiornamento gui_main.py: {e}")
        return False

def create_enhanced_widget_file():
    """Crea istruzioni per il file widget potenziato"""
    print("\n📝 ISTRUZIONI PER CREARE IL WIDGET POTENZIATO:")
    print("1. Crea un nuovo file 'enhanced_fuzzy_widget_with_details.py'")
    print("2. Copia il codice del widget potenziato")
    print("3. Aggiungi queste modifiche al tuo 'fuzzy_search_widget.py':")
    print("")
    
    modifications = """
# === MODIFICHE DA AGGIUNGERE A fuzzy_search_widget.py ===

# 1. Aggiungi questi import in cima al file:
import psycopg2.extras

# 2. Sostituisci il metodo _on_possessore_double_click con:
def _on_possessore_double_click(self, index):
    '''Gestisce doppio click su possessore con dettagli completi.'''
    item = self.possessori_table.item(index.row(), 0)
    if item:
        possessore_data = item.data(Qt.UserRole)
        possessore_id = possessore_data.get('id')
        
        try:
            # Recupera le partite collegate
            QApplication.setOverrideCursor(Qt.WaitCursor)
            partite = self._get_partite_per_possessore(possessore_id)
            QApplication.restoreOverrideCursor()
            
            # Mostra dialog con dettagli
            self._mostra_dettagli_possessore(possessore_data, partite)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore dettagli possessore: {e}")

# 3. Aggiungi questi metodi helper:
def _get_partite_per_possessore(self, possessore_id):
    '''Recupera partite per possessore.'''
    try:
        return self.db_manager.get_partite_per_possessore(possessore_id)
    except Exception as e:
        self.logger.error(f"Errore recupero partite per possessore {possessore_id}: {e}")
        return []

def _mostra_dettagli_possessore(self, possessore_data, partite):
    '''Mostra dialog dettagli possessore.'''
    # Per ora un dialog semplificato
    nome = possessore_data.get('nome_completo', 'N/A')
    comune = possessore_data.get('comune_nome', 'N/A')
    num_partite = len(partite)
    
    dettagli = f"👤 {nome}\\n🏛️ {comune}\\n📋 {num_partite} partite collegate\\n\\n"
    
    if partite:
        dettagli += "Partite:\\n"
        for p in partite[:5]:  # Prime 5 partite
            dettagli += f"• N.{p.get('numero_partita', '?')} - {p.get('tipo_partita', 'N/A')}\\n"
        if len(partite) > 5:
            dettagli += f"... e altre {len(partite) - 5} partite"
    
    QMessageBox.information(self, f"Dettagli Possessore", dettagli)

# 4. Per località, sostituisci _on_localita_double_click con:
def _on_localita_double_click(self, index):
    '''Gestisce doppio click su località.'''
    item = self.localita_table.item(index.row(), 0)
    if item:
        localita_data = item.data(Qt.UserRole)
        localita_id = localita_data.get('id')
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            immobili = self._get_immobili_per_localita(localita_id)
            QApplication.restoreOverrideCursor()
            
            self._mostra_dettagli_localita(localita_data, immobili)
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Errore", f"Errore dettagli località: {e}")

def _get_immobili_per_localita(self, localita_id):
    '''Recupera immobili per località.'''
    try:
        conn = self.db_manager._get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                query = '''
                SELECT i.id as immobile_id, i.natura, i.numero_piani, i.numero_vani,
                       p.id as partita_id, p.numero_partita, c.nome as comune_nome
                FROM immobile i
                JOIN partita p ON i.partita_id = p.id
                JOIN comune c ON p.comune_id = c.id
                WHERE i.localita_id = %s
                ORDER BY p.numero_partita
                '''
                cur.execute(query, (localita_id,))
                results = cur.fetchall()
                return [dict(row) for row in results] if results else []
        finally:
            self.db_manager._release_connection(conn)
    except Exception as e:
        self.logger.error(f"Errore recupero immobili per località {localita_id}: {e}")
        return []

def _mostra_dettagli_localita(self, localita_data, immobili):
    '''Mostra dialog dettagli località.'''
    nome = localita_data.get('nome', 'N/A')
    tipo = localita_data.get('tipo', 'N/A')
    civico = localita_data.get('civico', '')
    comune = localita_data.get('comune_nome', 'N/A')
    
    nome_completo = f"{nome} {civico}" if civico else nome
    
    dettagli = f"🏠 {nome_completo}\\n📍 {tipo}\\n🏛️ {comune}\\n"
    dettagli += f"🏢 {len(immobili)} immobili\\n\\n"
    
    if immobili:
        dettagli += "Immobili:\\n"
        for imm in immobili[:5]:  # Primi 5 immobili
            partita = imm.get('numero_partita', '?')
            natura = imm.get('natura', 'N/A')
            dettagli += f"• Partita N.{partita}: {natura}\\n"
        if len(immobili) > 5:
            dettagli += f"... e altri {len(immobili) - 5} immobili"
    
    QMessageBox.information(self, f"Dettagli Località", dettagli)

# === FINE MODIFICHE ===
"""
    
    print(modifications)

def main():
    """Implementa i collegamenti ai dettagli"""
    print("=" * 60)
    print("IMPLEMENTAZIONE COLLEGAMENTI AI DETTAGLI")
    print("=" * 60)
    
    print("\n1. Creazione backup...")
    backups = backup_current_files()
    
    print(f"\n2. Aggiornamento gui_main.py...")
    gui_updated = update_gui_main_for_enhanced_widget()
    
    print(f"\n3. Istruzioni per modifiche...")
    create_enhanced_widget_file()
    
    print("\n" + "=" * 60)
    print("📋 RIEPILOGO IMPLEMENTAZIONE")
    print("=" * 60)
    
    if backups and gui_updated:
        print("✅ PREPARAZIONE COMPLETATA!")
        print("\n🔧 PASSI FINALI:")
        print("1. Applica le modifiche mostrate sopra al file fuzzy_search_widget.py")
        print("2. Riavvia l'applicazione: python gui_main.py")
        print("3. Testa il doppio click su possessori e località")
        
        print("\n🎯 COSA OTTERRAI:")
        print("• Doppio click su possessore → Mostra tutte le sue partite")
        print("• Doppio click su località → Mostra tutti gli immobili")
        print("• Dialog informativi con dettagli completi")
        print("• Collegamenti pronti per espansione futura")
        
        print(f"\n💾 Backup creati: {len(backups)} file")
        for backup in backups:
            print(f"   - {backup}")
            
    else:
        print("❌ PROBLEMI DURANTE LA PREPARAZIONE")
        print("Controlla i messaggi di errore sopra")

if __name__ == "__main__":
    main()
