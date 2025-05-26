import json
import pandas as pd

def export_log_to_excel(log_path, excel_path):
    with open(log_path) as f:
        rows = [json.loads(line.split(" | ", 1)[1]) for line in f if "{" in line]
    df = pd.DataFrame(rows)
    df.to_excel(excel_path, index=False)

def export_log_to_html(log_path, html_path):
    with open(log_path) as f:
        rows = [json.loads(line.split(" | ", 1)[1]) for line in f if "{" in line]
    df = pd.DataFrame(rows)
    # Dale formato con Styler
    styled = df.style.set_table_styles([
        {'selector': 'th', 'props': [('background-color', '#101d86'), ('color', 'white'), ('font-weight', 'bold')]},
        {'selector': 'td', 'props': [('padding', '5px')]},
        {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f2f2f2')]}
    ]).set_caption("PyFuzzyFlow Test Report")
    styled.to_html(html_path)
