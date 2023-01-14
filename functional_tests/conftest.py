import os.path

import pytest

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items):
   #Make sure that test copy is our first test, and test_delete is the last one.
   for idx, item in enumerate(items):
       if item.name == 'test_copy':
           break

   if idx != 0:
       items[0], items[idx] = items[idx], items[0]

   for idx, item in enumerate(items):
       if item.name == 'test_delete':
           break

   if idx != len(items) - 1:
       items[-1], items[idx] = items[idx], items[-1]
