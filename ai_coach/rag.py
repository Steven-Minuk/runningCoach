# ai_coach/rag.py

import os
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter


VECTORSTORE_PATH = "ai_coach/vectorstore"


def build_vectorstore(pdf_paths: list[str]):
    """Build vectorstore from PDF files — run once"""
    print("Building vectorstore from PDFs...")

    docs = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        docs.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(docs)
    print(f"Created {len(chunks)} chunks from {len(docs)} pages")

    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(VECTORSTORE_PATH)
    print(f"Vectorstore saved to {VECTORSTORE_PATH}")


def load_vectorstore():
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )
    return FAISS.load_local(
        VECTORSTORE_PATH,
        embeddings,
        allow_dangerous_deserialization=True
    )


@tool
def search_running_docs(query: str) -> str:
    """Search running science documents for training advice.
    Use this for questions about training methodology, recovery, pacing, nutrition."""
    vectorstore = load_vectorstore()
    results = vectorstore.similarity_search(query, k=3)

    if not results:
        return "No relevant information found in running documents."

    response = "From running science documents:\n\n"
    for i, doc in enumerate(results):
        response += f"[{i+1}] {doc.page_content}\n\n"

    return response