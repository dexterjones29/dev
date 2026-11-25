"""
PCard Credit Block Review
-------------------------
This script monitors commercial card delinquencies and identifies accounts 20 or more days past due.
Delinquent accounts are logged and then routed for credit limit reduction to $1.

Key steps:
1. Validates that underlying source tables are fresh.
2. Identifies accounts needing credit limit reductions using BigQuery MERGE.
3. Fetches newly inserted audit records into Python.
4. Notifies stakeholders via email and Monday.com.
5. Logs job execution status to PIPELINE_EXECUTION_LOG.
"""
# Package Import, Environment Settings, BigQuery, SharePoint, and Monday.com Configuration
import pandas as pd
from utilities import shared_utils

shared_utils.load_secrets()
shared_utils.set_proxy()
client = shared_utils.get_bq_client()
# ctx = shared_utils.get_sharepoint_context('CPC')

# Pipeline Configuration Constants
PIPELINE_NAME = 'PCard_Credit_Block_Review'
HISTORY_TABLE = 'taw-entpayments-prod-2935.AW_PPD.PCARD_CREDIT_BLOCK_REVIEW'
CP_NUMBER = 'CP-12324886'
TO_EMAIL = ['Dexter_Jones@keybank.com']
FROM_EMAIL = 'CXPO_Commercial_Card@keybank.com'
BOARD_ID = 18427930042
# shared_utils.get_monday_column_map(BOARD_ID)

def check_data_freshness() -> bool:
    """Validate that underlying data source tables are updated within threshold."""
    stale_threshold = 'DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)'
    tables_to_check = ['esa-prod-7486.ESA_MART_ECP_DATA.PR360_CPC_ACCT_DLY']
    stale_tables = shared_utils.validate_table_freshness(tables_to_check, custom_threshold=stale_threshold)

    if stale_tables:
        subject = 'PCard Credit Block Review - STALE DATA'
        body = 'Data loads are not prepared for today. The following tables are stale:\n\n' + '\n'.join(stale_tables)
        shared_utils.send_email(TO_EMAIL, subject, body, from_email=FROM_EMAIL)
        print('Data loads are not prepared for today based upon the latest update date of the underlying tables.')
        
        shared_utils.log_execution(
            pipeline_name=PIPELINE_NAME,
            cp_number=CP_NUMBER,
            status='HALTED_STALE_DATA',
            records_processed=0,
            error_msg=f"Stale tables detected: {', '.join(stale_tables)}",
            client=client
        )
        return False
    
    return True

def retrieve_and_merge_records() -> pd.DataFrame:
    """Executes BigQuery MERGE to insert new results into the historical table and retrieves new results for notifications."""

    main_query = f"""
    DECLARE run_time STRING;
    SET run_time = FORMAT_DATETIME('%F %X', CURRENT_DATETIME('America/New_York'));

    -- Step 1: Create a temporary session table for candidate records
    CREATE TEMP TABLE temp_table AS
    SELECT
      SNAPSHOT_DT
    , UPPER(COMPANY_NM) AS NAME
    , COMPANY_NUM AS COMP_NUM
    , IPI
    , CAST(COMPANY_CREDIT_LMT as INT64) as COMPANY_CREDIT_LMT
    , CRR_OUTSTANDINGS_AMT + OTH_OUTSTANDINGS_AMT AS TOTAL_OUTSTANDING
    , NUM_OF_DAY_DLNQNT AS DEL_DAYS
    , TOT_DLNQNCY_AMT AS DEL_TOTAL
    , DLNQNT_5_DAY_AMT AS DEL_UNDER_30
    , TOT_DLNQNCY_AMT - DLNQNT_5_DAY_AMT AS DEL_OVER_30
    FROM `esa-prod-7486.ESA_MART_ECP_DATA.PR360_CPC_ACCT_DLY`
    WHERE SNAPSHOT_DT >= CURRENT_DATE()-3
    AND CRR_OUTSTANDINGS_AMT + OTH_OUTSTANDINGS_AMT > 0
    AND NUM_OF_DAY_DLNQNT >= 20
    AND COMPANY_CREDIT_LMT > 1
    AND TOT_DLNQNCY_AMT > 50
    QUALIFY ROW_NUMBER() OVER (PARTITION BY COMPANY_NUM ORDER BY SNAPSHOT_DT) = 1;

    -- Step 2: Merge non-duplicate records into historical table
    MERGE `{HISTORY_TABLE}` h
    USING temp_table t
    ON h.COMP_NUM = t.COMP_NUM
    AND h.DEL_UNDER_30 = t.DEL_UNDER_30
    AND PARSE_DATETIME('%Y-%m-%d %H:%M:%S', h.RUN_TIME_ET) >= DATETIME_SUB(CURRENT_DATETIME('America/New_York'), INTERVAL 30 DAY) -- Is there an entry for this account and balance logged within the last 30 days?
    WHEN NOT MATCHED THEN
      INSERT (
          RUN_TIME_ET
        , UNIQUE_ID
        , SNAPSHOT_DT
        , NAME
        , COMP_NUM
        , IPI
        , COMPANY_CREDIT_LMT
        , TOTAL_OUTSTANDING
        , DEL_DAYS
        , DEL_TOTAL
        , DEL_UNDER_30
        , DEL_OVER_30
      )
      VALUES (
          run_time
        , GENERATE_UUID()
        , t.SNAPSHOT_DT
        , t.NAME
        , t.COMP_NUM
        , t.IPI
        , t.COMPANY_CREDIT_LMT
        , t.TOTAL_OUTSTANDING
        , t.DEL_DAYS
        , t.DEL_TOTAL
        , t.DEL_UNDER_30
        , t.DEL_OVER_30
      );

    -- Step 3: Return newly inserted records for this execution batch
    SELECT *
    FROM `{HISTORY_TABLE}`
    WHERE RUN_TIME_ET = run_time
    ORDER BY COMP_NUM, SNAPSHOT_DT DESC, DEL_DAYS DESC;
    """

    results = client.query(main_query).to_dataframe().convert_dtypes()

    if not results.empty:
        results['SNAPSHOT_DT'] = pd.to_datetime(results['SNAPSHOT_DT'], errors='coerce').dt.date

        int_cols = ['COMP_NUM', 'IPI', 'COMPANY_CREDIT_LMT', 'DEL_DAYS']
        for col in int_cols:
            if col in results.columns:
                results[col] = results[col].astype('Int64')

        float_cols = ['TOTAL_OUTSTANDING', 'DEL_TOTAL', 'DEL_UNDER_30', 'DEL_OVER_30']
        for col in float_cols:
            if col in results.columns:
                results[col] = results[col].astype('Float64').round(2)

    return results

