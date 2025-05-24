from neo4j import GraphDatabase
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import os
from utils.neo4j_helper import *

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASS = os.getenv("NEO4J_PASS")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# Load CSVs
try:
    patients = pd.read_csv("./data/patients.csv")
    encounters = pd.read_csv("./data/encounters.csv")
    providers = pd.read_csv("./data/providers.csv")
    payers = pd.read_csv("./data/payers.csv")
    claims = pd.read_csv("./data/claims.csv")
    medications = pd.read_csv("./data/medications.csv")
except Exception as e:
    print(f"Error loading CSV files: {e}")
    exit(1)

try: 
    # Clean up IDs (if any NaN)
    patients['Id'] = patients['Id'].astype(str)
    encounters['Id'] = encounters['Id'].astype(str)
    providers['Id'] = providers['Id'].astype(str)
    payers['Id'] = payers['Id'].astype(str)
    claims['Id'] = claims['Id'].astype(str)
    medications['CODE'] = medications['CODE'].astype(str)
except Exception as e:  
    print(f"Error converting IDs to string: {e}")
    exit(1)

print("Data loaded successfully.")
# --- Indexes for performance ---
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



patients['AGE'] = patients['BIRTHDATE'].apply(get_age)
patients['AGE_RANGE'] = patients['AGE'].apply(age_bucket)
patients['INCOME_RANGE'] = patients['INCOME'].apply(income_bucket)
patients['ZIPCODE'] = patients['ZIP'].astype(str)

# Create Age_Range, Income_Range, Zipcode nodes
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


# 1. PATIENT -[:HAS_ENCOUNTER]-> ENCOUNTER
rel_query = """
UNWIND $batch AS row
MATCH (p:Patient {Id: row.PATIENT})
MATCH (e:Encounter {Id: row.Id})
MERGE (p)-[:HAS_ENCOUNTER]->(e)
"""
create_relationships(encounters, rel_query, driver)

# 2. ENCOUNTER -[:ATTENDED_BY]-> PROVIDER
rel_query = """
UNWIND $batch AS row
MATCH (e:Encounter {Id: row.Id})
MATCH (pr:Provider {Id: row.PROVIDER})
MERGE (e)-[:ATTENDED_BY]->(pr)
"""
create_relationships(encounters, rel_query, driver)

# 3. ENCOUNTER -[:BILLED_BY]-> PAYER
rel_query = """
UNWIND $batch AS row
MATCH (e:Encounter {Id: row.Id})
MATCH (py:Payer {Id: row.PAYER})
MERGE (e)-[:BILLED_BY]->(py)
"""
create_relationships(encounters, rel_query, driver)

# 4. PATIENT -[:HAS_CLAIM]-> CLAIM
rel_query = """
UNWIND $batch AS row
MATCH (p:Patient {Id: row.PATIENTID})
MATCH (c:Claim {Id: row.Id})
MERGE (p)-[:HAS_CLAIM]->(c)
"""
create_relationships(claims, rel_query, driver)

# 5. CLAIM -[:PROVIDED_BY]-> PROVIDER
rel_query = """
UNWIND $batch AS row
MATCH (c:Claim {Id: row.Id})
MATCH (pr:Provider {Id: row.PROVIDERID})
MERGE (c)-[:PROVIDED_BY]->(pr)
"""
create_relationships(claims, rel_query, driver)

# 6. CLAIM -[:PAID_BY]-> PAYER
rel_query = """
UNWIND $batch AS row
MATCH (c:Claim {Id: row.Id})
MATCH (py:Payer {Id: row.PRIMARYPATIENTINSURANCEID})
MERGE (c)-[:PAID_BY]->(py)
"""
create_relationships(claims, rel_query, driver)

# 7. ENCOUNTER -[:HAS_MEDICATION]-> MEDICATION
rel_query = """
UNWIND $batch AS row
MATCH (e:Encounter {Id: row.ENCOUNTER})
MATCH (m:Medication {CODE: row.CODE})
MERGE (e)-[:HAS_MEDICATION]->(m)
"""
create_relationships(medications, rel_query, driver)

# 8. PATIENT -[:HAS_MEDICATION]-> MEDICATION
rel_query = """
UNWIND $batch AS row
MATCH (p:Patient {Id: row.PATIENT})
MATCH (m:Medication {CODE: row.CODE})
MERGE (p)-[:HAS_MEDICATION]->(m)
"""
create_relationships(medications, rel_query, driver)

# 9. MEDICATION -[:COVERED_BY]-> PAYER
rel_query = """
UNWIND $batch AS row
MATCH (m:Medication {CODE: row.CODE})
MATCH (py:Payer {Id: row.PAYER})
MERGE (m)-[:COVERED_BY]->(py)
"""
create_relationships(medications, rel_query, driver)

driver.close()
