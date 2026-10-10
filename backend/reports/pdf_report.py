import os
from datetime import datetime

def create_pdf_report(data: dict, output_path: str) -> str:
    """Generates a professional PDF report from structured analysis data."""
    title = data.get('title', 'AI Document Analysis Report')
    summary = data.get('document_summary') or data.get('background') or data.get('subject') or 'N/A'
    purpose = data.get('purpose', 'N/A')
    findings = data.get('key_findings') or data.get('findings') or []
    risks = data.get('risks') or data.get('problems') or []
    recommendations = data.get('recommendations') or []
    conclusion = data.get('conclusion', 'N/A')

    # Try ReportLab first
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=12
        )
        h2_style = ParagraphStyle(
            'H2Style',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2563EB'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = styles['Normal']

        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        story.append(Spacer(1, 10))

        if purpose and purpose != 'N/A':
            story.append(Paragraph("Purpose", h2_style))
            story.append(Paragraph(purpose, body_style))

        if summary and summary != 'N/A':
            story.append(Paragraph("Summary", h2_style))
            story.append(Paragraph(summary, body_style))

        if findings:
            story.append(Paragraph("Key Findings", h2_style))
            for f in findings:
                story.append(Paragraph(f"• {f}", body_style))

        if risks:
            story.append(Paragraph("Risks & Problems", h2_style))
            for r in risks:
                story.append(Paragraph(f"• {r}", body_style))

        if recommendations:
            story.append(Paragraph("Recommendations", h2_style))
            for r in recommendations:
                story.append(Paragraph(f"• {r}", body_style))

        if conclusion and conclusion != 'N/A':
            story.append(Paragraph("Conclusion", h2_style))
            story.append(Paragraph(conclusion, body_style))

        doc.build(story)
        return output_path
    except Exception as e:
        print(f"ReportLab PDF generation notice: {e}, attempting FPDF/text PDF fallback...")

    # Fallback: Simple FPDF or clean text-PDF formatting
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, title[:60], ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Summary", ln=True)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 8, str(summary))

        pdf.output(output_path)
        return output_path
    except Exception as e2:
        print(f"FPDF fallback failed: {e2}")

    # Plain text output if PDF libraries uninstalled
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"=== {title} ===\n\n")
        f.write(f"Purpose:\n{purpose}\n\nSummary:\n{summary}\n\n")
        f.write(f"Key Findings:\n" + "\n".join(f"- {item}" for item in findings) + "\n\n")
        f.write(f"Risks:\n" + "\n".join(f"- {item}" for item in risks) + "\n\n")
        f.write(f"Recommendations:\n" + "\n".join(f"- {item}" for item in recommendations) + "\n\n")

    return output_path
