from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from fastapi import Query

from langchain.prompts import PromptTemplate
from langchain.document_loaders import PyMuPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from motor.motor_asyncio import AsyncIOMotorClient
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv
import shutil
import os

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MONGO_URL = os.getenv("MONGO_URL")


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


client = AsyncIOMotorClient(MONGO_URL)
db = client["pdf_db"]
chunks_collection = db["pdf_chunks"]
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
    

    
    await chunks_collection.delete_many({"filename": file.filename})

    for idx, chunk in enumerate(chunks):
        await chunks_collection.insert_one({
            "filename": file.filename,
            "chunk_index": idx,
            "chunk_text": chunk.page_content
            
        })
    await qa_pdf_collection.delete_many({"filename": file.filename})
   
    await qa_pdf_collection.insert_one({
        "filename": file.filename,
       
    })
    

    return {"message": "PDF uploaded and processed", "filename": file.filename}


@app.post("/ask")
async def ask_question(filename: str = Form(...), question: str = Form(...)):
   
    cursor = chunks_collection.find({"filename": filename})
    docs = []
    async for doc in cursor:
        docs.append(Document(page_content=doc["chunk_text"]))

    if not docs:
        return {"error": "No content found. Please upload the PDF again."}


    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.7,
    )
  
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
Answer the question using the context below.

Context:
{context}

Question: {question}
Answer:"""
    )

    
    chain = load_qa_chain(llm=llm, chain_type="stuff", prompt=prompt)


    result = chain.invoke({
        "input_documents": docs,
        "question": question
    })
    await qa_pdf_collection.update_one(
    {"filename": filename},
    {
        "$push": {
            "qa_pairs": {
                "question": question,
                "answer": result["output_text"]
            }
        }
    },
    upsert=True
)
   

    return {"answer": result['output_text']}


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