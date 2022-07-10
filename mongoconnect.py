import os
from dotenv import load_dotenv

def get_database():
    load_dotenv()

    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    cluster = os.getenv("CLUSTER")
    dbname = os.getenv("DBNAME")

    CONNECTION_STRING = f"mongodb+srv://{username}:{password}@{cluster}.mongodb.net"

    from pymongo import MongoClient
    client = MongoClient(CONNECTION_STRING)

    return client[dbname]
    
if __name__ == "__main__":    
    dbname = get_database()