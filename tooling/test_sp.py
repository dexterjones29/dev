from utilities import sp, utils

utils.load_secrets()

print('Creating SharePoint context...')
ctx = sp.get_context('AUTOMATION')

print('Reading SharePoint site...')
web = ctx.web.get().execute_query()

print('SharePoint authentication successful.')
print(f'Site title: {web.properties.get('Title')}')
print(f'Site URL: {web.properties.get('Url')}')

FOLDER_LOCATION = '/sites/CBControlAuto/Shared Documents/Files'
content = b'Local VS Code SharePoint write test.'
file_url = sp.upload_files(ctx, FOLDER_LOCATION, 'sp_local_test.txt', content)
print(f'SharePoint Site Page creation successful.')
print(f'Page URL: {page.absolute_url}')