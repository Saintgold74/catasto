


        

class LoginDialog(QDialog):
    def __init__(self, db_manager: CatastoDBManager, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.db_manager = db_manager
        self.logged_in_user_id: Optional[int] = None
        self.logged_in_user_info: Optional[Dict] = None
        self.current_session_id: Optional[str] = None
        
        self.setWindowTitle("Login - Catasto Storico")
        self.setMinimumWidth(350)
        self.setModal(True)

        layout = QVBoxLayout(self)
        
        form_layout = QGridLayout()
        form_layout.addWidget(QLabel("Username:"), 0, 0)
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Inserisci username")
        form_layout.addWidget(self.username_edit, 0, 1)
        
        form_layout.addWidget(QLabel("Password:"), 1, 0)
        self.password_edit = QPasswordLineEdit()
        form_layout.addWidget(self.password_edit, 1, 1)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.setDefault(True)
        self.login_button.clicked.connect(self.handle_login)
        
        self.cancel_button = QPushButton("Esci")
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.username_edit.setFocus()

    def handle_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Login Fallito", "Username e password sono obbligatori.")
            return
        
        credentials = self.db_manager.get_user_credentials(username)
        login_success = False
        
        if credentials:
            user_id_local = credentials['id']
            stored_hash = credentials['password_hash']
            
            if _verify_password(stored_hash, password):
                login_success = True
                gui_logger.info(f"Login GUI OK per ID: {user_id_local}")
            else:
                QMessageBox.warning(self, "Login Fallito", "Password errata.")
                gui_logger.warning(f"Login GUI fallito (pwd errata) per ID: {user_id_local}")
                self.password_edit.selectAll()
                self.password_edit.setFocus()
                return
        else:
            QMessageBox.warning(self, "Login Fallito", "Utente non trovato o non attivo.")
            gui_logger.warning(f"Login GUI fallito (utente '{username}' non trovato/attivo).")
            self.username_edit.selectAll()
            self.username_edit.setFocus()
            return
        
        if login_success and user_id_local is not None:
            session_id_returned = self.db_manager.register_access(
                user_id_local, 'login', 
                indirizzo_ip=client_ip_address_gui,
                esito=True,
                application_name='CatastoAppGUI'
            )
            
            if session_id_returned:
                self.logged_in_user_id = user_id_local
                self.logged_in_user_info = credentials # Contiene l'ID dell'utente DB, non app_user_id!
                                                    # Assicurati che 'id' in credentials sia l'app_user_id
                self.current_session_id = session_id_returned

                # Imposta le variabili di sessione per l'audit
                # Assumendo che user_id_local sia l'app_user_id
                if not self.db_manager.set_audit_session_variables(self.logged_in_user_id, self.current_session_id): # <--- CHIAMATA
                    # Gestisci l'errore, forse il login non dovrebbe procedere
                    QMessageBox.critical(self, "Errore Audit", "Impossibile impostare le informazioni di sessione per l'audit.")
                    # Potresti decidere di non accettare il login qui

                # Commentato perché il metodo `set_session_app_user` sembra fare qualcosa di simile,
                # ma `set_audit_session_variables` è più specifico per i GUC.
                # if not self.db_manager.set_session_app_user(self.logged_in_user_id, client_ip_address_gui):
                #    gui_logger.error("Impossibile impostare contesto DB post-login!")

                QMessageBox.information(self, "Login Riuscito", 
                                        f"Benvenuto {self.logged_in_user_info.get('nome_completo', username)}!")
                self.accept()
            else:
                QMessageBox.critical(self, "Login Fallito", "Errore critico: Impossibile registrare la sessione di accesso.")
                gui_logger.error(f"Login GUI OK per ID {user_id_local} ma fallita reg. accesso.")














# --- Widget per Esportazioni ---

# --- Finestra di Creazione Utente ---
# --- Finestra principale ---


# --- Widget per riepilogo dati immobili ---

# --- Schede specifiche per Consultazione ---


# --- Dialogo Dettagli Partita ---







    




class RegistrazioneProprietaWidget(QWidget):
    partita_creata_per_operazioni_collegate = pyqtSignal(int, int)

    def __init__(self, db_manager: 'CatastoDBManager', parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.comune_id: Optional[int] = None
        self.comune_display_name: Optional[str] = None # Salva anche il nome per la UI
        self.possessori_data: List[Dict[str, Any]] = []
        self.immobili_data: List[Dict[str, Any]] = []

        self._initUI() # Ora questo chiamerà il metodo definito sotto

    def _initUI(self):
        # TUTTA LA LOGICA PER CREARE I WIDGET DI QUESTO TAB VA QUI:
        layout = QVBoxLayout(self) # Imposta il layout principale per questo widget

        # Esempio (basato sulla struttura precedente del suo widget):
        form_group = QGroupBox("Dati Nuova Proprietà")
        form_layout = QGridLayout() # O QFormLayout

        # Comune
        comune_label = QLabel("Comune (*):")
        self.comune_display = QLabel("Nessun comune selezionato.")
        self.comune_button = QPushButton("Seleziona Comune...")
        self.comune_button.clicked.connect(self.select_comune) # Assumendo che select_comune esista
        form_layout.addWidget(comune_label, 0, 0)
        form_layout.addWidget(self.comune_display, 0, 1)
        form_layout.addWidget(self.comune_button, 0, 2)

        # Numero partita
        num_partita_label = QLabel("Numero Partita (*):")
        self.num_partita_edit = QSpinBox()
        self.num_partita_edit.setMinimum(1); self.num_partita_edit.setMaximum(9999999)
        form_layout.addWidget(num_partita_label, 1, 0)
        form_layout.addWidget(self.num_partita_edit, 1, 1, 1, 2) # Span

        # Data impianto
        data_label = QLabel("Data Impianto (*):")
        self.data_edit = QDateEdit(calendarPopup=True)
        self.data_edit.setDate(QDate.currentDate())
        self.data_edit.setDisplayFormat("yyyy-MM-dd")
        form_layout.addWidget(data_label, 2, 0)
        form_layout.addWidget(self.data_edit, 2, 1, 1, 2) # Span

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Sezione Possessori
        possessori_group = QGroupBox("Possessori Associati")
        possessori_layout = QVBoxLayout(possessori_group)
        self.possessori_table = QTableWidget()
        # ... (configurazione possessori_table) ...
        self.possessori_table.setColumnCount(4) # Esempio: ID, Nome, Titolo, Quota
        self.possessori_table.setHorizontalHeaderLabels(["ID Poss.", "Nome Completo", "Titolo", "Quota"])
        possessori_layout.addWidget(self.possessori_table)
        btn_add_poss = QPushButton("Aggiungi Possessore"); btn_add_poss.clicked.connect(self.add_possessore)
        btn_rem_poss = QPushButton("Rimuovi Possessore"); btn_rem_poss.clicked.connect(self.remove_possessore)
        h_layout_poss = QHBoxLayout(); h_layout_poss.addWidget(btn_add_poss); h_layout_poss.addWidget(btn_rem_poss); h_layout_poss.addStretch()
        possessori_layout.addLayout(h_layout_poss)
        layout.addWidget(possessori_group)

        # Sezione Immobili
        immobili_group = QGroupBox("Immobili Associati")
        immobili_layout = QVBoxLayout(immobili_group)
        self.immobili_table = QTableWidget()
        # ... (configurazione immobili_table) ...
        self.immobili_table.setColumnCount(5) # Esempio
        self.immobili_table.setHorizontalHeaderLabels(["ID", "Natura", "Località", "Class.", "Consist."])
        immobili_layout.addWidget(self.immobili_table)
        btn_add_imm = QPushButton("Aggiungi Immobile"); btn_add_imm.clicked.connect(self.add_immobile)
        btn_rem_imm = QPushButton("Rimuovi Immobile"); btn_rem_imm.clicked.connect(self.remove_immobile)
        h_layout_imm = QHBoxLayout(); h_layout_imm.addWidget(btn_add_imm); h_layout_imm.addWidget(btn_rem_imm); h_layout_imm.addStretch()
        immobili_layout.addLayout(h_layout_imm)
        layout.addWidget(immobili_group)

        # Pulsante Registra Proprietà
        self.btn_registra_proprieta = QPushButton(QApplication.style().standardIcon(QStyle.SP_DialogSaveButton), " Registra Nuova Proprietà")
        self.btn_registra_proprieta.clicked.connect(self._salva_proprieta) # Collegato al metodo corretto
        layout.addWidget(self.btn_registra_proprieta)

        layout.addStretch(1)
        # Non serve self.setLayout(layout) qui se il layout è già stato passato a QWidget nel costruttore del layout
    
    def select_comune(self):
        """Apre il selettore di comuni."""
        dialog = ComuneSelectionDialog(self.db_manager, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_comune_id:
            self.comune_id = dialog.selected_comune_id
            self.comune_display.setText(dialog.selected_comune_name)
    
    def add_possessore(self):
        """Aggiunge un possessore alla lista."""
        dialog = PossessoreSelectionDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.selected_possessore:
            self.possessori_data.append(dialog.selected_possessore)
            self.update_possessori_table()
    
    def remove_possessore(self):
        """Rimuove il possessore selezionato dalla lista."""
        selected_rows = self.possessori_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un possessore da rimuovere.")
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self.possessori_data):
            del self.possessori_data[row]
            self.update_possessori_table()
    
    def update_possessori_table(self):
        """Aggiorna la tabella dei possessori."""
        if not hasattr(self, 'possessori_data') or self.possessori_data is None:
            self.possessori_data = [] # Assicura che sia una lista se non definito

        self.possessori_table.setRowCount(len(self.possessori_data))
        
        # Assicurati che NUOVE_ETICHETTE_POSSESSORI sia definito globalmente,
        # come attributo di classe/istanza, o passato al metodo se necessario.
        # Esempio: NUOVE_ETICHETTE_POSSESSORI = ["cognome_nome", "paternita_dettaglio", ...]
        # Se non è definito, il controllo 'in NUOVE_ETICHETTE_POSSESSORI' causerà un NameError.
        # Per ora, assumiamo che sia definito da qualche parte accessibile.
        # Se non lo è, dovrà definirlo o rimuovere il blocco condizionale se le colonne sono fisse.

        for i, dati_possessore in enumerate(self.possessori_data): # Usa 'i' e 'dati_possessore'
            current_col = 0 # Inizializza l'indice di colonna per ogni riga

            # Colonna 0: Nome Completo (come da sua logica originale)
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('nome_completo', ''))))
            current_col += 1

            # Colonna 1: Cognome e Nome (come da sua logica originale)
            # Questa potrebbe essere la stessa del blocco "NUOVE COLONNE" o una versione diversa.
            # Se 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI è per una visualizzazione speciale, gestiscila qui.
            if 'cognome_nome' in NUOVE_ETICHETTE_POSSESSORI: # Assumendo NUOVE_ETICHETTE_POSSESSORI sia definito
                # Usa il valore da dati_possessore.get('cognome_nome', 'N/D')
                # Questa era la colonna che causava l'errore usando 'row_idx' e 'col' non definite.
                self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('cognome_nome', 'N/D'))))
            else:
                # Fallback o gestione se 'cognome_nome' non è in NUOVE_ETICHETTE_POSSESSORI ma è una colonna fissa
                self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('cognome_nome', ''))))
            current_col += 1

            # Colonna 2: Paternità
            # Il blocco "NUOVE COLONNE" aveva anche una 'paternita'. Chiarire quale usare.
            # Se il blocco if precedente gestiva una 'paternita' condizionale:
            # if 'paternita_speciale' in NUOVE_ETICHETTE_POSSESSORI:
            #     self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita_speciale', 'N/D'))))
            # else:
            #     self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita', ''))))
            # current_col += 1
            # Oppure, se è sempre la stessa 'paternita':
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('paternita', ''))))
            current_col += 1
            
            # Colonna 3: Quota
            self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('quota', ''))))
            current_col += 1
            
            # Aggiungere altre colonne se necessario, seguendo il pattern:
            # self.possessori_table.setItem(i, current_col, QTableWidgetItem(str(dati_possessore.get('nome_campo', ''))))
            # current_col += 1

        self.possessori_table.resizeColumnsToContents()
    
    def add_immobile(self):
        """Aggiunge un immobile alla lista."""
        dialog = ImmobileDialog(self.db_manager, self.comune_id, self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted and dialog.immobile_data:
            self.immobili_data.append(dialog.immobile_data)
            self.update_immobili_table()
    
    def remove_immobile(self):
        """Rimuove l'immobile selezionato dalla lista."""
        selected_rows = self.immobili_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Attenzione", "Seleziona un immobile da rimuovere.")
            return
        
        row = selected_rows[0].row()
        if 0 <= row < len(self.immobili_data):
            del self.immobili_data[row]
            self.update_immobili_table()
    
    def update_immobili_table(self):
        """Aggiorna la tabella degli immobili."""
        self.immobili_table.setRowCount(len(self.immobili_data))
        
        for i, immobile in enumerate(self.immobili_data):
            self.immobili_table.setItem(i, 0, QTableWidgetItem(immobile.get('natura', '')))
            self.immobili_table.setItem(i, 1, QTableWidgetItem(immobile.get('localita_nome', '')))
            self.immobili_table.setItem(i, 2, QTableWidgetItem(immobile.get('classificazione', '')))
            self.immobili_table.setItem(i, 3, QTableWidgetItem(immobile.get('consistenza', '')))
            
            piani_vani = ""
            if 'numero_piani' in immobile and immobile['numero_piani']:
                piani_vani += f"Piani: {immobile['numero_piani']}"
            if 'numero_vani' in immobile and immobile['numero_vani']:
                if piani_vani:
                    piani_vani += ", "
                piani_vani += f"Vani: {immobile['numero_vani']}"
            
            self.immobili_table.setItem(i, 4, QTableWidgetItem(piani_vani))
    
    # All'interno della classe RegistrazioneProprietaWidget in prova.py

    def _salva_proprieta(self):
        gui_logger.info("Avvio registrazione nuova proprietà...")
        if not self.comune_id:
            QMessageBox.warning(self, "Dati Mancanti", "Selezionare un comune."); return
        if not self.possessori_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un possessore."); return
        if not self.immobili_data:
            QMessageBox.warning(self, "Dati Mancanti", "Aggiungere almeno un immobile."); return
        
        numero_partita = self.num_partita_edit.value()
        data_impianto_dt = self.data_edit.date().toPyDate() # Converte QDate in datetime.date
        
        # Prepara i dati JSON per possessori e immobili
        # La procedura SQL si aspetta JSONB, quindi serializziamo qui.
        # Assicurati che json_serial gestisca le date se presenti nei dati
        def json_serial(obj):
            if isinstance(obj, (datetime, date)): return obj.isoformat()
            raise TypeError(f"Tipo {type(obj)} non serializzabile JSON")

        try:
            possessori_json_str = json.dumps(self.possessori_data, default=json_serial)
            immobili_json_str = json.dumps(self.immobili_data, default=json_serial)
        except TypeError as te:
            gui_logger.error(f"Errore serializzazione JSON per nuova proprietà: {te}")
            QMessageBox.critical(self, "Errore Dati", f"Errore nella preparazione dei dati per il database: {te}")
            return

        # Assumendo che il suo metodo in DBManager sia stato aggiornato e si chiami,
        # ad esempio, registra_nuova_proprieta_completa e accetti JSON.
        # E che restituisca l'ID della nuova partita o sollevi eccezione.
        try:
            # Chiamata aggiornata con i 5 argomenti che la procedura SQL catasto.registra_nuova_proprieta si aspetta
            nuova_partita_id = self.db_manager.registra_nuova_proprieta(
                comune_id=self.comune_id,
                numero_partita=numero_partita,
                data_impianto=data_impianto_dt,
                possessori_json_str=possessori_json_str,
                immobili_json_str=immobili_json_str
            )

            if nuova_partita_id is not None and self.comune_id is not None: # Controlla anche comune_id
                msg_success = f"Nuova proprietà (Partita N.{numero_partita}, ID: {nuova_partita_id}) registrata con successo per il comune ID {self.comune_id}."
                gui_logger.info(msg_success)
                
                reply = QMessageBox.question(self, "Registrazione Completata", 
                                             f"{msg_success}\n\nVuoi procedere con operazioni collegate (es. Duplicazione, Trasferimento Immobili) su questa o un'altra partita?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    # Emetti il segnale con l'ID della nuova partita e il suo comune_id
                    self.partita_creata_per_operazioni_collegate.emit(nuova_partita_id, self.comune_id) # Assicurati che self.comune_id sia corretto
                
                self._pulisci_form_registrazione()
            # else: Se nuova_partita_id è None, il DBManager dovrebbe aver sollevato un'eccezione
            # che viene catturata sotto.

        except (DBUniqueConstraintError, DBDataError, DBMError) as e_db:
            gui_logger.error(f"Errore DB registrazione proprietà: {e_db}")
            QMessageBox.critical(self, "Errore Database", str(e_db))
        except Exception as e_gen:
            gui_logger.critical(f"Errore imprevisto registrazione proprietà: {e_gen}", exc_info=True)
            QMessageBox.critical(self, "Errore Imprevisto", f"Errore: {type(e_gen).__name__}: {e_gen}")
    def _pulisci_form_registrazione(self):
        """Pulisce tutti i campi del form di registrazione proprietà."""
        gui_logger.info("Pulizia campi del form Registrazione Proprietà.")
        
        # Reset Comune selezionato
        self.comune_id = None
        self.comune_display_name = None # Se usa una variabile per il nome del comune
        if hasattr(self, 'comune_display') and isinstance(self.comune_display, QLabel):
            self.comune_display.setText("Nessun comune selezionato")
        
        # Reset Numero Partita
        if hasattr(self, 'num_partita_edit') and isinstance(self.num_partita_edit, QSpinBox):
            self.num_partita_edit.setValue(self.num_partita_edit.minimum()) # O un valore di default sensato come 1

        # Reset Data Impianto
        if hasattr(self, 'data_edit') and isinstance(self.data_edit, QDateEdit):
            self.data_edit.setDate(QDate.currentDate())

        # Reset liste dati interni
        self.possessori_data = []
        self.immobili_data = []

        # Aggiorna/Pulisci le tabelle UI dei possessori e immobili (se le ha)
        if hasattr(self, 'update_possessori_table'): # Metodo che popola/pulisce la QTableWidget dei possessori
            self.update_possessori_table() 
        elif hasattr(self, 'possessori_table') and isinstance(self.possessori_table, QTableWidget): # Alternativa se non c'è update_xxx
            self.possessori_table.setRowCount(0)

        if hasattr(self, 'update_immobili_table'): # Metodo che popola/pulisce la QTableWidget degli immobili
            self.update_immobili_table()
        elif hasattr(self, 'immobili_table') and isinstance(self.immobili_table, QTableWidget):
            self.immobili_table.setRowCount(0)
            
        # Imposta il focus su un campo iniziale, ad esempio il pulsante per selezionare il comune
        if hasattr(self, 'comune_button') and isinstance(self.comune_button, QPushButton):
            self.comune_button.setFocus()
        elif hasattr(self, 'num_partita_edit'): # O il campo numero partita
            self.num_partita_edit.setFocus()
        
        gui_logger.info("Campi form Registrazione Proprietà puliti.")
