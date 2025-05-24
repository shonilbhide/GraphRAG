from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from utils.neo4j_helper import *

load_dotenv()

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASS = os.getenv("NEO4J_PASS")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

with driver.session() as session:
    # Create vector indexes for all relevant node types
    session.execute_write(
        create_vector_index,
        index_name="patient_embedding_index",
        node_label="Patient",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )
    session.execute_write(
        create_vector_index,
        index_name="provider_embedding_index",
        node_label="Provider",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )
    session.execute_write(
        create_vector_index,
        index_name="payer_embedding_index",
        node_label="Payer",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )
    session.execute_write(
        create_vector_index,
        index_name="claim_embedding_index",
        node_label="Claim",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )
    session.execute_write(
        create_vector_index,
        index_name="encounter_embedding_index",
        node_label="Encounter",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )
    session.execute_write(
        create_vector_index,
        index_name="medication_embedding_index",
        node_label="Medication",
        embedding_property="embedding",
        embedding_dimension=1536,
        similarity_function="cosine"
    )

driver.close()