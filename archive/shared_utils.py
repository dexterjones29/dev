"""
Shared Utilities Package
------------------------
A shared utility module containing common functions for BigQuery, SharePoint, Monday,com, email delivery, and monitoring. 
Used across Commercial Bank control automation pipeline operations.
"""
import datetime as dt
import io
import json
import msal
import numpy as np
import os
import pandas as pd
import re
import requests
import smtplib
import uuid

from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.primitives import serialization, hashes
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from google.cloud import bigquery, storage
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
from office365.runtime.auth.token_response import TokenResponse
from office365.runtime.auth.authentication_context import AuthenticationContext
from os.path import basename

# ====================================
# 1. ENVIRONMENT & PROXY CONFIGURATION
# ====================================

def load_secrets():
    """Load environment variables from .env file."""
    load_dotenv()

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

# ==================================
# 2. CLOUD STORAGE & SHAREPOINT AUTH
# ==================================

SHAREPOINT_DEPARTMENTS = {
    'CPC': {
        'site_name': 'CommercialCardProduct',
        'pfx_blob': 'Certificates/SPO-CommercialCardProduct-DataTransfer.pfx',
        'client_id_env': 'CLIENT_ID_CPC',
        'tenant_id_env': 'SP_TENANT_ID',
        'pfx_pass_env': 'PFX_PASSWORD_CPC'
    },
    'PPC': {
        'site_name': 'ECPAPrepaidProduct',
        'pfx_blob': 'Certificates/SPO-ECPAPrepaidProduct-DataTransfer.pfx',
        'client_id_env': 'CLIENT_ID_PPC',
        'tenant_id_env': 'SP_TENANT_ID',
        'pfx_pass_env': 'PFX_PASSWORD_PPC'
    },
    'NYS_COURIER': {
        'site_name': 'NYSCourier',
        'pfx_blob': 'Certificates/SPO-NYSCourier-DataTransfer.pfx',
        'client_id_env': 'CLIENT_ID_NYS_COURIER',
        'tenant_id_env': 'SP_TENANT_ID',
        'pfx_pass_env': 'PFX_PASSWORD_NYS_COURIER'        
    }
}

def download_pfx_from_gcs(bucket_name, blob_name):
    """Download PFX blob to /tmp and return local path."""
    local_path = os.path.join('/tmp', os.path.basename(blob_name))
    client = storage.Client()
    client.bucket(bucket_name).blob(blob_name).download_to_filename(local_path)
    return local_path

def get_sp_access_token_pfx(pfx_path, pfx_password, client_id, tenant_id):
    """Use PFX to acquire an app-only token for SharePoint."""
    with open(pfx_path, 'rb') as f:
        pfx_bytes = f.read()

    private_key, cert, _ = load_key_and_certificates(pfx_bytes, pfx_password.encode())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    thumbprint = cert.fingerprint(hashes.SHA1()).hex()
    authority = f'https://login.microsoftonline.com/{tenant_id}'

    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential={
            'private_key': private_key_pem.decode(),
            'thumbprint': thumbprint,
        },
    )

    token = app.acquire_token_for_client(scopes=['https://kbna.sharepoint.com/.default'])
    if 'access_token' not in token:
        raise Exception(f'Failed to acquire token: {token}')
    return token['access_token']

def get_sp_context_pfx(site_root, pfx_path, pfx_password, client_id, tenant_id):
    """Establish SharePoint ClientContext using PFX."""
    access_token = get_sp_access_token_pfx(pfx_path, pfx_password, client_id, tenant_id)
    ctx = ClientContext(site_root).with_access_token(lambda: TokenResponse(access_token, 'Bearer'))
    ctx.authentication_context._token_expires = dt.datetime.max.replace(tzinfo=dt.timezone.utc)
    return ctx

def get_sharepoint_context(department, bucket_name='commercial_payments_controls'):
    """Return authenticated SharePoint ClientContext for a configured department."""
    if department not in SHAREPOINT_DEPARTMENTS:
        valid_keys = list(SHAREPOINT_DEPARTMENTS.keys())
        raise ValueError(f"Unknown department key '{department}'. Valid options: {valid_keys}")
        
    config = SHAREPOINT_DEPARTMENTS[department]
    site_root = f"https://kbna.sharepoint.com/sites/{config['site_name']}"
    
    pfx_path = download_pfx_from_gcs(bucket_name, config['pfx_blob'])
    client_id = os.getenv(config['client_id_env'])
    tenant_id = os.getenv(config['tenant_id_env'])
    pfx_password = os.getenv(config['pfx_pass_env'])
    
    if not all([client_id, tenant_id, pfx_password]):
        missing = [k for k, v in {
            config['client_id_env']: client_id,
            config['tenant_id_env']: tenant_id,
            config['pfx_pass_env']: pfx_password
        }.items() if not v]
        raise EnvironmentError(f"Missing required environment variables in .env: {missing}")

    return get_sp_context_pfx(site_root, pfx_path, pfx_password, client_id, tenant_id)

