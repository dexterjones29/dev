"""
SharePoint Utilities Package
----------------------------
- get_context()
- download_files()
- upload_files()
- walk_folder()
- get_month_folders()
- get_files()
- get_date_from_path()
- filter_new_files()
- execute_with_retry()
- ensure_folder()
- get_page_url()
- create_review_list()
- get_review_list_map()
- ensure_review_list()
- create_review_list_item()
"""

import datetime as dt
import os

import msal
import pandas as pd
import tempfile
import time

from . import bq
from .constants import SHAREPOINT_ROOT, AUTOMATION_SITE, SHAREPOINT_DEPARTMENTS

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from google.cloud import storage
from office365.runtime.auth.token_response import TokenResponse
from office365.runtime.client_request_exception import ClientRequestException
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.fields.url_value import FieldUrlValue
from office365.sharepoint.files.file import File
from office365.sharepoint.lists.creation_information import ListCreationInformation
from office365.sharepoint.lists.templates.type import ListTemplateType
from urllib.parse import quote

def get_context(department, bucket_name='commercial_payments_controls'):
    """Return an authenticated SharePoint context."""
    if department not in SHAREPOINT_DEPARTMENTS:
        raise ValueError(f"Unknown department key '{department}'. Valid options: {list(SHAREPOINT_DEPARTMENTS)}")

    config = SHAREPOINT_DEPARTMENTS[department]
    site_root = f'https://kbna.sharepoint.com/sites/{config['site_name']}'
    client_id = os.getenv(config['client_id_env'])
    tenant_id = os.getenv('SP_TENANT_ID')
    pfx_password = os.getenv(config['pfx_pass_env'])
    missing = [key for key, value in {config['client_id_env']: client_id, 'SP_TENANT_ID': tenant_id, config['pfx_pass_env']: pfx_password}.items() if not value]

    if missing:
        raise EnvironmentError(f'Missing rquired environment variables in .env: {missing}')

    pfx_path = os.path.join(tempfile.gettempdir(), os.path.basename(config['pfx_blob']))
    storage.Client().bucket(bucket_name).blob(config['pfx_blob']).download_to_filename(pfx_path)

    with open(pfx_path, 'rb') as file:
        pfx_bytes = file.read()

    private_key, certificate, _ = load_key_and_certificates(pfx_bytes, pfx_password.encode())
    private_key_pem = private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())
    thumbprint = certificate.fingerprint(hashes.SHA1()).hex()
    authority = f'https://login.microsoftonline.com/{tenant_id}'
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential={'private_key': private_key_pem.decode(), 'thumbprint': thumbprint})
    token = app.acquire_token_for_client(scopes=['https://kbna.sharepoint.com/.default'])

    if 'access_token' not in token:
        raise Exception(f'Failed to acquire SharePoint token: {token}')

    ctx = ClientContext(site_root).with_access_token(lambda: TokenResponse(token['access_token'], 'Bearer'))
    ctx.authentication_context._token_expires = dt.datetime.max.replace(tzinfo=dt.timezone.utc)

    return ctx

def download_files(ctx, server_relative_url: str) -> bytes:
    """Download a SharePoint file into memory."""
    return File.open_binary(ctx, server_relative_url).content

def upload_files(ctx, folder_path: str, filename: str, content: bytes) -> str:
    """Upload an in-memory file to a SharePoint folder."""
    folder = ctx.web.get_folder_by_server_relative_url(folder_path)
    uploaded_file = folder.upload_file(filename, content).execute_query()
    server_relative_url = getattr(uploaded_file, 'server_relative_url', uploaded_file.properties.get('ServerRelativeUrl', ''))

    if not server_relative_url:
        raise AttributeError(f'SharePoint upload succeeded, but the uploaded file URL was not returned for {filename}.')

    return server_relative_url

def walk_folder(ctx, folder):
    """Recursively yield all files in a SharePoint folder."""
    ctx.load(folder, ['Files', 'Folders'])
    ctx.execute_query()

    for file_object in folder.files:
        yield file_object

    for subfolder in folder.folders:
        yield from walk_folder(ctx, subfolder)

