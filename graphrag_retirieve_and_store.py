from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
from utils.neo4j_helper import *
from utils.add_patient import *

load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASS = os.getenv("NEO4J_PASS")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

def get_embedding(patient_id):
    with driver.session() as session:
        result = session.run(
            "MATCH (p:Patient {Id: $Id}) RETURN p.embedding AS embedding",
            Id=patient_id
        )
        record = result.single()
        return record["embedding"] if record else None

def find_similar_patients(embedding, top_k=5):
    with driver.session() as session:
        result = session.run(
            """
            CALL db.index.vector.queryNodes('patient_embedding_index', $top_k, $embedding)
            YIELD node, score
            RETURN node.Id AS patient_id, score
            ORDER BY score DESC
            """,
            top_k=top_k,
            embedding=embedding
        )
        return [(r["patient_id"], r["score"]) for r in result]

def check_eligibility(patient_ids):
    cypher_patient_ids = "[" + ", ".join(f'"{pid}"' for pid in patient_ids) + "]"
    query = f"""
    UNWIND {cypher_patient_ids} AS pid
    MATCH (p:Patient {{Id: pid}})-[:HAS_CLAIM]->(c:Claim)-[:PAID_BY]->(py:Payer)
    WHERE py.NAME IN ['Medicare', 'Medicaid']
    RETURN p.Id AS patient_id, collect(DISTINCT py.NAME) AS eligible_payers
    """
    with driver.session() as session:
        result = session.run(
            query
        )
        return {r["patient_id"]: r["eligible_payers"] for r in result}

def eligibility_score(similar_patients, eligibility):
    eligible_scores = [score for pid, score in similar_patients if eligibility.get(pid)]
    total_score = sum([score for _, score in similar_patients])
    if total_score == 0:
        return 0
    return sum(eligible_scores) / total_score

if __name__ == "__main__":
    try:
        new_patient = {
            "Id": "dff5e8b2-1234-4cde-8f9a-abcdef123456",  # unique and different
            "FIRST": "Lars",
            "LAST": "Schmidt",
            "GENDER": "M",
            "BIRTHDATE": "8/15/1985",            # much younger
            "ETHNICITY": "hispanic",             # different
            "RACE": "white",                     # different
            "INCOME": 250000,                    # very high income
            "ZIP": 90210,                        # different, affluent area
            "ADDRESS": "1234 Beverly Hills Blvd",
            "BIRTHPLACE": "Los Angeles California US",
            "CITY": "Beverly Hills",
            "COUNTY": "Los Angeles County",
            "HEALTHCARE_COVERAGE": 500000.00,    # very high
            "HEALTHCARE_EXPENSES": 2000.00,      # very low
            "MARITAL": "S",                      # single
            "PREFIX": "Mr.",
            "STATE": "California",               # different state
        }


        add_patient(new_patient, driver)
        embed_and_store(new_patient["Id"], new_patient, driver)  # No openai argument needed

        embedding = get_embedding(new_patient["Id"])
        # print(f"Embedding for new patient {new_patient['Id']}: {embedding}")

        if embedding is None:
            print("No embedding found for new patient.")
            driver.close()
            exit(1)

        similar_patients = find_similar_patients(embedding, top_k=5)
        print(['"'+str(pid)+'"' for pid, _ in similar_patients])
        eligibility = check_eligibility([str(pid) for pid, _ in similar_patients])
        print(eligibility)
        score = eligibility_score(similar_patients, eligibility)
        print(f"Eligibility score for Medicare/Medicaid: {score:.3f}")
        print("Top similar patients and their eligibility:")
        for pid, sim in similar_patients:
            print(f"Patient {pid} (similarity: {sim:.3f}) - Eligible for: {eligibility.get(pid, [])}")
        driver.close()

    except Exception as e:
        print(f"An error occurred: {e}")
        driver.close()
        exit(1)
