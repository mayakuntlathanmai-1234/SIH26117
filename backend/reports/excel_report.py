from openpyxl import Workbook
import os

def create_excel_report(data: list, output_path: str) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Data Export"
    
    if not data or not isinstance(data, list) or len(data) == 0:
        ws.append(["No data available"])
        wb.save(output_path)
        return output_path
        
    # Extract headers from first dictionary
    headers = list(data[0].keys())
    ws.append(headers)
    
    # Append rows
    for item in data:
        row = [str(item.get(h, "")) for h in headers]
        ws.append(row)
        
    wb.save(output_path)
    return output_path
