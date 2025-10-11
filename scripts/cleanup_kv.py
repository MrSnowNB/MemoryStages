import asyncio
import re
from src.core.dao import DAO

INVALID_KEYS = {"", "what"}
DUPLICATES = {"displayname"}  # duplicated variant of displayName
PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")

async def main():
    dao = DAO()
    items = await dao.list_keys()
    for i in items:
        if i.key in INVALID_KEYS or i.key in DUPLICATES or not PATTERN.match(i.key):
            print("Deleting:", i.key)
            await dao.delete_key(i.key)

if __name__ == "__main__":
    asyncio.run(main())
