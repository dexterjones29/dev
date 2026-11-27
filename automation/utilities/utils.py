"""
Shared Utilities Package
------------------------
Authentication
- load_secrets()
- set_proxy()
- clear_proxy()

Helpers
- extract_pdf_text()
- format_worksheet()

Notifications
- send_email()
- send_styled_email()
- send_email_notifications()
"""
import html
import os
import pandas as pd
import pymupdf
import smtplib

from dotenv import load_dotenv
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename
from pathlib import Path

from . import bq
from .constants import EMAIL_SIGNATURE, BIGQUERY_CONSOLE, EXECUTION_LOG, FROM_EMAIL, MBU_NAMES

# --------------
# AUTHENTICATION
# --------------

def load_secrets():
    """Load local development environment variables when an automation .env file exists."""
    env_file = Path(__file__).resolve().parent.parent / '.env'

    if env_file.exists():
        load_dotenv(env_file)

def set_proxy():
    """Configure proxy in Jupyter. Skip proxy configuration in Cloud Run."""
    if os.getenv('K_SERVICE'):
        return

    proxy = 'http://vzproxy.keybank.com:80'

    for key in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'):
        os.environ[key] = proxy

def clear_proxy():
    """Remove proxy environment variables."""
    for variable in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY'):
        os.environ.pop(variable, None)

# -------
# HELPERS
# -------

def extract_pdf_text(pdf_source):
    """Extract text from a PDF."""
    if isinstance(pdf_source, (str, os.PathLike)):
        with pymupdf.open(pdf_source) as doc:
            return '\n'.join(page.get_text() for page in doc)

    if isinstance(pdf_source, bytes):
        with pymupdf.open(stream=pdf_source, filetype='pdf') as doc:
            return '\n'.join(page.get_text() for page in doc)

    if hasattr(pdf_source, 'seek'):
        pdf_source.seek(0)

    with pymupdf.open(stream=pdf_source.read(), filetype='pdf') as doc:
        return '\n'.join(page.get_text() for page in doc)

