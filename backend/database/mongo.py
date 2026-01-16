from pymongo import MongoClient
from config import MONGO_URI, DATABASE_NAME

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

pacientes = db["pacientes"]
historico = db["historico"]
counters = db["counters"]
users = db["users"]