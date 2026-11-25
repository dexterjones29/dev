"""
BigQuery Utilities Package
--------------------------
- get_client()
- query_to_df()
- get_control_config()
- get_table_url()
- create_history_table()
- create_etl_table()
- validate_table_freshness()
- get_population_evaluated()
- load_to_table()
- get_latest_file_date()
"""
import datetime as dt
import pandas as pd

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from .constants import CONFIG, PROJECT

def get_client(project_id: str = PROJECT) -> bigquery.Client:
    """Return an authenticated BigQuery client using Application Default Credentials"""
    return bigquery.Client(project=project_id, location='US')

def query_to_df(query, job_config=None, client=None):
    """Execute a BigQuery query and return a nullable-typed DataFrame."""
    if client is None:
        client = get_client()

    return client.query(query, job_config=job_config).to_dataframe().convert_dtypes()

def get_control_config(procedure_id, client=None):
    """Return one control record from CONFIG."""
    if client is None:
        client = get_client()

    procedure_id = str(procedure_id).strip().upper().replace('_', '-')

    if not procedure_id.startswith('CP-'):
        procedure_id = f'CP-{procedure_id}'

    if not procedure_id.replace('CP-', '').isdigit():
        raise ValueError(f'Invalid Procedure ID: {procedure_id}')

    query = f"""
    SELECT *
    FROM `{CONFIG}`
    WHERE PROCEDURE_ID = @procedure_id
    """

    job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('procedure_id', 'STRING', procedure_id)])
    results = query_to_df(query, job_config=job_config, client=client)

    if results.empty:
        raise ValueError(f'No CONFIG record found fo {procedure_id}.')

    if len(results) > 1:
        raise ValueError(f'Multiple CONFIG records found fo {procedure_id}.')

    return results.iloc[0].to_dict()

def get_table_url(table_id):
    """Return the Google Cloud Console URL for a fully qualified BigQuery table."""
    project_id, dataset_name, table_name = table_id.split('.')
    return f'https://console.cloud.google.com/bigquery?ws=!1m5!1m4!4m3!1s{project_id}!2s{dataset_name}!3s{table_name}'

def create_history_table(table_id, result_schema, client=None):
    """Create a history table if it doesn't already exist."""
    if client is None:
        client = get_client()

    try:
        client.get_table(table_id)
        return

    except NotFound:
        pass

    schema = [
        bigquery.SchemaField('RUN_TIME_UTC', 'TIMESTAMP'),
        bigquery.SchemaField('UNIQUE_ID', 'STRING')
    ]
    schema.extend(bigquery.SchemaField(column, data_type) for column, data_type in result_schema.items())
    client.create_table(bigquery.Table(table_id, schema=schema))
    print(f'Created history table: {table_id}')

def create_etl_table(table_id, etl_schema, client=None):
    """Create an ETL table with standard lineage fields if it doesn't already exist."""
    if client is None:
        client = get_client()

    try:
        client.get_table(table_id)
        return

    except NotFound:
        pass

    schema = [
        bigquery.SchemaField('FILE_NAME', 'STRING'),
        bigquery.SchemaField('FILE_DATE', 'DATE'),
        bigquery.SchemaField('LOAD_TIME_UTC', 'TIMESTAMP')
    ]
    schema.extend(bigquery.SchemaField(column, data_type) for column, data_type in etl_schema.items())
    client.create_table(bigquery.Table(table_id, schema=schema))
    print(f'Created ETL table: {table_id}')

