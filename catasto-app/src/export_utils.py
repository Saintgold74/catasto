def export_to_json(data, filename):
    import json
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)

def export_to_csv(data, filename):
    import csv
    with open(filename, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(data[0].keys())  # Write header
        for row in data:
            writer.writerow(row.values())

def export_to_pdf(data, filename):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Exported Data', 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font('Arial', '', 12)
    for key, value in data.items():
        pdf.cell(0, 10, f"{key}: {value}", 0, 1)
    
    pdf.output(filename)