"""
Control Assembly
----------------
Assembles standardized Control Automation Python scripts from CONFIG.

Key steps:
1. Accepts a Procedure ID (CP-Number) as a command-line argument. (Example: python Control_Assembly.py --cp-number CP-XXXXXXXX)
2. Retrieves the authoritative MBU, PROCEDURE_ID, and CONTROL_PROCEDURE from `taw-entpayments-prod-2935.AW_COMMERCIAL_CP.CONFIG`.
3. Validates that exactly one configuration record exists per control procedure.
4. Derives standardized Python, Cloud Run, BigQuery, and SharePoint identifiers.
5. Assembles the standardized Control Automation Python script.
"""
import argparse

from pathlib import Path

from utilities import bq, constants, utils

utils.load_secrets()
client = bq.get_client()

DEV_DIR = Path(__file__).resolve().parent.parent
AUTOMATION_DIR = DEV_DIR / 'automation'
PREASSEMBLED_DIR = DEV_DIR / 'preassembled'

def get_control_config(procedure_id: str) -> dict:
    """Retrieve and validate one control configuration record from CONFIG."""
    config = bq.get_control_config(procedure_id, client=client)
    config['MBU'] =str(config['MBU']).strip().upper()
    config['CONTROL_PROCEDURE'] = str(config['CONTROL_PROCEDURE']).strip()

    if config['MBU'] not in constants.MBU_NAMES:
        raise ValueError(f'Invalid MBU for {config['PROCEDURE_ID']}: {config['MBU']}')

    if not config['CONTROL_PROCEDURE']:
        raise ValueError(f'Control Procedure is missing for {config['PROCEDURE_ID']}.')

    return config

def build_control_names(config: dict) -> dict:
    """Derive standardized names from configuration."""
    mbu = config['MBU']
    procedure_id = config['PROCEDURE_ID']
    formatted_id = procedure_id.replace('-', '_')
    technical_id = f'{mbu}_{formatted_id}'

    return {
        'TECHNICAL_ID': technical_id,
        'PYTHON_FILE': f'{technical_id}.py',
        'CLOUD_RUN_JOB': technical_id.lower().replace('_', '-'),
        'HISTORY_TABLE': f'{constants.DATASET}.{technical_id}',
        'ETL_TABLE': f'{constants.DATASET}.{technical_id}_ETL',
        'REVIEW_LIST': f'{mbu} {procedure_id} - {config['CONTROL_PROCEDURE']}'
    }

