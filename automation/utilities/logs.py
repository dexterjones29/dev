"""
Log Utilities Package
---------------------
- hash_text()
- create_run_context()
- log_diagnostic()
- log_execution()
"""

import hashlib
import pandas as pd
import re
import uuid

from . import bq
from .constants import COMPONENT_STATUSES, DIAGNOSTIC_LOG, EXECUTION_MODES, EXECUTION_STATUSES, EXECUTION_LOG, TRIGGER_TYPES

def hash_text(value: str) -> str:
    """Return a SHA-256 hash for normalized non-empty text."""
    if not isinstance(value, str):
        raise TypeError('hash_text() requires a string.')

    normalized = re.sub(r'\s+', ' ', value).strip()

    if not normalized:
        raise ValueError('Cannot hash empty text.')

    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def create_run_context(mbu, procedure_id, control_procedure, execution_mode='PRODUCTION', trigger_type=None, rerun_ind=False):
    """Create standardized execution metadata for one control run."""
    execution_mode = execution_mode.strip().upper()

    if execution_mode not in EXECUTION_MODES:
        raise ValueError(f'Invalid execution mode: {execution_mode}')

    if trigger_type:
        trigger_type = trigger_type.strip().upper()

        if trigger_type not in TRIGGER_TYPES:
            raise ValueError(f'Invalid trigger type: {trigger_type}')

    return {
        'RUN_ID': str(uuid.uuid4()),
        'RUN_TIME_START_UTC': pd.Timestamp.now(tz='UTC').floor('s'),
        'RUN_TIME_END_UTC': None,
        'DURATION_SECONDS': None,
        'MBU': mbu.strip().upper(),
        'PROCEDURE_ID': str(procedure_id).strip().upper(),
        'CONTROL_PROCEDURE': str(control_procedure).strip(),
        'EXECUTION_MODE': execution_mode,
        'TRIGGER_TYPE': trigger_type,
        'RERUN_IND': rerun_ind,
        'DIAGNOSTIC_SEQUENCE': 0
    }

def log_diagnostic(
        run_context,
        step_name,
        status,
        component=None,
        source_object=None,
        source_field=None,
        expected_value=None,
        observed_value=None,
        row_count=None,
        query_job_id=None,
        bytes_processed=None,
        query_duration_seconds=None,
        record_id=None,
        destination_location=None,
        detail_message=None,
        error_message=None,
        event_sequence=None,
        client=None
):
    """Write one step-level diagnostic even for a control execution."""
    if client is None:
        client = bq.get_client()

    status = status.strip().upper()

    if status not in COMPONENT_STATUSES:
        raise ValueError(f'Invalid diagnostic status: {status}')

    if event_sequence is None:
        run_context['DIAGNOSTIC_SEQUENCE'] = run_context.get('DIAGNOSTIC_SEQUENCE', 0) + 1
        event_sequence = run_context['DIAGNOSTIC_SEQUENCE']

    row = [{
        'DIAGNOSTIC_ID': str(uuid.uuid4()),
        'RUN_ID': run_context['RUN_ID'],
        'EVENT_TIME_UTC': pd.Timestamp.now(tz='UTC').floor('s'),
        'EVENT_SEQUENCE': event_sequence,
        'MBU': run_context['MBU'],
        'PROCEDURE_ID': run_context['PROCEDURE_ID'],
        'CONTROL_PROCEDURE': run_context['CONTROL_PROCEDURE'],
        'EXECUTION_MODE': run_context['EXECUTION_MODE'],
        'STEP_NAME': step_name.strip().upper(),
        'COMPONENT': component,
        'STATUS': status,
        'SOURCE_OBJECT': source_object,
        'SOURCE_FIELD': source_field,
        'EXPECTED_VALUE': str(expected_value) if expected_value is not None else None,
        'OBSERVED_VALUE': str(observed_value) if observed_value is not None else None,
        'ROW_COUNT': row_count,
        'QUERY_JOB_ID': query_job_id,
        'BYTES_PROCESSED': bytes_processed,
        'QUERY_DURATION_SECONDS': query_duration_seconds,
        'RECORD_ID': str(record_id) if record_id is not None else None,
        'DESTINATION_LOCATION': destination_location,
        'DETAIL_MESSAGE': detail_message,
        'ERROR_MESSAGE': str(error_message) if error_message else None
    }]

    client.load_table_from_dataframe(pd.DataFrame(row), DIAGNOSTIC_LOG).result()
    return row[0]

