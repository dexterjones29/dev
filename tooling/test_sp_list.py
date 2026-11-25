from utilities import sp, utils

utils.load_secrets()
ctx = sp.get_context('AUTOMATION')

TEST_LIST = 'Permission Test = 'Delete Me'

results_list = sp.create_review_list(ctx=ctx, list_title=TEST_LIST)
print(f'List creation successful: {TEST_LIST}')

results_list.delete_object(execute_query())
print(f'List deletion successful: {TEST_LIST}')