def build_control_script(config: dict, names: dict) -> str:
    """Build the standardized control automation script."""
    mbu = config['MBU']
    procedure_id = config['PROCEDURE_ID']
    formatted_id = procedure_id.replace('-', '_')
    control_procedure = config['CONTROL_PROCEDURE']
    return f'''"""
Commercial Bank Control Automation
MBU: {constants.MBU_NAMES.get(mbu, mbu)}
Procedure ID: {procedure_id}
Control Procedure: {control_procedure}
------------------------------------------------------
<< enter script description here >>
"""
############################## DEVELOPER INSTRUCTIONS ##############################
# Required Inputs
# ---------------
# 1. LIVE_EMAIL (actual email recipients)
# 2. DATA_TABLES (source table(s) amd freshness date column(s))
# 3. FREQUENCY ('DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', or 'ANNUALLY')
# 4. POPULATION_RECORD ('description of one record in the evaluated population') and REVIEW_RECORD ('description of one record for review')
# 5. RESULT_SCHEMA (minimum columns required to meet the population and risk logic requirements of the control procedure)
# 6. MERGE_KEYS (this defines what counts as a unique result)
# 7. Evaluated Population Query (defines the total population evaluated during each run of the query)
# 8. Risk Logic Query (applies the risk criteria filters to the Evaluated Population Query)

# Query Standards
# ---------------
# Result columns should contain only the minimum fields required to:
#
# 1. Define the evaluated population
# 2. Apply the documented control risk logic
# 3. Explain why records require review (REVIEW_CRITERIA column)
# 4. Assist control reviewer in dispositioning results and retaining evidence.
####################################################################################
import os

import pandas as pd

from utilities import bq, constants, logs, sp, tables, utils

utils.load_secrets()
client = bq.get_client()

# Configured Constants
MBU = {mbu!r}
CONTROL_PROCEDURE = {control_procedure!r}
PROCEDURE_ID = {procedure_id!r}
FORMATTED_ID = {formatted_id!r}
HISTORY_TABLE = f'{{constants.DATASET}}.{{MBU}}_{{FORMATTED_ID}}'

############################## REQUIRED INPUTS START ##############################
# 1. Add email recipients as needed. 
 
# Example:
# LIVE_EMAIL = [
#   'CONTROL_REVIEWER@keybank.com',
#   'CONTROL_OWNER@keybank.com',
#   'CONTROL_DELEGATE@keybank.com',
#   'TEAM_MAILBOX@keybank.com',
#   constants.FROM_EMAIL
# ]

# Email Testing and Recipients
TEST_MODE = os.getenv('TEST_MODE', 'True').lower() == 'true'
LIVE_EMAIL = [

    constants.FROM_EMAIL
]
TO_EMAIL = constants.FROM_EMAIL if TEST_MODE else LIVE_EMAIL

# 2. Define source table(s) and their freshness-date column(s). More than one table may not be necessary.

# Example:
# SOURCE_TABLE_1 = 'project.dataset.table_1'
# SOURCE_TABLE_2 = 'project.dataset.table_2'
# DATA_TABLES = {{
#    SOURCE_TABLE_1: 'DATE_COLUMN'
#    SOURCE_TABLE_2: 'DATE_COLUMN'
# }}

# Data Source and Freshness Contracts
SOURCE_TABLE_1 = ''
SOURCE_TABLE_2 = ''

DATA_TABLES = {{}}

# 3. Enter one of the predefined control frequencies ['DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY'].

# Example:
# FREQUENCY = constants.CONTROL_FREQUENCY['DAILY']

FREQUENCY = constants.CONTROL_FREQUENCY['CHANGE_ME']

# 4. Description of one record in the evaluated population and one record for review.

# Example:
# POPULATION_RECORD = 'One Commercial Card company account as of the date evaulated'
# REVIEW_RECORD = 'One company requiring review for delinquency and missing credit-block treatment'

# Control Result and Persistence Contract
POPULATION_RECORD = ''
REVIEW_RECORD = ''

# 5. List the minimum columns needed to assess the population and apply the documented risk logic.

# Example:
# RESULT_SCHEMA = {{
#       'SNAPSHOT_DT': 'DATE',
#       'NAME': 'STRING', 
#       'COMP_NUM': 'INT64',
#       'IPI': 'INT64',
#       'COMPANY_CREDIT_LMT': 'INT64',
#       'TOTAL_OUTSTANDING': 'NUMERIC',
#       'DEL_DAYS': 'INT64',
#       'DEL_TOTAL': 'NUMERIC',
#       'DEL_UNDER_30': 'NUMERIC',
#       'DEL_OVER_30': 'NUMERIC',
#       'REVIEW_CRITERIA': 'STRING'
# }}

RESULT_SCHEMA = {{}}

RESULT_COLUMNS = list(RESULT_SCHEMA)

# 6. List the columns that uniquely identify a result.

# Example:
# MERGE_KEYS = ['COMP_NUM']

MERGE_KEYS = []

# 7. Define the total population evaluated during each run of the query.

# Example:
# SELECT
#   SNAPSHOT_DT
# , UPPER(COMPANY_NM) as NAME
# , COMPANY_NUM as COMP_NUM
# , IPI
# , CAST(COMPANY_CREDIT_LMT as INT64) as COMPANY_CREDIT_LMT
# , CRR_OUTSTANDINGS_AMT + OTH_OUTSTANDINGS_AMT as TOTAL_OUTSTANDING
# , NUM_OF_DAY_DLNQNT as DEL_DAYS
# , TOT_DLNQNCY_AMT as DEL_TOTAL
# , DLNQNT_5_DAY_AMT as DEL_UNDER_30
# , TOT_DLNQNCY_AMT - DLNQNT_5_DAY_AMT as DEL_OVER_30
# FROM `project.dataset.table`
# WHERE SNAPSHOT_DT = SOURCE_DATE
# AND CRR_OUTSTANDINGS_AMT + OTH_OUTSTANDINGS_AMT > 0
# QUALIFY ROW_NUMBER() OVER (PARTITION BY COMPANY_NUM ORDER BY SNAPSHOT_DT) = 1

def query_population_evaluated() -> str:
    """Return the population evaluated by the documented control procedure."""
    return f"""
    SELECT




    FROM `project.dataset.table`


    WHERE


    """

# 8. Apply the risk criteria filters to the Evaluated Population Query.

# Example:
# SELECT
#   *
# , '20+ days delinquent; delinquency > $50; credit block not applied' as REVIEW_CRITERIA
# FROM ({{population_evaluated}})
# WHERE DEL_DAYS >= 20
# AND COMPANY_CREDIT_LMT > 1
# AND DEL_TOTAL > 50

def query_risk_logic(population_evaluated: str) -> str:
    """Apply the the documented control procedure risk logic to the population evaluated."""
    return f"""
    SELECT
      *
    , '' as REVIEW_CRITERIA
    FROM ({{population_evaluated}})
    WHERE


    """
############################## REQUIRED INPUTS END ##############################

def validate_control_configuration():
    """Validate required control-specific configuration before execution."""
    errors = []

    if MBU not in constants.MBU_NAMES:
        errors.append(f'Invalid MBU: {{MBU}}')

    if not PROCEDURE_ID:
        errors.append('PROCEDURE_ID cannot be empty.')

    if not CONTROL_PROCEDURE:
        errors.append('CONTROL_PROCEDURE cannot be empty.')

    if not LIVE_EMAIL:
        errors.append('LIVE_EMAIL cannot be empty.')

    if not DATA_TABLES:
        errors.append('DATA_TABLES cannot be empty.')

    if FREQUENCY not in constants.CONTROL_FREQUENCY.values():
        errors.append(f'Invalid FREQUENCY: {{FREQUENCY}}')

    if not POPULATION_RECORD.strip():
        errors.append('POPULATION_RECORD cannot be empty.')

    if not REVIEW_RECORD.strip():
        errors.append('REVIEW_RECORD cannot be empty.')

    if not RESULT_SCHEMA:
        errors.append('RESULT_SCHEMA cannot be empty.')

    if not MERGE_KEYS:
        errors.append('MERGE_KEYS cannot be empty.')

    missing_merge_keys = [column for column in MERGE_KEYS if column not in RESULT_SCHEMA]

    if missing_merge_keys:
        errors.append('MERGE_KEYS contains fields not present in RESULT_SCHEMA: ' + ', '.join(missing_merge_keys))

    if errors:
        raise ValueError('Control configuration validation failed:\\n- ' + '\\n- '.join(errors))

def build_merge_condition():
    """Build the MERGE condition."""
    return '\\n    AND '.join(f'h.{{column}} = t.{{column}}' for column in MERGE_KEYS)

def get_null_expression(column: str, data_type: str) -> str:
    """Return a typed NULL expression for the persistence summary row."""
    return f'CAST(NULL AS {{data_type}} as {{column}}'

def merge_records(query: str, run_time, run_context) -> tuple[pd.DataFrame, int, int, int]:
    """Add new results to history and return the current run results and counts."""
    insert_columns = '\\n    , '.join(RESULT_COLUMNS)
    value_columns = '\\n    , '.join(f't.{{column}}' for column in RESULT_COLUMNS)
    merge_condition = build_merge_condition()
    summary_nulls = '\\n    , '.join(get_null_expression(column, data_type) for column, data_type in RESULT_SCHEMA.items())
    run_time = pd.Timestamp(run_time).floor('s').isoformat()

    query = f"""
    DECLARE run_time TIMESTAMP DEFAULT TIMESTAMP_TRUNC('{{run_time}}', SECOND);
    DECLARE results_identified INT64;
    DECLARE results_inserted INT64;

    CREATE TEMP TABLE temp_table AS {{query}};
    SET results_identified = (SELECT COUNT(*) FROM temp_table);

    MERGE `{{HISTORY_TABLE}}` h
    USING temp_table t
    ON {{merge_condition}}
    WHEN NOT MATCHED THEN
    INSERT (RUN_TIME_UTC, UNIQUE_ID, {{insert_columns}})
    VALUES (run_time, GENERATE_UUID(), {{value_columns}});

    SET results_inserted = (SELECT COUNT(*) FROM `{{HISTORY_TABLE}}` WHERE RUN_TIME_UTC = run_time);

    SELECT
      FALSE as SUMMARY_ROW
    , results_identified as RESULTS_IDENTIFIED
    , results_inserted as RESULTS_INSERTED
    , RUN_TIME_UTC
    , UNIQUE_ID
    , {{insert_columns}}
    FROM `{{HISTORY_TABLE}}`
    WHERE RUN_TIME_UTC = run_time

    UNION ALL

    SELECT
      TRUE as SUMMARY_ROW
    , results_identified as RESULTS_IDENTIFIED
    , results_inserted as RESULTS_INSERTED
    , CAST(NULL AS TIMESTAMP) as RUN_TIME_UTC
    , CAST(NULL AS STRING) as UNIQUE_ID
    , {{summary_nulls}}
    """

    start_time = pd.Timestamp.now(tz='UTC').floor('s')

    try:
        query_job = client.query(query)
        output = query_job.to_dataframe().convert_dtypes()
        query_duration_seconds = int((pd.Timestamp.now(tz='UTC).floor('s') - start_time).total_seconds())
        summary = output[output['SUMMARY_ROW']].iloc[0]
        results_identified = int(summary['RESULTS_IDENTIFIED'])
        results_inserted = int(summary['RESULTS_INSERTED'])
        results_skipped = results_identified - results_inserted
        results = output[~output['SUMMARY_ROW']].drop(columns=['SUMMARY_ROW', 'RESULTS_IDENTIFIED', 'RESULTS_INSERTED']).reset_index(drop=True)

        logs.log_diagnostic(
            run_context=run_context,
            step_name='REVIEW_QUERY',
            component='BIGQUERY',
            status='SUCCESS',
            row_count=results_identified,
            query_job_id=query_job.job_id,
            bytes_processed=getattr(query_job, 'total_bytes_processed', None),
            query_duration_seconds=query_duration_seconds,
            detail_message=f'Review query and history persistence completed. Inserted: {{results_inserted:,}}; skipped: {{results_skipped:,}}.',
            client=client
            )

        return results, results_identified, results_inserted, results_skipped
    except Exception as e:
        logs.log_diagnostic(
            run_context=run_context,
            step_name='REVIEW_QUERY',
            component='BIGQUERY',
            status='FAILED',
            source_object=HISTORY_TABLE,
            error_message=e,
            client=client
            )
        raise

def get_control_results(run_context) -> tuple[pd.DataFrame, int, int, int, int, str, str]:
    """Execute the control queries, persist new results, return results, counts, and query hashes."""
    bq.create_history_table(HISTORY_TABLE, RESULT_SCHEMA, client=client)
    population_query = query_population_evaluated()
    review_query = query_risk_logic(population_query)
    population_query_hash = logs.hash_text(population_query)
    review_query_hash = logs.hash_text(review_query)
    population_evaluated = bq.get_population_evaluated(population_query, client=client, run_context=run_context)
    results, results_identified, results_inserted, results_skipped = merge_records(review_query, run_context['RUN_TIME_START_UTC'], run_context)

    return results, population_evaluated, results_identified, results_inserted, results_skipped, population_query_hash, review_query_hash

def send_notifications(results, population_evaluated, result_location, run_context):
    """Send the standardized control automation completion notification."""
    return utils.send_email_notification(
        results=results,
        recipients=TO_EMAIL,
        mbu=MBU,
        procedure_id=PROCEDURE_ID,
        control_procedure=CONTROL_PROCEDURE,
        history_table=HISTORY_TABLE,
        population_evaluated=population_evaluated,
        run_time=run_context['RUN_TIME_START_UTC'],
        result_location=result_location
    )

def main():
    """Execute the control pipeline and record configuration, freshness, results, review, notification, and execution outcomes."""
    run_context = logs.create_run_context(MBU, PROCEDURE_ID, CONTROL_PROCEDURE, execution_mode='TEST' if TEST_MODE else 'PRODUCTION')

    population_evaluated = None
    results_identified = None
    results_inserted = None
    results_skipped = None
    population_query_hash = None
    review_query_hash = None

    configuration_status = 'SKIPPED'
    freshness_status = 'SKIPPED'
    population_query_status = 'SKIPPED'
    review_query_status = 'SKIPPED'
    history_write_status = 'SKIPPED'    
    review_write_status = 'SKIPPED'
    email_status = 'SKIPPED'
    email_result = None

    try:
        validate_control_configuration()
        configuration_status = 'SUCCESS'

        logs.log_diagnostic(
            run_context=run_context,
            step_name='CONFIGURATION_VALIDATION',
            component='CONTROL',
            status='SUCCESS',
            detail_message='Configuration validated successfully.',
            client=client
        )

        stale_tables = bq.validate_table_freshness(DATA_TABLES, FREQUENCY, run_context=run_context, client=client)
        freshness_status = 'FAILED' if not stale_tables.empty else 'SUCCESS'

        if not stale_tables.empty:
            freshness_subject = f'{{constants.MBU_NAMES.get(MBU, MBU)}} {{CONTROL_PROCEDURE}} - STALE DATA'

            freshness_body = (
                'Data freshness validation failed:\\n\\n'
                + '\\n'.join(
                    f"{{row['TABLE_ID']}}\\n"
                    f"Required: {{row['REQUIRED_DT']}}\\n"
                    f"Observed: {{row['MAX_DT']}}"
                    for _, row in stale_tables.iterrows()
                )
            )

            email_result = utils.send_email(TO_EMAIL, freshness_subject, freshness_body)
            email_status = 'SUCCESS'

            logs.log_diagnostic(
                run_context=run_context,
                step_name='EMAIL_NOTIFICATION',
                component='SMTP',
                status='SUCCESS',
                observed_value=';'.join(email_result['RECIPIENTS']),
                row_count=len(email_result['RECIPIENTS']),
                detail_message=email_result['SUBJECT'],
                client=client
            )            

            logs.log_execution(
                run_context=run_context,
                status='HALTED_STALE_DATA',
                configuration_status=configuration_status,
                freshness_status=freshness_status,
                population_query_status=population_query_status,
                review_query_status=review_query_status,
                history_write_status=history_write_status,
                review_write_status=review_write_status,
                email_status=email_status,
                intended_recipients=LIVE_EMAIL,
                actual_recipients=TO_EMAIL,
                error_step='SOURCE_FRESHNESS',
                error_message='Stale tables detected: ' + ', '.join(stale_tables['TABLE_ID'].astype(str).tolist()),
                client=client
            )
            return

        results, population_evaluated, results_identified, results_inserted, results_skipped, population_query_hash, review_query_hash = get_control_results(run_context)
        population_query_status = 'SUCCESS'
        review_query_status = 'SUCCESS'
        history_write_status = 'SUCCESS'
        _, results_list, result_location = sp.ensure_review_list(MBU, PROCEDURE_ID, CONTROL_PROCEDURE)
        review_item = sp.create_review_list_item(results_list, run_context, results_inserted, HISTORY_TABLE)
        review_write_status = 'SUCCESS'

        logs.log_diagnostic(
            run_context=run_context,
            step_name='REVIEW_PUBLICATION',
            component='SHAREPOINT',
            status='SUCCESS',
            record_id=review_item.properties.get('Id'),
            destination_location=result_location,
            row_count=1,
            detail_message='SharePoint review item published successfully.',
            client=client
        )   

        email_result = send_notifications(results, population_evaluated, result_location, run_context)
        email_status = 'SUCCESS'

        logs.log_diagnostic(
            run_context=run_context,
            step_name='EMAIL_NOTIFICATION',
            component='SMTP',
            status='SUCCESS',
            observed_value=';'.join(email_result['RECIPIENTS']),
            row_count=len(email_result['RECIPIENTS']),
            detail_message=email_result['SUBJECT'],
            client=client
        )  

        status = 'SUCCESS_ZERO_RESULTS' if results_inserted == 0 else 'SUCCESS'

        logs.log_diagnostic(
            run_context=run_context,
            step_name='EXECUTION_COMPLETE',
            component='CONTROL',
            status='SUCCESS',
            observed_value=status,
            detail_message='Automation executed successfully.',
            client=client
        )

        logs.log_execution(
                run_context=run_context,
                status=status,
                population_evaluated=population_evaluated,
                results_identified=results_identified,
                results_inserted=results_inserted,
                results_skipped=results_skipped,
                configuration_status=configuration_status,
                freshness_status=freshness_status,
                population_query_status=population_query_status,
                review_query_status=review_query_status,
                history_write_status=history_write_status,
                review_write_status=review_write_status,
                email_status=email_status,
                intended_recipients=LIVE_EMAIL,
                actual_recipients=TO_EMAIL,
                email_subject=email_result['SUBJECT'],
                population_query_hash=population_query_hash,
                review_query_hash=review_query_hash,
                client=client
        )

    except Exception as e:
        print(f'Pipeline execution error: {{e}}')

        error_step = 'CONFIGURATION_VALIDATION' if configuration_status == 'SKIPPED' else 'EXECUTION'
        failure_status = 'FAILED_CONFIGURATION' if error_step == 'CONFIGURATION_VALIDATION' else 'FAILED_UNKNOWN'

        try:
            logs.log_diagnostic(
                run_context=run_context,
                step_name=error_step,
                component='CONTROL',
                status='FAILED',
                error_message=e,
                client=client
            )            

            logs.log_execution(
                    run_context=run_context,
                    status=failure_status,
                    population_evaluated=population_evaluated,
                    results_identified=results_identified,
                    results_inserted=results_inserted,
                    results_skipped=results_skipped,
                    configuration_status= 'FAILED' if failure_status == 'FAILED_CONFIGURATION' else configuration_status,
                    freshness_status=freshness_status,
                    population_query_status=population_query_status,
                    review_query_status=review_query_status,
                    history_write_status=history_write_status,
                    review_write_status=review_write_status,
                    email_status=email_status,
                    intended_recipients=LIVE_EMAIL,
                    actual_recipients=TO_EMAIL,
                    email_subject=(email_result['SUBJECT'] if email_result else None),
                    population_query_hash=population_query_hash,
                    review_query_hash=review_query_hash,
                    error_step=error_step,
                    error_message=e,
                    client=client
            )
        except Exception as e:
            print('Failed to record execution diagnostics: ' f'{{e}}')

        raise

if __name__ == '__main__':
    main()
'''

