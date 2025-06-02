* {
        font-family: Segoe UI, Arial, sans-serif; /* Font più moderno, fallback a sans-serif */
        font-size: 10pt;
        color: #333333; /* Testo scuro di default */
    }
    QMainWindow {
        background-color: #F4F4F4; /* Sfondo principale grigio molto chiaro */
    }
    QWidget {
        background-color: #F4F4F4;
    }
    QLabel {
        color: #202020;
        background-color: transparent;
        padding: 2px;
    }
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit, QComboBox {
        background-color: #FFFFFF;
        color: #333333;
        border: 1px solid #CCCCCC;
        border-radius: 4px;
        padding: 5px;
        selection-background-color: #0078D4; /* Blu per selezione testo */
        selection-color: white;
    }
    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, 
    QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QComboBox:focus {
        border: 1px solid #0078D4; /* Bordo blu quando in focus */
        /* box-shadow: 0 0 3px #0078D4; /* Leggera ombra esterna (potrebbe non funzionare su tutte le piattaforme Qt) */
    }
    QLineEdit[readOnly="true"], QTextEdit[readOnly="true"] {
        background-color: #E9E9E9;
        color: #505050;
    }
    QPushButton {
        background-color: #0078D4; /* Blu Microsoft come colore primario */
        color: white;
        border: none; /* No bordo per un look più flat */
        border-radius: 4px;
        padding: 8px 15px;
        font-weight: bold;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #005A9E; /* Blu più scuro per hover */
    }
    QPushButton:pressed {
        background-color: #004C8A; /* Ancora più scuro per pressed */
    }
    QPushButton:disabled {
        background-color: #BDBDBD;
        color: #757575;
    }
    QTabWidget::pane {
        border-top: 1px solid #D0D0D0;
        background-color: #FFFFFF; /* Sfondo bianco per il contenuto dei tab */
        padding: 5px;
    }
    QTabBar::tab {
        background: #E0E0E0;
        color: #424242;
        border: 1px solid #D0D0D0;
        border-bottom: none; /* Il bordo inferiore è gestito dal pane o dal tab selezionato */
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        padding: 7px 12px;
        margin-right: 2px;
    }
    QTabBar::tab:hover {
        background: #D0D0D0;
    }
    QTabBar::tab:selected {
        background: #FFFFFF; /* Stesso colore del pane */
        color: #0078D4;     /* Colore d'accento per il testo del tab selezionato */
        font-weight: bold;
        border-color: #D0D0D0;
        /* Rimuovi il bordo inferiore del tab selezionato per farlo fondere con il pane */
        border-bottom-color: #FFFFFF; 
    }
    QTableWidget {
        gridline-color: #E0E0E0;
        background-color: #FFFFFF;
        alternate-background-color: #F9F9F9;
        selection-background-color: #60AFFF; /* Blu più chiaro per selezione tabella */
        selection-color: #FFFFFF;
        border: 1px solid #D0D0D0;
    }
    QHeaderView::section {
        background-color: #F0F0F0;
        color: #333333;
        padding: 5px;
        border: 1px solid #D0D0D0;
        border-bottom-width: 1px; 
        font-weight: bold;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
        width: 20px;
    }
    QComboBox::down-arrow {
        image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-arrow-down-16.png); /* Freccia standard di Qt */
    }
    QComboBox QAbstractItemView { /* Lista a discesa */
        border: 1px solid #D0D0D0;
        selection-background-color: #0078D4;
        selection-color: white;
        background-color: white;
        padding: 2px;
    }
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #D0D0D0;
        border-radius: 4px;
        margin-top: 1.5ex; /* Spazio per il titolo */
        padding: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px 0 5px;
        left: 10px;
        color: #0078D4; /* Titolo del GroupBox con colore d'accento */
    }
    QCheckBox {
        spacing: 5px;
    }
    QCheckBox::indicator {
        width: 16px; height: 16px;
        border: 1px solid #B0B0B0; border-radius: 3px;
        background-color: white;
    }
    QCheckBox::indicator:checked {
        background-color: #0078D4; border-color: #005A9E;
        /* Per un checkmark SVG (richiede Qt 5.15+ o gestione via QIcon) */
        /* image: url(path/to/checkmark.svg) */
    }
    QStatusBar {
        background-color: #E0E0E0;
        color: #333333;
    }
    QMenuBar { background-color: #E0E0E0; color: #333333; }
    QMenuBar::item:selected { background: #C0C0C0; }
    QMenu { background-color: #FFFFFF; border: 1px solid #B0B0B0; color: #333333;}
    QMenu::item:selected { background-color: #0078D4; color: white; }