def get_month_folders(base_folder, start_date, lookback_months=1):
    """Generate SharePoint month folders using the M-YYYY convention."""
    today = dt.date.today()
    current_month = start_date.month - lookback_months
    current_year = start_date.year

    while current_month <= 0:
        current_month += 12
        current_year -= 1

    current = dt.date(current_year, current_month, 1)
    end_month = dt.date(today.year, today.month, 1)
    folders = []

    while current <= end_month:
        folders.append(f'{base_folder}/{current_month}-{current_year}')
        current = dt.date(current.year + 1, 1, 1) if current_month == 12 else dt.date(current_year, current.month + 1, 1)

    return folders

def get_files(ctx, folder_paths):
    """Collect files recursively from a list of SharePoint folders."""
    all_files = []

    for path in folder_paths:
        try:
            folder = ctx.web.get_folder_by_server_relative_url(path)
            all_files.extend(list(walk_folder(ctx, folder)))
        except Exception as error:
            print(f'Unable to access folder {path}: {error}')

    return all_files

def get_date_from_path(path, folder_pattern, file_pattern):
    """Extract a date from a path using folder and filename patterns."""
    folder_match = folder_pattern.search(path)
    file_match = file_pattern.search(path)

    if not folder_match or not file_match:
        return None

    try:
        return dt.date(int(folder_match.group(2)), int(file_match.group(1)), int(file_match.group(2)))
    except ValueError:
        return None

def filter_new_files(files, max_date, date_extractor, file_prefix=None, date_offset_days=0):
    """Return SharePoint files whose effective dates exceed max_date."""
    new_files = []

    for file_object in files:
        name = file_object.properties['Name']

        if file_prefix and not name.startswith(file_prefix):
            continue

        url = file_object.properties['ServerRelativeUrl']
        file_date = date_extractor(name)

        if file_date is None:
            continue

        report_date = file_date + dt.timedelta(days=date_offset_days)

        if report_date > max_date:
            new_files.append({'server_relative_url': url, 'file_name':name, 'file_date': file_date})

    return new_files

def execute_with_retry(operation, description, max_attempts=5):
    """Execute one SharePoint operation with retry for transient failures."""
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()

        except ClientRequestException as error:
            status_code = getattr(error.response, 'status_code', None)

            if status_code not in {429, 500, 502, 503, 504} or attempt == max_attempts:
                raise

            retry_after = error.response.headers.get('Retry-After')
            wait_seconds = int(retry_after) if retry_after else min(2 ** attempt, 30)

            print(f'SharePoint returned {status_code} whilel {description}. Retrying in {wait_seconds} seconds ({attempt}/{max_attempts})...')
            time.sleep(wait_seconds)

def ensure_folder(ctx, library_path, folder_name):
    """Return an existing SharePoint folder or create it when missing."""
    library_path = library_path.rstrip('/')
    folder_path = f'{library_path}/{folder_name}'
    folder = ctx.web.get_folder_by_server_relative_url(folder_path)

    try:
        execute_with_retry(lambda: ctx.load(folder).execute_query(), f'checking folder {folder_path}')
        created = False

    except ClientRequestException as error:
        if getattr(error.response, 'status_code', None) != 404:
            raise

        library = ctx.web.get_folder_by_server_relative_url(library_path)
        folder = execute_with_retry(lambda: library.folders.add(folder_name).execute_query(), f'creating folder {folder_path}')
        created = True
        print(f'Created SharePoint folder: {folder_path}')

    server_relative_url = folder.properties.get('ServerRelativeUrl', folder_path)
    folder_url = SHAREPOINT_ROOT + quote(server_relative_url, safe='/')

    return {
        'FOLDER': folder,
        'URL': folder_url,
        'CREATED': created
    }

def get_page_url(procedure_id):
    """Return the standardized Control Procedure page URL."""
    procedure_id = str(procedure_id).strip()

    if not procedure_id:
        raise ValueError('Procedure ID cannot be empty.')

    return f'{SHAREPOINT_ROOT}{AUTOMATION_SITE}/SitePages/{procedure_id}.aspx'