# ========================================
# 3. THIRD-PARTY INTEGRATIONS (Monday.com)
# ========================================

def get_monday_headers():
    """Return standard Monday.com API headers using environment variable."""
    api_key = os.getenv('MONDAY_API_KEY')
    if not api_key:
        raise ValueError('MONDAY_API_KEY not found in environment.')
    return {'Authorization': api_key, 'API-Version': '2024-04'}

def create_monday_item(board_id, item_name, column_values):
    """Create an item on Monday.com with specific column values."""
    api_url = 'https://api.monday.com/v2'
    headers = get_monday_headers()
    json_values = json.dumps(column_values)
    query = f'mutation {{ create_item (board_id: {board_id}, item_name: "{item_name}", column_values: "{json_values}") {{ id }} }}'
    data = {'query': query}
    proxies = {'https': 'vzproxy.keybank.com'}
    response = requests.post(url=api_url, json=data, headers=headers, proxies=proxies)
    response.raise_for_status()
    return response.json()

def get_monday_column_map(board_id):
    """Return the Monday.com board Column ID to Title mapping."""
    api_url = 'https://api.monday.com/v2'
    headers = get_monday_headers()
    query = f'{{ boards (ids: {board_id}) {{ item_name {{ items {{ column_values {{ id title }} }} }} }} }}'
    data = {'query': query}
    proxies = {'https': 'vzproxy.keybank.com'}
    response = requests.post(url=api_url, json=data, headers=headers, proxies=proxies)
    response.raise_for_status()
    data = response.json()

    # Extract the map from the first item found
    try:
        items = data['data']['boards'][0]['items_page']['items']
        if not items:
            return 'No items found on board to map columns.'

        col_map = {
            col['column']['id']: col ['column']['title']
            for col in items[0]['column_values']
        }
        return col_map
    except (KeyError, IndexError):
        return 'Failed to parse board column data.'

# =================================
# 4. BIGQUERY & WAREHOUSE UTILITIES
# =================================

def get_bq_client(project_id='taw-entpayments-prod-2935'):
    """Load BigQuery client with standard credentials."""
    clear_proxy()

    if not os.getenv('K_SERVICE'):
        credential_path = '/home/jupyter/.config/gcloud/application_default_credentials.json'

        if os.path.exists(credential_path):
            os.environ.setdefault('GOOGLE_APPLICATION_CREDENTIALS', credential_path)

    return bigquery.Client(project=project_id)
def validate_table_freshness(table_list, date_column='SNAPSHOT_DT', custom_threshold=None):
    """Check multiple tables for data freshness. Returns a list of stale table IDs. Empty list means all tables are fresh. Default threshold is CURRENT_DATE -1 day."""
    client = get_bq_client()
    threshold = custom_threshold or 'DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)'

    sub_queries = []

    if isinstance(table_list, dict):
        table_items = table_list.items()
    else:
        table_items = [(table, date_column) for table in table_list]

    for table, dt_col in table_items:
        clean_table = table.replace(':', '.')
        sub_queries.append(
            f"""
            SELECT
              '{table}' as table_id
            , MAX({dt_col}) as max_dt
            FROM '{clean_table}'
            """
        )

    master_query = f"""
    WITH results AS (
        {' UNION ALL '.join(sub_queries)}
    )
    SELECT table_id, max_dt
    FROM results
    WHERE max_dt < ({threshold}) OR max_dt IS NULL
    """

    try:
        results = client.query(master_query).to_dataframe()
    except Exception:
        print(master_query)
        raise

    if results.empty:
        return []

    # Print diagnostic info
    print('STALE TABLES DETECTED:')
    for _, row in results.iterrows():
        print (f" - {row['table_id']} (Last updated: {row['max_dt']})")

    return results['table_id'].tolist()

def load_to_bigquery(df, table_id, write_disposition='WRITE_APPEND'):
    """Standardized BigQuery data loader from DataFrame."""
    client = get_bq_client()
    job_config = bigquery.LoadJobConfig()
    job_config.write_disposition = write_disposition
    job_config.ignore_unknown_values = True
    job = client.load_table_from_dataframe(df, table_id, location='US', job_config=job_config)
    return job.result()

# ==================================
# 5. DATA FORMATTING & NOTIFICATIONS
# ==================================

def format_worksheet(workbook, worksheet, df):
    """
    Applies preferred Excel workbook formatting using xlsxwriter.
    - Font: Aptos, Size: 11
    - Alignment: Centered (Horizontal & Vertical)
    - Headers: Bold, Gray background (#D9D9D9), Bordered
    - Column Widths: Auto-adjusted based on content
    - Freeze Panes: Top row frozen
    """
    header_format = workbook.add_format({
        'bold': True,
        'font_name': 'Aptos',
        'font_size': 11,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#D9D9D9',
        'border': 1
    })
    cell_format = workbook.add_format({
        'font_name': 'Aptos',
        'font_size': 11,
        'align': 'center',
        'valign': 'vcenter'
    })

    for col_num, col_name in enumerate(df.columns):
        # Rewrite header row with formatting
        worksheet.write(0, col_num, col_name, header_format)
        # Calculate max length for auto-width
        series = df[col_name].astype(str)
        max_len = max(series.map(len).max(), len(col_name)) + 3
        worksheet.set_column(col_num, col_num, max_len, cell_format)
    # Freeze header row
    worksheet.freeze_panes(1, 0)

