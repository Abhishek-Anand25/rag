from graph import RAGAgent,rag_app,lead_gen_node,res,client
from tools import extract_text_from_docx, extract_text_from_pdf
from openai import OpenAI
import os


file_path = r"Knowledge/Prospectus.docx"
rag_state = {
    "file_path": file_path
}
embdStart = rag_app.invoke(rag_state)

Queries = []



def admission_enquiry(query:str):
    

    result = res.invoke({"query": query})
    # print(result.get("answer"))

    Queries.append(query)
    print("\n")

    return result.get("answer")
