"""
Shared Constants Package
--------
- PROJECT
- DATASET
- CLOUD_CONFIG
- COLUMN_MAP
- CONFIG
- CONFIG_STAGE
- DIAGNOSTIC_LOG
- EXECUTION_LOG
- PROJECT_BOARD

Google Cloud Runtime Configuration

Control Automation Configuration
- EXECUTION_STATUSES
- COMPONENT_STATUSES
- EXECUTION_MODES
- TRIGGER_TYPES
- MBU_NAMES
- MBU_DISPLAY_NAMES
- EXPECTED_MBUS
- EXPECTED_CONTROL_DESIGNS
- CONTROL_FREQUENCY
- GRC_FREQUENCY

Notifications
- FROM_EMAIL
- TEAMS_EMAIL
- EMAIL_SIGNATURE

System Links
- BIGQUERY_CONSOLE
- MONDAY_BOARD
- SHAREPOINT_DEPARTMENTS
"""

PROJECT = 'taw-entpayments-prod-2935'
DATASET = f'{PROJECT}.AW_COMMERCIAL_CP'

CLOUD_CONFIG = f'{DATASET}.CLOUD_CONFIG'
COLUMN_MAP = f'{DATASET}.COLUMN_MAP'
CONFIG = f'{DATASET}.CONFIG'
CONFIG_STAGE = f'{DATASET}.CONFIG_STAGE'
DIAGNOSTIC_LOG = f'{DATASET}.DIAGNOSTIC_LOG'
EXECUTION_LOG = f'{DATASET}.EXECUTION_LOG'
PROJECT_BOARD = f'{DATASET}.PROJECT_BOARD'

EXECUTION_STATUSES = {
    'SUCCESS', 'SUCCESS_ZERO_RESULTS', 'SUCCESS_WITH_WARNING',
    'HALTED_STALE_DATA', 'HALTED_CONFIGURATION', 'HALTED_POPULATION_VARIANCE',
    'FAILED_CONFIGURATION', 'FAILED_FRESHNESS_CHECK',
    'FAILED_POPULATION_QUERY', 'FAILED_REVIEW_QUERY',
    'FAILED_HISTORY_WRITE', 'FAILED_REVIEW_WRITE',
    'FAILED_NOTIFICATION', 'FAILED_UNKNOWN'
}

COMPONENT_STATUSES = {
    'STARTED',
    'SUCCESS',
    'WARNING',
    'FAILED',
    'SKIPPED'
}

EXECUTION_MODES = {'PRODUCTION', 'TEST'}

TRIGGER_TYPES = {'SCHEDULED', 'MANUAL', 'RERUN'}

MBU_NAMES = {
    'COS': 'Commercial Onboarding and Servicing',
    'PDS': 'Payment and Deposit Services',
    'MM': 'Middle Market',
    'PMT': 'Commercial Payments'
}

MBU_DISPLAY_NAMES = {
    'COS': 'COS',
    'PDS': 'PDS',
    'MM': 'Middle Market',
    'PMT': 'Payments'
}

EXPECTED_MBUS = {
    'Commercial Onboarding and Servicing': 'COS',
    'Payment and Deposit Services': 'PDS',
    'Middle Market': 'MM',
    'Commercial Payments': 'PMT'
}

EXPECTED_CONTROL_DESIGNS = {
    'Automated',
    'Hybrid',
    'IT Dependent',
    'Manual'
}

CONTROL_FREQUENCY = {
    'DAILY': 'DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)',
    'WEEKLY': 'DATE_SUB(CURRENT_DATE(), INTERVAL MOD(EXTRACT(DAYOFWEEK FROM CURRENT_DATE()) + 1, 7) DAY)',    
    'MONTHLY': 'LAST_DAY(DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH), MONTH)',
    'QUARTERLY': 'DATE_SUB(DATE_TRUNC(CURRENT_DATE(), QUARTER), INTERVAL 1 DAY)',
    'ANNUALLY': 'DATE_SUB(DATE_TRUNC(CURRENT_DATE(), YEAR), INTERVAL 1 DAY)'
}

