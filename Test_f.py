# Test_fpdf.py
try:
    from fpdf import FPDF
    print("FPDF è installato e importabile correttamente.")
except ImportError:
    print("ERRORE: FPDF NON è installato o non è importabile.")