

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI

from fastapi import Query
from langchain_core.prompts import ChatPromptTemplate

import uvicorn
from langchain_core.vectorstores import InMemoryVectorStore


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from motor.motor_asyncio import AsyncIOMotorClient
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv

from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
import shutil

import os
load_dotenv()
from langchain_google_genai import GoogleGenerativeAIEmbeddings
os.environ["GOOGLE_API_KEY"]=os.getenv("GOOGLE_API_KEY")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")

vector_store = InMemoryVectorStore(embeddings)
app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


client = AsyncIOMotorClient("mongodb://localhost:27017")

db = client["pdf_db"]

qa_pdf_collection=db["pdf_qa"]

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name

    
    loader = PyMuPDFLoader(temp_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(docs)
    
    for doc in chunks:
        doc.metadata["filename"] = file.filename
    vector_store.add_documents(documents=chunks)
    
    return {"message": "PDF uploaded and processed", "filename": file.filename}


@app.post("/ask")
async def ask_question(filename: str = Form(...), question: str = Form(...)):

 llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest", 
        temperature=0
    )

 retriever = vector_store.as_retriever(
    search_kwargs={
        "filter": lambda doc: doc.metadata.get("filename") == filename,
        "k": 5
    }
)

 system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Keep the "
        "answer concise."
        "\n\n"
        "{context}"
    )

 prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

 question_answer_chain = create_stuff_documents_chain(llm, prompt)
 rag_chain = create_retrieval_chain(retriever, question_answer_chain)
 response = rag_chain.invoke({"input": question,})
 
 await qa_pdf_collection.update_one(
    {"filename": filename},
    {
        "$push": {
            "qa_pairs": {
                "question": question,
                "answer":response["answer"]
            }
        }
    },
    upsert=True
)
 
 return response



@app.get("/export-pdf")
async def export_pdf(filename: str = Query(...)):
    doc = await qa_pdf_collection.find_one({"filename": filename})
    if not doc or "qa_pairs" not in doc:
        return {"qa_pairs": []}
    return {"qa_pairs": doc["qa_pairs"]}
    


@app.get("/")
def read_root():
    return {"message": "PDF Q&A App is running!"}
@app.get("/healthz")
def health_check():
    return {"status": "ok"}


@app.get("/hii")
def need():
     return "hii"



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

