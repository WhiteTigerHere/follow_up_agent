import os
import argparse
import google.generativeai as genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from infrastructure.supabase_repo import supabase
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

# Configure Gemini for Embeddings
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "dummy_key"))

def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise ImportError("Please install pypdf to read PDF files.")
    elif ext in ['.txt', '.md']:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def ingest_document(file_path: str, doc_type: str, tags: list):
    print(f"Reading {file_path}...")
    try:
        raw_text = extract_text(file_path)
    except Exception as e:
        print(f"Failed to read file: {e}")
        return
    
    # Recursive character splitting as requested:
    # 400 tokens (~1600 chars), 75 tokens overlap (~300 chars)
    # Order: double newline → single newline → sentence → word
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1600,
        chunk_overlap=300,
        separators=["\n\n", "\n", r"(?<=\. )", " ", ""]
    )
    chunks = splitter.split_text(raw_text)
    print(f"Split into {len(chunks)} chunks. Generating embeddings...")
    
    filename = os.path.basename(file_path)
    success_count = 0
    
    for i, chunk in enumerate(chunks):
        try:
            # Generate 768-D embeddings matching the pgvector_ctx logic
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=chunk,
                task_type="retrieval_document",
                output_dimensionality=768
            )
            embedding = result['embedding']
            
            metadata = {
                "source_filename": filename,
                "doc_type": doc_type,
                "tags": tags
            }
            
            # Insert into the org_document_embeddings table
            supabase.table('org_document_embeddings').insert({
                "content": chunk,
                "embedding": embedding,
                "metadata": metadata
            }).execute()
            
            success_count += 1
        except Exception as e:
            print(f"Error inserting chunk {i+1}: {e}")
            
    print(f"Ingestion complete. Successfully stored {success_count} chunks.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Org Documents into RAG")
    parser.add_argument("file", help="Path to the document (.pdf, .txt, .md)")
    parser.add_argument("--type", default="general", help="Document type (e.g. policy, guide)")
    parser.add_argument("--tags", nargs="*", default=[], help="List of tags")
    args = parser.parse_args()
    
    ingest_document(args.file, args.type, args.tags)
