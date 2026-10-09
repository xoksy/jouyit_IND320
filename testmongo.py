import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

password = os.getenv("MONGODB_PASSWORD")

uri = f"mongodb+srv://matthieujouyit_db_user:{password}@cluster0.l9mrgyg.mongodb.net/?appName=Cluster0"

client = MongoClient(uri)

try:
    client.admin.command("ping")
    print("Connected successfully")
    client.close()

except Exception as e:
    raise Exception(
        "The following error occurred: ", e
    )