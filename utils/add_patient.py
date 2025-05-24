from neo4j import GraphDatabase
from utils.neo4j_helper import get_age, age_bucket, income_bucket, connect_patient_demographics

def add_patient(patient_dict, driver):
    # Create Patient node
    with driver.session() as session:
        session.run(
            """
            MERGE (p:Patient {Id: $Id})
            SET p += $props
            """,
            Id=patient_dict["Id"],
            props=patient_dict
        )
    # Add demographic relationships
    patient = patient_dict.copy()
    patient["AGE"] = get_age(patient["BIRTHDATE"])
    patient["AGE_RANGE"] = age_bucket(patient["AGE"])
    patient["INCOME_RANGE"] = income_bucket(patient["INCOME"])
    patient["ZIPCODE"] = str(patient["ZIP"])
    connect_patient_demographics([patient], driver)

def patient_to_text(patient_dict):
    # Customize as needed
    fields = [
        patient_dict.get("FIRST", ""),
        patient_dict.get("LAST", ""),
        patient_dict.get("GENDER", ""),
        patient_dict.get("BIRTHDATE", ""),
        patient_dict.get("ETHNICITY", ""),
        patient_dict.get("RACE", ""),
        str(patient_dict.get("INCOME", "")),
        str(patient_dict.get("ZIP", ""))
    ]
    return " ".join(fields)

from sentence_transformers import SentenceTransformer

# Load the model only once (do this at the top-level, not inside the function)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # must match the model used for all other patients
model = SentenceTransformer(EMBEDDING_MODEL)

def embed_and_store(patient_id, patient_dict, driver):
    text = patient_to_text(patient_dict)
    embedding = model.encode(text, normalize_embeddings=True).tolist()
    with driver.session() as session:
        session.run(
            "MATCH (p:Patient {Id: $Id}) SET p.embedding = $embedding",
            Id=patient_id,
            embedding=embedding
        )