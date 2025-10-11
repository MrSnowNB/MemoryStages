import os
import tempfile
import sys
sys.path.insert(0, 'src')
os.environ['DB_PATH'] = tempfile.mkstemp(suffix='.db')[1]

from src.core.dao import get_key, set_key, delete_key, list_keys, get_kv_count

# Add some keys
set_key('count_test_1', 'value1', 'test', 'lowercase')
set_key('count_test_2', 'value2', 'test', 'lowercase')

print('After setting 2 keys:')
keys = list_keys()
print(f'List keys count: {len(keys)}')
for k in keys:
    print(f'Key: {k.key}, Value: "{k.value}"')

# Delete one (tombstone)
delete_key('count_test_1')

print('\nAfter deleting count_test_1:')
keys = list_keys()
print(f'List keys count: {len(keys)}')
for k in keys:
    print(f'Key: {k.key}, Value: "{k.value}"')

count = get_kv_count()
print(f'\nKV Count result: {count}')

# Let's also check what's actually in the database
from src.core.db import get_db

with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM kv")
    rows = cursor.fetchall()
    print("\nActual DB contents:")
    for row in rows:
        print(f"Key: {row[0]}, Value: '{row[1]}'")
