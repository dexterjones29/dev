from google.cloud import bigquery

client = bigquery.Client(project='project-8e6b567c-c982-46ae-a41')

query = """ SELECT CURRENT_TIMESTAMP() """
result = client.query(query).result()

for row in result:
    print(row.test_timestamp)