def send_email(to_email, subject, body, from_email='ecp_prepaid_product@keybank.com', attachments=None):
    """Send email with optional attachments."""
    if isinstance(to_email, list):
        to_email_str = ';'.join(to_email)
    else:
        to_email_str = to_email
        to_email = [to_email]

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email_str
    msg.attach(MIMEText(body))

    if attachments:
        for f in attachments:
            with open(f, 'rb') as fil:
                part = MIMEApplication(fil.read(), Name=basename(f))
                part['Content-Disposition'] = f'attachment; filename="{basename(f)}"'
                msg.attach(part)

    smtp = smtplib.SMTP(host='smtpgw.keybank.com', port=25)
    smtp.sendmail(from_email, to_email, msg.as_string())
    smtp.quit()

def send_html_email(to_email, subject, html_body, from_email='ecp_prepaid_product@keybank.com', attachments=None):
    """Send an HTML-formatted email with optional attachments"""
    if isinstance(to_email, list):
        to_email_str = ';'.join(to_email)
    else:
        to_email_str = to_email
        to_email = [to_email]

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email_str
    msg.attach(MIMEText(html_body, 'html'))   

    if attachments:
        for f in attachments:
            with open(f, 'rb') as fil:
                part = MIMEApplication(fil.read(), Name=basename(f))
                part['Content-Disposition'] = f'attachment; filename="{basename(f)}"'
                msg.attach(part)

    smtp = smtplib.SMTP(host='smtpgw.keybank.com', port=25)
    smtp.sendmail(from_email, to_email, msg.as_string())
    smtp.quit()

def sas_round(x, base=0.01):
    """Matches SAS round(x, base) behavior (round half away from zero)."""
    if pd.isna(x):
        return x
    return np.sign(x) * np.floor(np.abs(x) / base + 0.5) * base

def log_execution(pipeline_name, cp_number, status, records_processed=0, error_msg=None, client=None):
    """Log pipeline execution metadata to the central commercial automation audit table."""
    if client is None:
        client = get_bq_client()

    log_table = 'taw-entpayments-prod-2935.AW_PPD.PIPELINE_EXECUTION_LOG'

    log_data = [{
        'RUN_TIME_ET': pd.Timestamp.now(tz='America/New York').strftime('%Y-%m-%d %H:%M:%S'),
        'UNIQUE_ID': str(uuid.uuid4()),
        'PIPELINE_NAME': pipeline_name,
        'CP_NUMBER': cp_number,
        'STATUS': status,
        'RECORDS_PROCESSED': records_processed,
        'ERROR_MESSAGE': str(error_msg) if error_msg else None
    }]

    df_log = pd.DataFrame(log_data)
    job = client.load_table_from_dataframe(df_log, log_table)
    job.result()

def send_teams_alert(pipeline_name, status, message, records_processed=0, execution_time_sec=0.0):
    """Sends an operational status card to a Microsoft Teams channel via Webhook."""
    webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
    if not webhook_url:
        print("Warning: TEAMS_WEBHOOK_URL not set. Skipping Teams notification.")
        return

    # Color coding: Green for success, Red for failure, Yellow for warnings/stale data
    theme_colors = {
        'SUCCESS': '28A745',
        'FAILED': 'DC3545',
        'HALTED_STALE_DATA': 'FFC107'
    }
    color = theme_colors.get(status.upper(), '0078D7')

    # Adaptive Card Payload
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": f"Pipeline Status: {pipeline_name}",
                            "weight": "Bolder",
                            "size": "Medium"
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Status:", "value": status},
                                {"title": "Records:", "value": str(records_processed)},
                                {"title": "Duration:", "value": f"{execution_time_sec:.2f}s"},
                                {"title": "Details:", "value": message}
                            ]
                        }
                    ]
                }
            }
        ]
    }

    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Teams alert: {e}")

def get_jaccard_similarity():
    """Return the SQL string for the Jaccard name similarity UDF."""
    return """
    CREATE TEMP FUNCTION name_similarity(a STRING, b STRING)
    RETURNS FLOAT64
    LANGUAGE js AS r\"\"\"
        if (!a || !b) return 0;
        a = a.toLowerCase().replace(/[^a-z0-9\\s]/g, '').trim();
        b = b.toLowerCase().replace(/[^a-z0-9\\s]/g, '').trim();
        if (a == b) return 1;

        let setA = new Set(a.split(/\\s+/));
        let setB = new Set(b.split(/\\s+/));
        let intersection = new Set([....setA].filter(x => setB.has(x)));
        let union = new Set([...setA, ...setB]);
        return intersection.size / union.size;
    \"\"\";
    """

