import pandas as pd

def batcher(iterable, size=1000):
    for pos in range(0, len(iterable), size):
        yield iterable[pos:pos+size]

# --- Create Nodes ---
def create_nodes(label, data, id_col,driver):
    for batch in batcher(data.to_dict("records")):
        with driver.session() as session:
            session.write_transaction(
                lambda tx, b: tx.run(
                    f"UNWIND $batch AS row MERGE (n:{label} {{{id_col}: row.{id_col}}}) SET n += row",
                    batch=b
                ), batch
            )

# --- Create Demographic Nodes (Zipcode, Age_Range, Income_Range) and relationships ---
def get_age(birthdate, ref_date="2025-05-16"):
    try:
        bd = pd.to_datetime(birthdate, errors='coerce')
        ref = pd.to_datetime(ref_date)
        if pd.isnull(bd):
            return None
        return int((ref - bd).days // 365.25)
    except:
        return None

def age_bucket(age):
    if age is None:
        return "Unknown"
    if age < 18:
        return "0-17"
    elif age < 30:
        return "18-29"
    elif age < 45:
        return "30-44"
    elif age < 65:
        return "45-64"
    else:
        return "65+"

def income_bucket(income):
    try:
        income = float(income)
    except:
        return "Unknown"
    if income < 20000:
        return "<20k"
    elif income < 50000:
        return "20k-50k"
    elif income < 100000:
        return "50k-100k"
    else:
        return "100k+"
    
# Connect patients to demographic nodes
def connect_patient_demographics(batch, driver):
    query = """
    UNWIND $batch AS row
    MATCH (p:Patient {Id: row.Id})
    MATCH (a:Age_Range {range: row.AGE_RANGE})
    MERGE (p)-[:IN_AGE_RANGE]->(a)
    WITH p, row
    MATCH (i:Income_Range {range: row.INCOME_RANGE})
    MERGE (p)-[:IN_INCOME_RANGE]->(i)
    WITH p, row
    MATCH (z:Zipcode {zipcode: row.ZIPCODE})
    MERGE (p)-[:LIVES_IN]->(z)
    """
    with driver.session() as session:
        session.write_transaction(lambda tx, b: tx.run(query, batch=b), batch)

# --- Create Relationships ---
def create_relationships(data, query, driver):
    for batch in batcher(data.to_dict("records")):
        with driver.session() as session:
            session.write_transaction(lambda tx, b: tx.run(query, batch=b), batch)


def create_vector_index(tx, index_name, node_label, embedding_property, embedding_dimension, similarity_function):
    query = (
        f"CREATE VECTOR INDEX {index_name} "
        f"FOR (n:{node_label}) ON (n.{embedding_property}) "
        f"OPTIONS {{indexConfig: {{`vector.dimensions`: {embedding_dimension}, "
        f"`vector.similarity_function`: '{similarity_function}'}}}}"
    )
    tx.run(query)