def create_review_list(ctx, list_title):
    """Create and configure one standardized control review List."""
    create_info = ListCreationInformation(list_title, 'Control automation execution review and evidence.', ListTemplateType.GenericList)
    results_list = ctx.web.lists.add(create_info).execute_query()
    results_list.fields.add_choice_field('Status', ['New', 'Complete']).execute_query()
    results_list.fields.add_url_field('View Detailed Results').execute_query()
    results_list.fields.add_datetime('Run Time').execute_query()
    run_id_field = results_list.fields.add_text_field('Run ID').execute_query()
    run_id_field.set_property('Indexed', True)
    run_id_field.update().execute_query()
    run_id_field.set_property('EnforceUniqueValues', True)
    run_id_field.update().execute_query()
    print(f'Created SharePoint Review List: {list_title}')

    return results_list

def get_review_list_map(results_list):
    """Return SharePoint list display-name to internal-name mapping."""
    fields = results_list.fields.get().execute_query()
    return {field.properties.get('Title'): field.properties.get('InternalName') for field in fields}

def ensure_review_list(mbu, procedure_id, control_procedure, department='AUTOMATION'):
    """Return or create the standardized control review List."""
    ctx = get_context(department)
    list_title = f'{mbu} {procedure_id} - {control_procedure}'
    safe_title = list_title.replace("'", "''")
    existing_lists = ctx.web.lists.filter(f"Title eq '{safe_title}'").get().execute_query()

    if existing_lists:
        results_list = existing_lists[0]
    else:
        results_list = create_review_list(ctx, list_title)

    field_map = get_review_list_map(results_list)
    required_fields = ['Status', 'View Detailed Results', 'Run Time', 'Run ID']
    missing_fields = [field for field in required_fields if field not in field_map]

    if missing_fields:
        raise ValueError('SharePoint Review List is missing required fields: ' + ', '.join(missing_fields))

    root_folder = results_list.root_folder
    ctx.load(root_folder)
    ctx.execute_query()
    server_relative_url = root_folder.properties['ServerRelativeUrl']
    list_url = 'https://kbna.sharepoint.com' + quote(server_relative_url, safe='/')

    return ctx, results_list, list_url

def create_review_list_item(results_list, run_context, results_for_review, history_table):
    """Create or update a SharePoint result item using RUN_ID as the unique key."""
    field_map = get_review_list_map(results_list)
    required_fields = ['Status', 'View Detailed Results', 'Run Time', 'Run ID']
    missing_fields = [field for field in required_fields if field not in field_map]

    if missing_fields:
        raise ValueError('SharePoint Review List is missing required fields: ' + ', '.join(missing_fields))

    run_id = str(run_context['RUN_ID']).strip()
    run_time = pd.Timestamp(run_context['RUN_TIME_START_UTC']).floor('s')
    item_title = (f'{run_time:%m-%d-%Y} - {results_for_review:,} Result(s)')
    status = 'Complete' if results_for_review == 0 else 'New'
    history_url = bq.get_table_url(history_table)
    detailed_results = FieldUrlValue(history_url, 'View Detailed Results')

    item_values = {
        'Title': item_title,
        field_map['Status']: status,
        field_map['View Detailed Results']: detailed_results,
        field_map['Run Time']: run_time.isoformat(),
        field_map['Run ID']: run_id                
    }

    existing_items = results_list.items.get_all().execute_query()
    existing_results = {str(item.properties.get(field_map['Run ID'], '')).strip(): item for item in existing_items if item.properties.get(field_map['Run ID'])}

    if run_id in existing_results:
        item = existing_results[run_id]

        for field, value in item_values.items():
            item.set_property(field, value)

        item.update().execute_query()
        print(f'Updated SharePoint Review List item: {item_title}')

    else:
        item = results_list.add_item(item_values).execute_query()
        print(f'Created SharePoint Review List item: {item_title}')

    return item