def log_execution(
        run_context,
        status,
        population_evaluated=None,
        results_identified=None,
        results_inserted=None,
        results_skipped=None,
        configuration_status=None,
        freshness_status=None,
        population_query_status=None,
        review_query_status=None,
        history_write_status=None,
        review_write_status=None,
        email_status=None,
        intended_recipients=None,
        actual_recipients=None,
        email_subject=None,
        image_tag=None,
        git_commit=None,
        config_hash=None,
        population_query_hash=None,
        review_query_hash=None,
        error_step=None,
        error_message=None,
        client=None,
):
    """Write one run-level execution record and finalize execution timing."""
    if client is None:
        client = bq.get_client()

    status = status.strip().upper()

    if status not in EXECUTION_STATUSES:
        raise ValueError(f'Invalid execution status: {status}')

    end_time = pd.Timestamp.now(tz='UTC').floor('s')
    start_time = pd.Timestamp(run_context['RUN_TIME_START_UTC']).floor('s')
    duration_seconds = int((end_time - start_time).total_seconds())
    run_context['RUN_TIME_END_UTC'] = end_time
    run_context['DURATION_SECONDS'] = duration_seconds

    intended_recipients = ';'.join(intended_recipients) if isinstance(intended_recipients, (list, tuple)) else intended_recipients
    actual_recipients = ';'.join(actual_recipients) if isinstance(actual_recipients, (list, tuple)) else actual_recipients

    row = [{
        'RUN_ID': run_context['RUN_ID'],
        'RUN_TIME_START_UTC': start_time,
        'RUN_TIME_END_UTC': end_time,
        'DURATION_SECONDS': duration_seconds,
        'MBU': run_context['MBU'],
        'PROCEDURE_ID': run_context['PROCEDURE_ID'],
        'CONTROL_PROCEDURE': run_context['CONTROL_PROCEDURE'],
        'EXECUTION_MODE': run_context['EXECUTION_MODE'],
        'TRIGGER_TYPE': run_context['TRIGGER_TYPE'],
        'RERUN_IND': run_context['RERUN_IND', False],
        'STATUS': status,
        'POPULATION_EVALUATED': population_evaluated,
        'RESULTS_IDENTIFIED': results_identified,
        'RESULTS_INSERTED': results_inserted,
        'RESULTS_SKIPPED': results_skipped,
        'CONFIGURATION_STATUS': configuration_status,
        'FRESHNESS_STATUS': freshness_status,
        'POPULATION_QUERY_STATUS': population_query_status,
        'REVIEW_QUERY_STATUS': review_query_status,
        'HISTORY_WRITE_STATUS': history_write_status,
        'REVIEW_WRITE_STATUS': review_write_status,
        'EMAIL_STATUS': email_status,
        'INTENDED_RECIPIENTS': intended_recipients,
        'ACTUAL_RECIPIENTS': actual_recipients,
        'EMAIL_SUBJECT': email_subject,
        'IMAGE_TAG': image_tag,
        'GIT_COMMIT': git_commit,
        'CONFIG_HASH': config_hash,
        'POPULATION_QUERY_HASH': population_query_hash,
        'REVIEW_QUERY_HASH': review_query_hash,
        'ERROR_STEP': error_step,
        'ERROR_MESSAGE': str(error_message) if error_message else None
    }]

    client.load_table_from_dataframe(pd.DataFrame(row), EXECUTION_LOG).result()
    return row[0]