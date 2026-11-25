from utilities import utils

result = utils.send_email(
    to_email='dexterjones29@gmail.com',
    subject='Local VS Code SMTP Test',
    body=(
        'This is a local Python SMTP connectivity test.\n\n'
        'Execution environment: VS Code / Windows / Python 3.15'
    )
)

print(result)