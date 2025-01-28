import requests
import json
import sqlite3
from urllib.parse import urlparse

from arena_utils import json

BLOCKS_PER_PAGE = 100  # 100 is max pages

def get_channel(channel_slug):
    """Get basic channel info from Are.na API"""
    url = f"https://api.are.na/v2/channels/{channel_slug}?per={BLOCKS_PER_PAGE}"
    r = requests.get(url)
    return r.json()

def get_channel_blocks_paginated(channel_slug, per=BLOCKS_PER_PAGE, pages=5):
    """Get all blocks from a channel with pagination"""
    blocks = []
    has_next = True
    page = 1
    while has_next:
        try:
            url = f"https://api.are.na/v2/channels/{channel_slug}/contents?per={BLOCKS_PER_PAGE}&page={page}"
            r = requests.get(url)
            data = r.json()
            blocks.extend(data["contents"])
            # stop requesting more when we cross the number of blocks per page
            has_next = len(data["contents"]) == BLOCKS_PER_PAGE
            page += 1
        except Exception as e:
            print("Error", e)
            has_next = False
    return blocks

def get_hostname(url):
    """Extract hostname from URL"""
    parsed_uri = urlparse(url)
    return '{uri.scheme}://{uri.netloc}/'.format(uri=parsed_uri)

def filter_blocks_by_hostname(blocks, hostname_whitelist={"https://en.wikipedia.org/"}):
    """Filter blocks to only those from whitelisted hostnames"""
    return [
        block for block in blocks
        if block.get("source") is not None 
        and get_hostname(block["source"].get("url", "")) in hostname_whitelist
    ]

def save_block_to_db(conn, block_ids, block_data_by_id, parsed_block_content_by_url):
    """
    Upsert block data to SQLITE DB, especially crawled text body
    """
    cur = conn.cursor()

    data = []
    for block_id in block_ids:
        block_valid = block_data_by_id.get(block_id) is not None
        block_url_valid = block_data_by_id.get(block_id).get("source") is not None
        if block_valid and block_url_valid:
            try:
                data.append((
                    block_id, # Are.na block ID
                    block_data_by_id[block_id].get("source", {}).get("url"), # path to website
                    json.dumps(block_data_by_id[block_id]), # raw body from API excluding crawled text
                    parsed_block_content_by_url.get(block_data_by_id[block_id].get("source", {}).get("url")), # markdown content
                    block_data_by_id[block_id].get("title"),
                    block_data_by_id[block_id].get("description"),
                    json.dumps(block_data_by_id[block_id].get("metadata")) if block_data_by_id[block_id].get("metadata") else None,
                ))
            except Exception as e:
                print(f"Failed to format block {block_id} for SQL:", e)
    
    query = """
    INSERT INTO "block" (
      id,
      source_url,
      full_json,
      crawled_text,
      title,
      description,
      metadata
     ) VALUES (
      ?, ?, ?, ?, ?, ?, ?
     )
      ON CONFLICT (id)
      DO UPDATE SET
        source_url = excluded.source_url,
        full_json = excluded.full_json,
        crawled_text = excluded.crawled_text,
        title = excluded.title,
        description = excluded.description,
        metadata = excluded.metadata,
        updated_at = CURRENT_TIMESTAMP;
    """
    cur.executemany(query, data)
    conn.commit()

def init_db(conn):
    """Initialize SQLite database with block table"""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS "block" (
      id                   string primary key,
      source_url          string,
      crawled_text        TEXT,
      title               string,
      description         string, 
      metadata            string,
      created_at          timestamp DEFAULT CURRENT_TIMESTAMP,
      updated_at          timestamp DEFAULT CURRENT_TIMESTAMP,
      full_json           TEXT
    );
    """)
    conn.commit()


def get_blocks_with_content_from_db(conn, block_ids):
    """Get full block data including crawled text from DB"""
    cur = conn.cursor()
    placeholders = ','.join('?' * len(block_ids))
    cur.execute(f"""
        SELECT id, source_url, crawled_text, title, description, metadata 
        FROM block 
        WHERE id IN ({placeholders})
    """, block_ids)

    return {
        row[0]: {
            "source_url": row[1],
            "crawled_text": row[2],
            "title": row[3],
            "description": row[4],
            "metadata": json.loads(row[5]) if row[5] else None
        }
        for row in cur.fetchall()
    }


def get_existing_blocks_from_db(conn, block_ids):
    """Fetch existing blocks from DB"""
    cur = conn.cursor()
    placeholders = ','.join('?' * len(block_ids))
    cur.execute(f"""
        SELECT id, source_url, crawled_text 
        FROM block 
        WHERE id IN ({placeholders})
    """, block_ids)
    return {row[0]: {"source_url": row[1], "crawled_text": row[2]}
            for row in cur.fetchall()}