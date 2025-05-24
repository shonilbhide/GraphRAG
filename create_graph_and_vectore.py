# create_graph_and_vectors.py

import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from sentence_transformers import SentenceTransformer
from utils.neo4j_helper import *
import time

start = time.time()
# --- CONFIG ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Free, local, 384 dims
EMBEDDING_DIM = 384
BATCH_SIZE = 128

# --- LOAD ENV ---
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASS = os.getenv("NEO4J_PASS")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

try:
    # --- LOAD DATA ---
    patients = pd.read_csv("./data/patients.csv")
    encounters = pd.read_csv("./data/encounters.csv")
    providers = pd.read_csv("./data/providers.csv")
    payers = pd.read_csv("./data/payers.csv")
    claims = pd.read_csv("./data/claims.csv")
    medications = pd.read_csv("./data/medications.csv")
    print("Data loaded successfully.")

    # --- Clean up IDs ---
    patients['Id'] = patients['Id'].astype(str)
    encounters['Id'] = encounters['Id'].astype(str)
    providers['Id'] = providers['Id'].astype(str)
    payers['Id'] = payers['Id'].astype(str)
    claims['Id'] = claims['Id'].astype(str)
    medications['CODE'] = medications['CODE'].astype(str)
    print("IDs cleaned successfully.")

    # --- Create Indexes ---
    with driver.session() as session:
        session.run("CREATE INDEX IF NOT EXISTS FOR (p:Patient) ON (p.Id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (e:Encounter) ON (e.Id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (pr:Provider) ON (pr.Id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (py:Payer) ON (py.Id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (c:Claim) ON (c.Id)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (m:Medication) ON (m.CODE)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (z:Zipcode) ON (z.zipcode)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (a:Age_Range) ON (a.range)")
        session.run("CREATE INDEX IF NOT EXISTS FOR (i:Income_Range) ON (i.range)")

    # --- Create Nodes ---
    create_nodes("Patient", patients, "Id", driver)
    create_nodes("Provider", providers, "Id", driver)
    create_nodes("Payer", payers, "Id", driver)
    create_nodes("Encounter", encounters, "Id", driver)
    create_nodes("Claim", claims, "Id", driver)
    create_nodes("Medication", medications, "CODE", driver)
    print("Nodes created successfully.")

    # --- Demographics ---
    patients['AGE'] = patients['BIRTHDATE'].apply(get_age)
    patients['AGE_RANGE'] = patients['AGE'].apply(age_bucket)
    patients['INCOME_RANGE'] = patients['INCOME'].apply(income_bucket)
    patients['ZIPCODE'] = patients['ZIP'].astype(str)

    age_ranges = patients['AGE_RANGE'].unique()
    income_ranges = patients['INCOME_RANGE'].unique()
    zipcodes = patients['ZIPCODE'].unique()

    with driver.session() as session:
        for age in age_ranges:
            session.run("MERGE (:Age_Range {range: $age})", age=age)
        for inc in income_ranges:
            session.run("MERGE (:Income_Range {range: $inc})", inc=inc)
        for zc in zipcodes:
            session.run("MERGE (:Zipcode {zipcode: $zc})", zc=zc)

    for batch in batcher(patients.to_dict("records")):
        connect_patient_demographics(batch, driver)
    print("Demographics connected successfully.")

    # --- Relationships ---
    rel_query = """
    UNWIND $batch AS row
    MATCH (p:Patient {Id: row.PATIENT})
    MATCH (e:Encounter {Id: row.Id})
    MERGE (p)-[:HAS_ENCOUNTER]->(e)
    """
    create_relationships(encounters, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (e:Encounter {Id: row.Id})
    MATCH (pr:Provider {Id: row.PROVIDER})
    MERGE (e)-[:ATTENDED_BY]->(pr)
    """
    create_relationships(encounters, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (e:Encounter {Id: row.Id})
    MATCH (py:Payer {Id: row.PAYER})
    MERGE (e)-[:BILLED_BY]->(py)
    """
    create_relationships(encounters, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (p:Patient {Id: row.PATIENTID})
    MATCH (c:Claim {Id: row.Id})
    MERGE (p)-[:HAS_CLAIM]->(c)
    """
    create_relationships(claims, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (c:Claim {Id: row.Id})
    MATCH (pr:Provider {Id: row.PROVIDERID})
    MERGE (c)-[:PROVIDED_BY]->(pr)
    """
    create_relationships(claims, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (c:Claim {Id: row.Id})
    MATCH (py:Payer {Id: row.PRIMARYPATIENTINSURANCEID})
    MERGE (c)-[:PAID_BY]->(py)
    """
    create_relationships(claims, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (e:Encounter {Id: row.ENCOUNTER})
    MATCH (m:Medication {CODE: row.CODE})
    MERGE (e)-[:HAS_MEDICATION]->(m)
    """
    create_relationships(medications, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (p:Patient {Id: row.PATIENT})
    MATCH (m:Medication {CODE: row.CODE})
    MERGE (p)-[:HAS_MEDICATION]->(m)
    """
    create_relationships(medications, rel_query, driver)

    rel_query = """
    UNWIND $batch AS row
    MATCH (m:Medication {CODE: row.CODE})
    MATCH (py:Payer {Id: row.PAYER})
    MERGE (m)-[:COVERED_BY]->(py)
    """
    create_relationships(medications, rel_query, driver)
    print("Relationships created successfully.")
    # --- Embedding Generation and Storage ---
    def patient_to_text(patient_dict):
        fields = [
            str(patient_dict.get("FIRST", "")),
            str(patient_dict.get("LAST", "")),
            str(patient_dict.get("GENDER", "")),
            str(patient_dict.get("BIRTHDATE", "")),
            str(patient_dict.get("ETHNICITY", "")),
            str(patient_dict.get("RACE", "")),
            str(patient_dict.get("INCOME", "")),
            str(patient_dict.get("ZIP", ""))
        ]
        return " ".join(fields)

    model = SentenceTransformer(EMBEDDING_MODEL)

    print("Generating and storing patient embeddings...")
    for i in range(0, len(patients), BATCH_SIZE):
        batch = patients.iloc[i:i+BATCH_SIZE]
        texts = [patient_to_text(row) for _, row in batch.iterrows()]
        embeddings = model.encode(texts, normalize_embeddings=True)
        for idx, emb in zip(batch.index, embeddings):
            patient_id = patients.loc[idx, "Id"]
            with driver.session() as session:
                session.run(
                    "MATCH (p:Patient {Id: $Id}) SET p.embedding = $embedding",
                    Id=patient_id,
                    embedding=emb.tolist()
                )

    print("All patient embeddings created and stored.")

    # --- Create Vector Index ---
    with driver.session() as session:
        session.execute_write(
            create_vector_index,
            index_name="patient_embedding_index",
            node_label="Patient",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )

        session.execute_write(
            create_vector_index,
            index_name="provider_embedding_index",
            node_label="Provider",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )
        session.execute_write(
            create_vector_index,
            index_name="payer_embedding_index",
            node_label="Payer",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )
        session.execute_write(
            create_vector_index,
            index_name="claim_embedding_index",
            node_label="Claim",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )
        session.execute_write(
            create_vector_index,
            index_name="encounter_embedding_index",
            node_label="Encounter",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )
        session.execute_write(
            create_vector_index,
            index_name="medication_embedding_index",
            node_label="Medication",
            embedding_property="embedding",
            embedding_dimension=EMBEDDING_DIM,
            similarity_function="cosine"
        )


    print("Vector index created.")

    driver.close()
    end = time.time()
    print(f"Total time taken: {end - start} seconds")
except Exception as e:
    print(f"Error: {e}")
    driver.close()
    exit(1)
