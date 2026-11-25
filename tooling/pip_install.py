"""
VM Python Package Installation
------------------------------
Installs the Python packages required by the Control Automation development and execution environment.
"""
import subprocess
import sys

PACKAGES = [
    'cryptography',
    'db-dtypes',
    'docx',
    'duckdb',
    'google-cloud-bigquery',
    'google-cloud-bigquery-storage',
    'google-cloud-storage',
    'matplotlib',
    'msal',
    'msoffcrypto-tool',
    'numpy',
    'Office365-REST-Python-Client',
    'openpyxl',
    'oracledb',
    'pandas',
    'pretty-html-table',
    'pyarrow',
    'python-dateutil',
    'python-dotenv',
    'requests',
    'XlsxWriter',
    'xlwt'
]

def install_packages():
    """Upgrade pip and install the required Python packages."""
    print('Upgrading pip...')

    subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    print(f'Installing {len(PACKAGES):,} packages...')

    subprocess.run([sys.executable, '-m', 'pip', 'install', *PACKAGES], check=True)
    print('Python package installation complete.')    

def main():
    """Install the Python environment required for Control Automation."""
    install_packages()

if __name__ == '__main__':
    main()