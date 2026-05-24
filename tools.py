from docx import Document
from openai import OpenAI
from PyPDF2 import PdfReader
import chromadb
import requests
import json
import pandas as pd
import os
import pandas as pd
from threading import Lock

file_lock = Lock()

# Initialize OpenAI client
client = OpenAI(api_key="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")

# Initialize ChromaDB client
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="knowledge_base")


from chromadb import PersistentClient

chroma_client = PersistentClient(path="chroma_db")   # folder where DB will be stored
collection = chroma_client.get_or_create_collection("my_collection")


# Step 1: Extract text from the PDF
def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def chunk_text(text, chunk_size=1000):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def store_embeddings_in_chromadb(chunks):
    for i, chunk in enumerate(chunks):
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunk
        ).data[0].embedding

        collection.add(
            ids=[f"chunk_{i}"],
            documents=[chunk],
            embeddings=[emb]
        )

    print(f"✅ Stored {len(chunks)} chunks in ChromaDB.")


def generate_with_gpt(prompt):

    full_response = ""

    with client.responses.stream(
        model="gpt-4.1",
        input=[{"role": "user", "content": prompt}]
    ) as stream:

        for event in stream:
            if event.type == "response.output_text.delta":
                text = event.delta
                print(text, end="", flush=True)
                full_response += text

    return full_response


def rag_search(query):
    # Get embedding of query
    query_emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    ).data[0].embedding

    # Similar chunks
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=3
    )

    context = "\n\n".join(results["documents"][0])

    prompt = f"""
    You are the helpful assistant for Loud Revel (Digital Marketing Agency). You should not answer any question that is not related to Loud Revel.
Use the following context to answer the question.

Context:
{context}

Question: {query}

Answer:
"""

    print("\n📘 Answer:")
    response = generate_with_gpt(prompt)
    return response

# def lead_gen(name:str,mob:int,lead_score:int):
#     df = pd.read_csv("Knowledge\Leads.csv")
#     df.loc[len(df)] = [name, mob, lead_score]
#     df.to_csv("Knowledge\Leads.csv", index=False)



def lead_gen(name: str, mob: int, lead_score: int):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "Knowledge", "Leads.csv")

    with file_lock:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
        else:
            df = pd.DataFrame(columns=["name", "mob", "lead_score"])

        df.loc[len(df)] = [name, mob, lead_score]
        df.to_csv(csv_path, index=False)




if __name__ == "__main__":
    # Example usage
    file_path = r"C:\Users\ssshi\PycharmProjects\EdAIsstant\Knowledge\Prospectus.docx"
    
    _, extension = os.path.splitext(file_path)
    extension = extension.lower() # Convert to lowercase for reliable comparison

    # --- 3. Conditional execution (if/elif/else) ---
    if extension == '.pdf':
        # Your code for PDF extraction goes here
        text = extract_text_from_pdf(file_path)
        
    elif extension == '.docx':
        # Your code for DOCX extraction goes here
        text = extract_text_from_docx(file_path)



    chunks = chunk_text(text, chunk_size=1000)
    store_embeddings_in_chromadb(chunks)

    query = "What is the main topic of the document?"
    rag_search(query)