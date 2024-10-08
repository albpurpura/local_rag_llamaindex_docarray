import shutil
import os
import logging
from typing import Dict
from fastapi import HTTPException
import shutil
from dotenv import load_dotenv
import os
from collection import Collection
import qdrant_client
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

COLLECTIONS_DIR = os.getenv("COLLECTIONS_DIR", "collections")
QDRANT_HOSTNAME = os.getenv("QDRANT_HOSTNAME", "qdrant")


class CollectionManager:
    def __init__(self):
        self.collections: Dict[str, Collection] = {}
        retries = 5
        while retries:
            try:
                self.client = qdrant_client.QdrantClient(host=QDRANT_HOSTNAME)
                self.load_existing_collections()
                break
            except Exception as e:
                retries -= 1
                logger.error(
                    f"Failed to connect to Qdrant. Retries left: {retries}. Error: {e}"
                )
                time.sleep(5)

    def load_existing_collections(
        self,
    ):
        existing_coll_names = [
            item.name for item in self.client.get_collections().collections
        ]
        for name in existing_coll_names:
            self.collections[name] = Collection(self.client, name)

    def create_collection(self, name: str) -> Dict:
        if name in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{name}' already exists"
            )
        self.collections[name] = Collection(self.client, name)
        return {"message": f"Collection '{name}' created successfully"}

    def delete_collection(self, name: str) -> Dict:
        if name not in self.collections:
            raise HTTPException(
                status_code=404, detail=f"Collection '{name}' not found"
            )
        del self.collections[name]
        shutil.rmtree(f"{COLLECTIONS_DIR}/{name}", ignore_errors=True)

        return {"message": f"Collection '{name}' deleted successfully"}

    def rename_collection(self, old_name: str, new_name: str) -> Dict:
        if old_name not in self.collections:
            raise HTTPException(
                status_code=404, detail=f"Collection '{old_name}' not found"
            )
        if new_name in self.collections:
            raise HTTPException(
                status_code=400, detail=f"Collection '{new_name}' already exists"
            )
        self.collections[new_name] = self.collections.pop(old_name)
        self.collections[new_name].name = new_name

        if os.path.exists(f"{COLLECTIONS_DIR}/{new_name}"):
            shutil.rmtree(f"{COLLECTIONS_DIR}/{new_name}")

        os.rename(f"{COLLECTIONS_DIR}/{old_name}", f"{COLLECTIONS_DIR}/{new_name}")
        return {
            "message": f"Collection renamed from '{old_name}' to '{new_name}' successfully"
        }

    def get_collection(self, name: str) -> Collection:
        if name not in self.collections:
            raise HTTPException(
                status_code=404, detail=f"Collection '{name}' not found"
            )
        return self.collections[name]
