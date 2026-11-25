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
        

    }]

    client.load_table_from_dataframe(pd.DataFrame(row), DIAGNOSTIC_LOG).result()
    return row[0]


def log_execution():
    """"""