def display_control_config(config: dict, names: dict):
    """Display the resolved control configuration and derived names."""
    print('\nControl Configuration')
    print('---------------------')
    print(f'MBU:                {config['MBU']}')
    print(f'MBU Name:           {constants.MBU_NAMES.get(config['MBU'], config['MBU'])}')
    print(f'Procedure ID:       {config['PROCEDURE_ID']}')
    print(f'Control Procedure:  {config['CONTROL_PROCEDURE']}')
    print('\nDerived Names')
    print('-------------')
    print(f'Python File:        {names['PYTHON_FILE']}')
    print(f'Cloud Run Job:      {names['CLOUD_RUN_JOB']}')
    print(f'History Table:      {names['HISTORY_TABLE']}')
    print(f'ETL Table:          {names['ETL_TABLE']}')
    print(f'Review List Name:   {names['REVIEW_LIST']}')

def write_control_script(config: dict, names: dict) -> bool:
    """Write a new control script to preassembly unless it already exists."""
    PREASSEMBLED_DIR.mkdir(parents=True, exist_ok=True)

    preassembled_file = PREASSEMBLED_DIR / names['PYTHON_FILE']
    active_file = AUTOMATION_DIR / names['PYTHON_FILE']

    if active_file.exists():
        print(f'\nControl script already exists in development: {active_file}')
        return False

    if preassembled_file.exists():
        print(f'\nControl script already exists in preassembly: {preassembled_file}')
        return False

    preassembled_file.write_text(build_control_script(config, names), encoding='utf-8')
    print(f'\nPreassembled control script: {preassembled_file}')
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--procedure-id', '--cp-number', dest='procedure_id', required=True)
    args = parser.parse_args()
    config = get_control_config(args.procedure_id)
    names = build_control_names(config)
    display_control_config(config, names)
    write_control_script(config, names)

if __name__ == '__main__':
    main()