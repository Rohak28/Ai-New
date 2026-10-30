import os
import json
from pymongo import MongoClient
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

# Setup MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=2000) # 2-second timeout
db = mongo_client["neuronest_ivn"]
reports_collection = db["reports"]

# Fallback Local JSON DB
LOCAL_DB_FILE = "local_db.json"
_fallback_mode = None

def is_fallback():
    """Check if MongoDB is available, otherwise use local JSON file."""
    global _fallback_mode
    if _fallback_mode is None:
        try:
            mongo_client.server_info() # Forces connection check
            _fallback_mode = False
            print("[Database] MongoDB connection successful.")
        except Exception as e:
            _fallback_mode = True
            print(f"[Database] MongoDB unavailable. Falling back to {LOCAL_DB_FILE}.")
    return _fallback_mode

def get_local_db():
    if os.path.exists(LOCAL_DB_FILE):
        with open(LOCAL_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_local_db(data):
    with open(LOCAL_DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def insert_report(report_data):
    """Inserts a full JSON parsed report into MongoDB or local fallback."""
    report_id = report_data.get("metadata", {}).get("report_no", "unknown_id")
    
    if is_fallback():
        db_data = get_local_db()
        db_data[report_id] = report_data
        save_local_db(db_data)
        print(f"Report {report_id} successfully saved to local fallback DB.")
    else:
        reports_collection.update_one(
            {"metadata.report_no": report_id},
            {"$set": report_data},
            upsert=True
        )
        print(f"Report {report_id} successfully saved to MongoDB.")
    
    return report_id

def get_report(report_id):
    """Fetch a full report by its report number."""
    if is_fallback():
        return get_local_db().get(report_id)
    return reports_collection.find_one({"metadata.report_no": report_id}, {"_id": 0})

def get_all_reports():
    """
    Fetch a lightweight list of all reports for the dashboard selector.
    Returns only metadata + analysis_summary.
    """
    if is_fallback():
        db_data = get_local_db()
        # Sort by keys descending (newest first approximation)
        reports = []
        for rid in reversed(list(db_data.keys())):
            data = db_data[rid]
            reports.append({
                "metadata": data.get("metadata"),
                "analysis_summary": data.get("analysis_summary")
            })
        return reports

    cursor = reports_collection.find(
        {},
        {
            "_id": 0,
            "metadata": 1,
            "analysis_summary": 1,
        }
    ).sort("_id", -1)  # newest first
    return list(cursor)

# Setup Milvus
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")

def setup_milvus():
    print(f"Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    try:
        connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
        collection_name = "ivn_knowledge_base"
        
        # Define Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text_content", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384) # Assuming a 384 dim model like all-MiniLM
        ]
        schema = CollectionSchema(fields, "IVN Automotive Standards & DBC Knowledge Base")
        
        if utility.has_collection(collection_name):
            collection = Collection(collection_name)
            print(f"Milvus Collection '{collection_name}' already exists.")
        else:
            collection = Collection(name=collection_name, schema=schema)
            # Create an index
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            print(f"Created Milvus Collection '{collection_name}' with vector index.")
        
        return collection
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")
        return None

def ingest_iso_standards():
    """Ingest seed automotive standards into Milvus for RAG."""
    collection = setup_milvus()
    if not collection:
        return
    
    # Mocking standard rules
    knowledge_base_chunks = [
        "ISO 11898-2 CAN Physical Layer: Rise time maximum is 190ns. Fall time maximum is 120ns.",
        "Failure Mode: If Rise Time exceeds 190ns but Fall time passes, it indicates excessive bus capacitance or long stub lengths.",
        "Bit Rate Tolerance: Bit time should be tightly bounded around nominal. A bit time of 0.00 ns indicates a catastrophic bus-off state, missing termination resistor, or offline node.",
        "DBC Rules: Unmapped messages like C00000B or C00290B marked as 'Not in DBC' indicate rogue nodes on the EV_CAN bus causing arbitration delays.",
        "Jitter: Max jitter should not exceed 10% of nominal periodicity. Load % above 70% can cause message starvation for low priority CAN IDs."
    ]
    
    # In a real scenario, use an embedding model like sentence_transformers
    # Here we mock 384-dimensional embeddings
    import random
    embeddings = [[random.random() for _ in range(384)] for _ in knowledge_base_chunks]
    
    # Check if we already inserted them to avoid duplicates (naive check for this sandbox)
    if collection.num_entities < len(knowledge_base_chunks):
        collection.insert([
            knowledge_base_chunks,
            embeddings
        ])
        collection.flush()
        print(f"Successfully ingested {len(knowledge_base_chunks)} ISO/DBC standards into Milvus.")
    else:
        print("ISO standards already exist in Milvus.")

if __name__ == "__main__":
    # Initialize the Vector DB with seed rules
    ingest_iso_standards()