def validate_table_freshness(table_list, frequency, date_column='SNAPSHOT_DT', run_context=None, client=None):
    """Validate source freshness and optionally record source-level diagnostic evidence."""
    if client is None:
        client = get_client()

    table_items = table_list.items() if isinstance(table_list, dict) else [(table, date_column) for table in table_list]
    table_items = list(table_items)

    if not table_items:
        raise ValueError('No source tables were provided for freshness validation.')

    sub_queries = []

    for table, date_field in table_items:
        clean_table = table.replace(':', '.')
        sub_queries.append(
            f"""
            SELECT
              '{table}' as TABLE_ID
            , '{date_field}' as DATE_FIELD
            , MAX({date_field}) as MAX_DT
            FROM `{clean_table}`
            """
        )
    main_query = f"""
    WITH

    results AS (
    
    {' UNION ALL '.join(sub_queries)}
    )

    SELECT
      TABLE_ID
    , DATE_FIELD
    , MAX_DT
    , ({frequency}) as REQUIRED_DT
    , CASE WHEN MAX_DT >= ({frequency}) THEN 'SUCCESS' ELSE 'FAILED' END as STATUS
    FROM results
    """
    start_time = pd.Timestamp.now(tz='UTC').floor('s')

    try:
        query_job = client.query(main_query)
        results = query_job.to_dataframe()
        query_duration_seconds = int((pd.Timestamp.now(tz='UTC').floor('s') - start_time).total_seconds())

    except Exception as e:
        if run_context:
            from .logs import log_diagnostic

            log_diagnostic(
                run_context=run_context,
                step_name='SOURCE_FRESHNESS',
                component='BIGQUERY',
                status='FAILED',
                detail_message='Source freshness query failed.',
                error_message=e,
                client=client
            )
        print(main_query)
        raise

    for _, row in results.iterrows():
        if run_context:
            from .logs import log_diagnostic

            log_diagnostic(
                run_context=run_context,
                step_name='SOURCE_FRESHNESS',
                component='BIGQUERY',
                status=row['STATUS'],
                source_object=row['TABLE_ID'],
                source_field=row['DATE_FIELD'],
                expected_value=row['REQUIRED_DT'],
                observed_value=row['MAX_DT'],
                query_job_id=query_job.job_id,
                bytes_processed=getattr(query_job, 'total_bytes_processed', None),
                query_duration_seconds=query_duration_seconds,
                detail_message='Source freshness validation completed.',
                client=client
            )

    stale_results = results[results['STATUS'] == 'FAILED'].copy()

    if stale_results.empty:
        print('DATA FRESHNESS CHECK PASSED')

        for _, row in results.iterrows():
            print(f" - {row['TABLE_ID']} | Requred: {row['REQUIRED_DT']} | Observed: {row['MAX_DT']}")

        return stale_results

    print('STALE TABLES DETECTED:')

    for _, row in stale_results.iterrows():
        print(f" - {row['TABLE_ID']} | Requred: {row['REQUIRED_DT']} | Observed: {row['MAX_DT']}")

    return stale_results

def get_population_evaluated():
    """Return the evaluated population count and optionally record query diagnostics."""
    if client is None:
        client = get_client()

    main_query = f"""
    SELECT
      COUNT(*) as POPULATION_EVALUATED
    FROM ({population_query})
    """
    start_time = pd.Timestamp.now(tz='UTC').floor('s')

    try:
        query_job = client.query(main_query)
        population_evaluated = int(query_job.to_dataframe().iloc[0]['POPULATION_EVALUATED'])
        query_duration_seconds = int((pd.Timestamp.now(tz='UTC').floor('s') - start_time).total_seconds())

        if run_context:
            from .logs import log_diagnostic

            log_diagnostic(
                run_context-run_context,
                step_name='POPULATION_QUERY',
                component='BIGQUERY',
                status='SUCCESS',
                row_count=population_evaluated,
                query_job_id=query_job.job_id,
                bytes_processed=getattr(query_job, 'total bytes processed', None),
                query_duration_seconds=query_duration_seconds,
                detail_message='Population query completed successfully.',
                client=client
            )

        return population_evaluated

    except Exception as e:
        if run_context:
            from .logs import log_diagnostic

            log_diagnostic(
                run_context=run_context,
                step_name='POPULATION_QUERY',
                component='BIGQUERY',
                status='FAILED',
                error_message=e,
                client=client
            )
        raise

def load_to_table():
    """Load a DataFrame into a BigQuery table."""
    if client is None:
        client = get_client()

    job_config = bigquery.LoadJobConfig()
    job_config.write_disposition = write_disposition
    job_config.ignore_unknown_values = True

    return client.load_table_from_dataframe(df, table_id, location='US', job_config=job_config).result()

def get_latest_file_date(table_id, default_date=dt.date(1900, 1, 1), client=None):
    """Return latest FILE_DATE, or default date when the table does not yet exist."""
    if client is None:
        client = get_client()

    query = f"""
    SELECT
      MAX(FILE_DATE) as FILE_DATE
    FROM `{table_id}`
    """

    try:
        result = client.query(query).result()
    except NotFound:
        print(f'Table does not exist yet: {table_id}. Using default FILE_DATE: {default_date}')
        return default_date

    row = next(result, None)

    if not row or row.FILE_DATE is None:
        return default_date

    print(f'Latest FILE_DATE in {table_id}: {row.FILE_DATE}')
    return row.FILE_DATE