def send_notifications(results: pd.DataFrame, has_records: bool):
    """Construct email summary and push items to Monday.com board."""
    record_count = len(results.index) if has_records else 0

    if not has_records:
        output_str = f"""
The PCard Credit Block Review resulted in no new values.

You can view historical results by running the following query:

SELECT *
FROM `{HISTORY_TABLE}`
ORDER BY RUN_TIME_ET DESC
        """
    else:
        output_str = f"""
Please review the {record_count} result(s) from the PCard Credit Block Review at:

https://keybank-org.monday.com/boards/{BOARD_ID}

Additionally, you can review historical results by running the following query:

SELECT *
FROM `{HISTORY_TABLE}`
ORDER BY RUN_TIME_ET DESC
        """

    signature = """
Thank you,

Dexter Jones
Senior Analyst | Commercial Bank Risk
Key Commercial Bank
Office: 518-436-2376
Mobile: 718-790-9213
dexter_jones@keybank.com
"""

    shared_utils.send_email(TO_EMAIL, PIPELINE_NAME, output_str + signature, from_email=FROM_EMAIL)
    print(output_str)

    if has_records:
        for _, row in results.iterrows():
            col_values = {
                'text_mkv5711s': str(row['RUN_TIME_ET']),
                'text_mks0rw5j': str(row['SNAPSHOT_DT']),
                'text_mm5aq5y1': str(row['COMP_NUM']),
                'text_mkv5fwa0': str(row['IPI']),
                'text_mkr0d8k0': str(row['COMPANY_CREDIT_LMT']),
                'text_mks0bv6z': str(row['TOTAL_OUTSTANDING']),
                'text_mkr0h7a4': str(row['DEL_DAYS']),
                'text_mkr0f1g2': str(row['DEL_TOTAL']),
                'text_mkr0h0kf': str(row['DEL_UNDER_30']),
                'text_mm6jt7f1': str(row['DEL_OVER_30']),
            }
            shared_utils.create_monday_item(BOARD_ID, str(row['UNIQUE_ID']), col_values)
        print('Results written to Monday.com')

def main():
    """Main execution controller."""
    try:
        # 1. Freshness Check
        if not check_data_freshness():
            return

        # 2. Extract, MERGE into BigQuery, and Return New Rows
        results = retrieve_and_merge_records()
        has_records = not results.empty
        record_count = len(results.index) if has_records else 0

        # 3. Notify Stakeholders & Push New Items to Monday.com
        send_notifications(results, has_records)

        # 4. Log Success Execution
        shared_utils.log_execution(
            pipeline_name=PIPELINE_NAME,
            cp_number=CP_NUMBER,
            status='SUCCESS',
            records_processed=record_count,
            client=client
        )

    except Exception as e:
        print(f'Pipeline execution error: {e}')
        try:
            shared_utils.log_execution(
                pipeline_name=PIPELINE_NAME,
                cp_number=CP_NUMBER,
                status='FAILED',
                records_processed=0,
                error_msg=str(e),
                client=client
            )
        except Exception as log_err:
            print(f'Failed to record audit log: {log_err}')
        raise e

if __name__ == '__main__':
    main()