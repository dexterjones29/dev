"""
Monday.com Utilities Package
----------------------------
- get_headers()
- get_board_name()
- get_column_map()
- get_groups()
- get_items()
- get_item_id()
- create_column_values()
- create_item()
- create_update()
- update_column()
- publish_items()
"""

import json
import os
import pandas as pd
import requests

API_URL = 'https://api.monday.com/v2'
API_VERSION = '2026-10'
PROXIES = {'https': 'vzproxy.keybank.com'}

def get_headers():
    """Return authenticated Monday.com API headers."""
    api_key = os.getenv('MONDAY_API_KEY')

    if not api_key:
        raise ValueError('MONDAY_API_KEY not found in environment.')

    return {'Authorization': api_key, 'API-Version': API_VERSION}

def get_board_name(board_id):
    """Return the Monday.com board name."""
    headers = get_headers()
    query = """
    query ($board_id: ID!) {
      boards(ids: [$board_id]) {
        name
      }
    }
    """
    variables = {'board_id': str(board_id)}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    boards = response_data.get('data', {}).get('boards', [])

    if not boards:
        raise ValueError(f'Monday.com Board ID not found: {board_id}')

    return boards[0]['name']

def get_column_map(board_id):
    """Return Monday column ID to column title mapping."""
    headers = get_headers()
    query = f"""{{boards(ids: {board_id}) {{ columns {{ id title}} }} }}"""
    data = {'query': query}
    response = requests.post(url=API_URL, json=data, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    try:
        columns = response_data['data']['boards'][0]['columns']
        return {col['id']: col['title'] for col in columns}

    except (KeyError, IndexError):
        return {}

def get_groups(board_id):
    """Return Monday group title to group ID mapping."""
    headers = get_headers()

    query = """
    query ($board_id: ID!) {
      boards(ids: [$board_id]) {
        groups {
          id
          title
        }
      }
    }
    """

    variables = {'board_id': str(board_id)}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    groups = response_data.get('data', {}).get('boards', [{}])[0].get('groups', [])

    return {group['title']: group['id'] for group in groups}

def get_items(board_id):
    """Retrieve all items and column values from a Monday.com board."""
    headers = get_headers()
    column_map = get_column_map(board_id)

    query = """
    query ($board_id: ID!){
      boards(ids: [$board_id]) {
        items_page(limit: 500) {
          cursor
          items {
            id
            name
            column_values {
              id
              text
            }
          }
        }
      }
    }
    """

    variables = {'board_id': str(board_id)}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    items_page = response_data['data']['boards'][0]['items_page']
    items = items_page['items']
    cursor = items_page['cursor']

    while cursor:
        query = """
        query ($cursor: String!) {
          next_items_page(limit: 500, cursor: $cursor) {
            cursor
            items {
              id
              name
              column_values {
                id
                text
              }
            }
          }
        }
        """
        variables = {'cursor': cursor}
        response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
        response.raise_for_status()
        response_data = response.json()

        if response_data.get('errors'):
            raise RuntimeError(f'Monday API error: {response_data['errors']}')

        items_page = response_data['data']['next_items_page']
        items.extend(items_page['items'])
        cursor = items_page['cursor']

    records = []

    for item in items:
        record = {'ITEM_ID': item['id'], 'PROJECT': item['name']}

        for column in item['column_values']:
            column_name = column_map.get(column['id'])

            if column_name:
                record[column_name] = column['text']

        records.append(record)

    results = pd.DataFrame(records)

    print(f'Retrieved {len(results):,} item(s) from Monday.com Board ID: {board_id}')

    return results

def get_item_id(board_id, item_name=None, column_name=None, column_value=None):
    """Return the unique Monday item ID matching the requested criteria."""
    results = get_items(board_id)

    if item_name is not None:
        matched = results.loc[results['PROJECT'].astype(str) == str(item_name)]

    elif column_name is not None and column_value is not None:
        if column_name not in results.columns:
            raise ValueError(f'Monday.com column not found: {column_name}')

        matched = results.loc[results[column_name].astype(str) == str(column_value)]

    else:
        raise ValueError('Provide either item_name or column_name and column_value.')

    if matched.empty:
        raise ValueError('No matching Monday.com item found.')

    if len(matched) > 1:
        raise ValueError(f'{len(matched):,} matching Monday.com items found.')

    return str(matched.iloc[0]['ITEM_ID'])

def create_column_values(row, column_map):
    """Create Monday column values automatically from dataframe column names matching board column title."""
    return {
        col_id: row[col_name].strftime('%Y-%m-%d %H:%M:%S') if col_name == 'RUN_TIME_UTC' else str(row[col_name])
        for col_id, col_name in column_map.items() if col_name in row.index
    }

def create_item(board_id, item_name, column_values, group_id=None):
    """Create a Monday.com item and return its item ID."""
    headers = get_headers()
    query = """mutation ($board_id: ID! $group_id: String $item_name: String! $column_values: JSON!)
    {create_item(board_id: $board_id group_id: $group_id item_name: $item_name column_values: $column_values) {id}}"""
    variables = {'board_id': str(board_id), 'group_id': group_id, 'item_name': item_name, 'column_values': json.dumps(column_values)}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    return response_data['data']['create_item']['id']

def create_update(item_id, update_text):
    """Add a text update to an existing Monday.com item."""
    headers = get_headers()
    query = """mutation ($item_id: ID! $body: String! {create_update(item_id: $item_id body: $body) {id}}"""
    variables = {'item_id': str(item_id), 'body': update_text}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    return response_data['data']['create_update']['id']

def update_column(board_id, item_id, column_id, value):
    """ Update a column value on an existing Monday.com item."""
    headers = get_headers()
    query = """mutation ($board_id: ID! $item_id: ID! $column_id: String! $value: JSON!)
    {change_column_value(board_id: $board_id item_id: $item_id column_id: $column_id value: $value) {id}}"""
    variables = {'board_id': str(board_id), 'item_id': str(item_id), 'column_id': column_id, 'value': json.dumps(value)}
    response = requests.post(url=API_URL, json={'query': query, 'variables': variables}, headers=headers, proxies=PROXIES)
    response.raise_for_status()
    response_data = response.json()

    if response_data.get('errors'):
        raise RuntimeError(f'Monday API error: {response_data['errors']}')

    return response_data['data']['change_column_value']['id']

def publish_items(results, board_id):
    """Publish dataframe rows to Monday.com when a board is configured."""
    if board_id is None:
        print('No Monday.com board configured')
        return

    if results.empty:
        print('No new records sent to Monday.com')
        return

    column_map = get_column_map(board_id)
    for _, row in results.iterrows():
        column_values = create_column_values(row, column_map)
        create_item(board_id=board_id, item_name=str(row['UNIQUE_ID']), column_values=column_values)
    print(f'Sent {len(results):,} record(s) to Monday.com Board ID: {board_id}')