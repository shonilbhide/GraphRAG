# Patient Eligibility GraphRAG System
[![License: CC BY-NC-ND 4.0](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
---

## 🩺 What is This Project?

This project is a **Graph Retrieval-Augmented Generation (GraphRAG) system** for healthcare. It helps answer questions like:

> “Is this new patient eligible for Medicare or Medicaid?”

It does this by building a smart knowledge graph of patients, claims, providers, payers, and more, then using AI to find patients most similar to a new applicant and estimate their eligibility.

![bankcrupcy](https://github.com/shonilbhide/GraphRAG/blob/main/data/TheOfficeGIF.gif)
---

## 🚀 Why Was It Built?

- **Healthcare data is complex.** Patients, doctors, insurance, claims, and medications are all connected.
- **Eligibility is nuanced.** Simple rules aren’t enough—real-world data and similarity matter.
- **GraphRAG combines the best of both worlds:**  
  - **Graphs** show relationships and context.  
  - **AI embeddings** find “similar” patients, even if their details aren’t identical.
- **Result:** More accurate, explainable, and fair eligibility predictions.


---

## 🏗️ How Does It Work?

### 1. **Build the Knowledge Graph**
- Loads CSV data (patients, encounters, providers, payers, claims, medications) into [Neo4j](https://neo4j.com/).
- Each entity is a **node**; their connections (e.g., a claim paid by a payer) are **edges**.

### 2. **Add Demographics**
- Patients are connected to age, income, and zipcode nodes for richer context.

### 3. **Generate Embeddings**
- Each patient’s information is converted into a vector (embedding) using a **free, local AI model** ([Sentence Transformers](https://www.sbert.net/)).
- These embeddings let us measure “how similar” two patients are.

### 4. **Create a Vector Index**
- Neo4j’s vector index enables fast, AI-powered similarity search.

### 5. **Eligibility Prediction**
- For a new patient, the system:
  - Adds their data to the graph.
  - Generates their embedding.
  - Finds the most similar patients.
  - Checks if those similar patients were eligible for Medicare/Medicaid.
  - Calculates a **score** showing how likely the new patient is eligible.

---

## 🗂️ Project Structure

.
- ├── data/
- │ ├── patients.csv
- │ ├── encounters.csv
- │ ├── providers.csv
- │ ├── payers.csv
- │ ├── claims.csv
- │ └── medications.csv
- ├── utils/
- │ ├── neo4j_helper.py
- │ └── add_patient.py
- ├── create_graph.py
- ├── create_graph_and_vectore.py
- ├── create_vectors.py
- ├── graphrag_retirieve_and_store.py
- ├── .env
- ├── .gitignore
- └── README.md


---

## ⚙️ How to Run

### 1. **Install Requirements**
pip install pandas neo4j python-dotenv sentence-transformers



### 2. **Neo4j Setup**
- Install Neo4j locally or use [Neo4j Aura](https://neo4j.com/cloud/aura/).
- Set your connection details in a `.env` file:
    - NEO4J_URI=bolt://localhost:7687
    - NEO4J_USER=neo4j
    - NEO4J_PASS=your_password



### 3. **Prepare Data**
- Place your CSV files in the `data/` directory.

### 4. **Build the Graph**
python create_graph.py


or, to also generate embeddings and vector index:
python create_graph_and_vectore.py



### 5. **(If needed) Generate Embeddings and Vector Index Separately**
python create_vectors.py



### 6. **Test Eligibility for a New Patient**
- Edit the patient dictionary in `graphrag_retirieve_and_store.py` to your test case.
- Run:
python graphrag_retirieve_and_store.py


- The script will print:
- The most similar patients
- Their eligibility status
- A score for Medicare/Medicaid eligibility

---

## 🖼️ Visuals

![Knowledge Graph Example](https://github.com/shonilbhide/GraphRAG/blob/main/data/Neo4J1.png)


---

## 💡 Why Use GraphRAG in Healthcare?

- **Personalized:** Finds the most truly similar patients, not just those with matching codes.
- **Explainable:** Shows which similar cases led to the eligibility decision.
- **Efficient:** Uses AI and graph technology for fast, scalable results.
- **No expensive APIs:** Embeddings are generated locally, so there are no rate limits or costs.

---

## 📝 Example Output

- Eligibility score for Medicare/Medicaid: 0.20
- Top similar patients and their eligibility:
- Patient 123... (similarity: 0.19) - Eligible for: ['Medicare']
- Patient 456... (similarity: 0.01) - Eligible for: []
...


---

## 📚 References & Further Reading

- [What is GraphRAG? (IBM)](https://www.ibm.com/think/topics/graphrag)
- [MedGraphRAG: Medical Graph RAG Paper (arXiv)](https://arxiv.org/abs/2408.04187)
- [Neo4j Vector Search Docs](https://neo4j.com/docs/cypher-manual/current/indexes-for-vector-search/)
- [Sentence Transformers Documentation](https://www.sbert.net/)
- [Synthea Synthetic Patient Data](https://synthea.mitre.org/)

---

## 📬 Contact

For questions, feature requests, or contributions, please open an issue or pull request.

---
## License

This work is licensed under a [Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International License](https://creativecommons.org/licenses/by-nc-nd/4.0/).

*This project shows how AI and knowledge graphs can make healthcare more transparent, efficient, and fair for everyone.*