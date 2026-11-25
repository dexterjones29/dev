import requests

from utilities import monday, utils

utils.load_secrets()

# print('MONDAY_API_KEY loaded:', bool(os.getenv('MONDAY_API_KEY')))

BOARD_ID = 18435447915 # stat sheet

response = requests.post(
    url=monday.API_URL,
    json={
        'query': '''
        query {
          me {
            id
            name
            email
          }
        }
        '''
    },
    headers=monday.get_headers(),
    proxies=monday.PROXIES
)

response.raise_for_status()
data = response.json()

if data.get('errors'):
    raise RuntimeError(f'Monday API erro: {data['errors']}')

print(data['data']['me'])

# results = monday.get_board_items(BOARD_ID)
# print(results.shape)
# print(results.head())

# item_id = '13491113523'

# update_id = monday.creat_update(item_id=item_id, update_text='Discovery started')
# print(f'Created update: {update_id}')