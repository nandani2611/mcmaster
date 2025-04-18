import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

class MongoDBClient:
    def __init__(self, db_name, collection_name):
        self.client = MongoClient(os.getenv('MONGO_URI'))
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    def insert_document(self, document):
        """Insert a single document into the collection."""
        return self.collection.insert_one(document)

    def insert_documents(self, documents):
        """Insert multiple documents into the collection."""
        return self.collection.insert_many(documents)

    def find_document(self, query):
        """Find a single document that matches the query."""
        return self.collection.find_one(query)

    def find_documents(self, query):
        """Find all documents that match the query."""
        return self.collection.find(query)

    def update_document(self, query, new_values):
        """Update a single document that matches the query."""
        return self.collection.update_one(query, new_values)

    def update_documents(self, query, new_values):
        """Update all documents that match the query."""
        return self.collection.update_many(query, new_values)

    def delete_document(self, query):
        """Delete a single document that matches the query."""
        return self.collection.delete_one(query)

    def delete_documents(self, query):
        """Delete all documents that match the query."""
        return self.collection.delete_many(query)