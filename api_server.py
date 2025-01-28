from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import uvicorn
from typing import Optional
import tempfile
import os
from vector_store import VectorStore
from parse_utils import fetch_and_parse_url, fetch_and_parse_pdf
import sqlite3
import logging
from datetime import datetime
from arena_utils import save_block_to_db
import json

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Block Parser API")

# Initialize vector store with environment variables
vector_store_host = os.getenv('VECTOR_STORE_HOST')
vector_store_port = os.getenv('VECTOR_STORE_PORT')
vector_store = VectorStore(host=vector_store_host, port=vector_store_port)

# Initialize DB connection
def get_db():
    db_path = os.getenv('SQLITE_DB_PATH', 'store.sqlite3')
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()

class URLInput(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class SearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 5

def process_block(
    conn: sqlite3.Connection,
    block_id: str,
    url: str,
    content: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """Process and store block data"""
    # Save to SQLite
    block_data = {
        "id": block_id,
        "source": {"url": url},
        "title": title,
        "description": description,
        "metadata": metadata
    }
    
    save_block_to_db(
        conn,
        block_ids=[block_id],
        block_data_by_id={block_id: block_data},
        parsed_block_content_by_url={url: content}
    )
    
    # Update vector store
    vector_store.upsert_blocks({
        block_id: {
            "source_url": url,
            "crawled_text": content,
            "title": title,
            "description": description,
            "metadata": metadata
        }
    })

@app.post("/blocks/url")
async def add_block_from_url(
    url_input: URLInput,
    background_tasks: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_db)
):
    """Add a new block from URL"""
    try:
        # Generate block ID
        block_id = f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Parse content
        if str(url_input.url).lower().endswith('.pdf'):
            content = fetch_and_parse_pdf(str(url_input.url))
        else:
            content = fetch_and_parse_url(str(url_input.url))
            
        if not content:
            raise HTTPException(status_code=400, detail="Failed to parse content")
            
        # Process in background
        background_tasks.add_task(
            process_block,
            conn,
            block_id,
            str(url_input.url),
            content,
            url_input.title,
            url_input.description,
            url_input.metadata
        )
        
        return JSONResponse({
            "status": "success",
            "message": "Block processing started",
            "block_id": block_id
        })
        
    except Exception as e:
        logger.error(f"Error processing URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/blocks/file")
async def add_block_from_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    conn: sqlite3.Connection = Depends(get_db)
):
    """Add a new block from uploaded file"""
    try:
        # Check file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
            
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
            
        try:
            # Parse PDF
            content = fetch_and_parse_pdf(tmp_path)
            if not content:
                raise HTTPException(status_code=400, detail="Failed to parse PDF")
                
            # Generate block ID
            block_id = f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Process in background
            background_tasks.add_task(
                process_block,
                conn,
                block_id,
                file.filename,  # Use filename as URL
                content,
                title,
                description,
                metadata and json.loads(metadata)
            )
            
            return JSONResponse({
                "status": "success",
                "message": "File processing started",
                "block_id": block_id
            })
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        logger.error(f"Error processing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_blocks(query: SearchQuery):
    """Search blocks by content similarity"""
    try:
        results = vector_store.search(query.query, limit=query.limit)
        return JSONResponse({
            "status": "success",
            "results": results
        })
    except Exception as e:
        logger.error(f"Error searching blocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)