GRC_FREQUENCY = ['DAILY', 'WEEKLY', 'MONTHLY', 'QUARTERLY', 'ANNUALLY']

FROM_EMAIL = 'CB_Risk_Control_Automation@keybank.com'

TEAMS_EMAIL = '2ef5d538.kbna.onmicrosoft.com@amer.teams.ms'

EMAIL_SIGNATURE = """
Thank you,

Dexter Jones
1LOD Technology & AI Risk
Key Commercial Bank
CB_Risk_Control_Automation@keybank.com
"""

BIGQUERY_CONSOLE = 'https://console.cloud.google.com/bigquery?project=taw-entpayments-prod-2935&supportedpurview=project&ws=!1m0pli=1'

MONDAY_BOARD = 'https://keybank-org.monday.com/boards'

SHAREPOINT_DEPARTMENTS = {
    '1LOD': {
        'site_name': 'PaymentsMonitoringandPortfolioManagement',
        'pfx_blob': 'Certificates/SPO-PaymentsMonitoringandPortfolioManagement-Reporting.pfx',
        'client_id_env': 'CLIENT_ID_1LOD',
        'pfx_pass_env': 'PFX_PASSWORD_1LOD'
    },
    'AUTOMATION': {
        'site_name': 'CBControlAuto',
        'pfx_blob': 'Certificates/SPO-CBControlAuto-PythonIntegration.pfx',
        'client_id_env': 'CLIENT_ID_AUTOMATION',
        'pfx_pass_env': 'PFX_PASSWORD_AUTOMATION'
    },
    'CPC': {
        'site_name': 'CommercialCardProduct',
        'pfx_blob': 'Certificates/SPO-CommercialCardProduct-DataTransfer.pfx',
        'client_id_env': 'CLIENT_ID_CPC',
        'pfx_pass_env': 'PFX_PASSWORD_CPC'
    },
    'CTF': {
        'site_name': 'CoreTreasuryFraudProductTeam',
        'pfx_blob': 'Certificates/SPO-CoreTreasuryFraudProductTeam-Python.pfx',
        'client_id_env': 'CLIENT_ID_CTF',
        'pfx_pass_env': 'PFX_PASSWORD_CTF'
    },
    'DLR': {
        'site_name': 'DealerFin-AutomationIntegration',
        'pfx_blob': 'Certificates/SPO-DealerFin-AutomationIntegration.pfx',
        'client_id_env': 'CLIENT_ID_DLR',
        'pfx_pass_env': 'PFX_PASSWORD_DLR'
    },
    'KMS': {
        'site_name': 'KMS_PTFLO_MGMT_GRC_CP',
        'pfx_blob': 'Certificates/SPO-KMS_PTFLO_MGMT_GRC_CP-PythonAutomation.pfx',
        'client_id_env': 'CLIENT_ID_KMS',
        'pfx_pass_env': 'PFX_PASSWORD_KMS'
    },
    'NYS_COURIER': {
        'site_name': 'NYSCourier',
        'pfx_blob': 'Certificates/SPO-NYSCourier-FileTransfer.pfx',
        'client_id_env': 'CLIENT_ID_NYS_COURIER',
        'pfx_pass_env': 'PFX_PASSWORD_NYS_COURIER'
    },
    'PMT': {
        'site_name': 'EnterprisePaymentsProcedureRepository',
        'pfx_blob': 'Certificates/SPO-EnterprisePaymentsProcedureRepository-Reporting.pfx',
        'client_id_env': 'CLIENT_ID_PMT',
        'pfx_pass_env': 'PFX_PASSWORD_PMT'
    },
    'PPC': {
        'site_name': 'ECPAPrepaidProduct',
        'pfx_blob': 'Certificates/SPO-ECPAPrepaidProduct-PPD.pfx',
        'client_id_env': 'CLIENT_ID_PPC',
        'pfx_pass_env': 'PFX_PASSWORD_PPC'
    }
}