def format_worksheet(workbook, worksheet, df):
    """Format an Excel worksheet using preferred style."""
    header_format = workbook.add_format({'bold': True, 'font_name': 'Aptos', 'font_size': 11, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D9D9D9', 'border': 1})
    cell_format = workbook.add_format({'font_name': 'Aptos', 'font_size': 11, 'align': 'center', 'valign': 'vcenter'})
    worksheet.freeze_panes(1,0)

    for column_number, column_name in enumerate(df.columns):
        worksheet.write(0, column_number, column_name, header_format)
        series = df[column_name].astype('string').fillna('')
        max_length = max(int(series.str.len().max()), len(str(column_name))) + 3
        worksheet.set_column(column_number, column_number, max_length, cell_format)

# -------------
# NOTIFICATIONS
# -------------

def send_email(to_email, subject, body, from_email=FROM_EMAIL, attachments=None, inline_images=None, is_html=False):
    """Send a plain-text or HTML-formatted email with optional attachments and inline images."""
    if isinstance(to_email, (list, tuple)):
        to_email = list(to_email)
        to_email_string = ';'.join(to_email)
    else:
        to_email_string = to_email
        to_email = [to_email]

    message = MIMEMultipart('related')
    message['Subject'] = subject
    message['From'] = from_email
    message['To'] = to_email_string

    alternative = MIMEMultipart('alternative')
    alternative.attach(MIMEText(body, 'html' if is_html else 'plain'))
    message.attach(alternative)

    for attachment in attachments or []:
        with open(attachment, 'rb') as file:
            part = MIMEApplication(file.read(), Name=basename(attachment))
            part['Content-Disposition'] = f'attachment; filename="{basename(attachment)}"'
            message.attach(part)

    for content_id, image_path in (inline_images or {}).items():
        with open(image_path, 'rb') as file:
            part = MIMEImage(file.read())
            part.add_header('Content-ID', f'<{content_id}>')
            part.add_header('Content-Disposition', 'inline', filename=basename(image_path))
            message.attach(part)

    smtp = smtplib.SMTP(host='smtpgw.keybank.com', port=25)

    try:
        refused_recipients = smtp.sendmail(from_email, to_email, message.as_string())

        if refused_recipients:
            raise RuntimeError(f'SMTP rejected recipients: {refused_recipients}')
    finally:
        smtp.quit()

    return {
        'FROM_EMAIL': from_email,
        'RECIPIENTS': to_email,
        'SUBJECT': subject,
        'ATTACHMENT_COUNT': len(attachments or []),
        'INLINE_IMAGE_COUNT': len(inline_images or {})
    }

def send_styled_email(to_email, subject, body_text, table=None, from_email=FROM_EMAIL, signature=EMAIL_SIGNATURE, attachments=None, column_widths=None, result_query=None, links=None):
    """Send a standardized HTML email with optional text, table, links, result query, signature, and attachments."""
    body_html = html.escape(body_text).replace('\n', '<br>')
    column_widths = column_widths or {}
    links = links or {}

    if table is not None and not table.empty:
        column_layout = ''.join(f'<col style="width:{column_widths.get(column, "auto")};">' for column in table.columns)
        header_cells = ''.join(
            f'''
            <th style="
                width:{column_widths.get(column, 'auto')};
                padding:9px 10px;
                background:#F3F5F8;
                border:1px solid #D9E2F3;
                color:#17365D;
                font-size:14px;
                font-weight:bold;
                text-align:center;
            ">
                {html.escape(str(column))}
            </th>
            '''
            for column in table.columns
        )

        table_rows = []

        for _, row in table.iterrows():
            cells = []

            for column in table.columns:
                value = '' if pd.isna(row[column]) else str(row[column])

                if column in links and value:
                    cell_value = (
                        f'<a href="{html.escape(links[column], quote=True)}" '
                        'style="color:#0563C1;text-decoration:underline;font-size:14px;font-weight:bold;">'
                        f'{html.escape(value)}</a>'
                    )
                else:
                    cell_value = html.escape(value)

                cells.append(
                    f'''
                    <td style="
                        width:{column_widths.get(column, 'auto')};
                        padding:8px 10px;
                        border:1px solid #D9E2F3;
                        color:#222222;
                        font-size:12px;
                        text-align:center;
                    ">
                        {cell_value}
                    </td>
                    '''
                )

            table_rows.append(f'<tr>{"".join(cells)}</tr>')

        table_html = f'''
        <table
            role="presentation"
            width="100%"
            cellpadding="0"
            cellspacing="0"
            style="
                width:100%;
                border-collapse:collapse;
                table-layout:fixed;
            "
        >
            <colgroup>
                {column_layout}
            </colgroup>

            <thead>
                <tr>
                    {header_cells}
                </tr>
            </thead>

            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        '''

    else:
        table_html = ''

    query_html = f'''
    <tr>
        <td style="
            padding:12px 26px 5px 26px;
            border-top:1px solid #D9E2F3;
        ">
            <div style="
                color:#17365D;
                font-size:16px;
                font-weight:bold;   
            ">
                Detailed Result History Query
            </div>

            <div style="
                padding-top:4px;
                color:#5A6472;
                font-size:13px;
                line-height:18px;
            ">
                (copy the query below, paste it into the BigQuery Console above, then press 'Run')
            </div>
        </td>
    </tr>    
    
    <tr>
        <td style="padding:7px 26px 18px 26px;">
            <div style="
                padding:16px;
                background:#F7F9FC;
                border:1px solid #D9E2F3;
            ">
                <div style="
                    margin:0'
                    padding:0;
                    color:#172B4D;
                    font-family:Consolas,'Courier New',monospace;
                    font-size:12px;
                    line-height:20px;
                    white-space:pre;
                    overflow-x:auto;
                ">{html.escape(result_query)}</div>
    
    
    
    
    
    '''