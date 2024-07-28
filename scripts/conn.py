import pymongo

def get_db():
    username = 'brlkflee'
    password = 'Rhythmclock'  # Replace with your actual password
    database_name = 'FYP_db'
    client = pymongo.MongoClient(f"mongodb+srv://{username}:{password}@cluster0.3yzdhiq.mongodb.net/{database_name}?retryWrites=true&w=majority")
    db = client[database_name]
    return db

# Fetch records from the records collection
def fetch_records():
    records = db.records.find()
    return list(records)


# Test connection
if __name__ == "__main__":
    db = get_db()
    print("Connection successful")
