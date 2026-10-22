import firebase_admin
from firebase_admin import credentials, firestore
import os

creds_path = "/home/james/stacklabs/serviceAccount.json"
if not os.path.exists(creds_path):
    print("No service account found")
    exit(1)

cred = credentials.Certificate(creds_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

collections = db.collections()
for col in collections:
    print("Collection:", col.id)
    docs = col.limit(2).stream()
    for doc in docs:
        print(f"  Doc ID: {doc.id} => {doc.to_dict()}")

