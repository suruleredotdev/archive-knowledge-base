from arena_utils import *
from arena_utils import get_blocks_with_content_from_db
from arena_utils import get_existing_blocks_from_db
from parse_utils import *
from vector_store import VectorStore
import sqlite3
import argparse

def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description='Parse Are.na blocks to markdown')
    parser.add_argument('--pdf-only', 
                       action='store_true',
                       help='Only process PDF files')
    parser.add_argument('--wikipedia-only', 
                       action='store_true',
                       help='Only process Wikipedia blocks')
    parser.add_argument('--debug', 
                       action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--transfer-vectors-only', action='store_true', help='Only read already parsed blocks from SQLite into vector storage')
    parser.add_argument('--skip-vectors', action='store_true', help='Skip vector storage')
    parser.add_argument('--qdrant-host', help='Remote Qdrant host')
    parser.add_argument('--qdrant-port', type=int, help='Remote Qdrant port')
    args = parser.parse_args()

    if args.transfer_vectors_only and args.skip_vectors:
        logger.error("Cannot use --transfer-vectors-only with --skip-vectors")
        exit(1)

    # Setup debug logging
    setup_logging(debug=args.debug)
    
    # Initialize DB and vector store
    conn = sqlite3.connect('store.sqlite3')
    init_db(conn)
    
    if not args.skip_vectors:
        vector_store = VectorStore(
            host=args.qdrant_host,
            port=args.qdrant_port
        )

    if not args.transfer_vectors_only:
        # Get all blocks from DB
        cur = conn.cursor()
        cur.execute("SELECT id FROM block")
        block_ids = [row[0] for row in cur.fetchall()]
        
        # Get full block data including parsed content
        blocks_with_content = get_blocks_with_content_from_db(conn, block_ids)
        vector_store.upsert_blocks(blocks_with_content)
        return

    # Get blocks from multiple channels
    channel_slugs = [
        "historiography-kr29u84pivs",
        "permaculture-gndkdg_ckpc",
        "african-empires-states",
    ]
    blocks = []
    for channel_slug in channel_slugs:
        channel_blocks = get_channel_blocks_paginated(channel_slug)
        blocks.extend(channel_blocks)

    # Filter blocks based on pdf_only flag
    if args.pdf_only:
        logger.info("PDF-only mode enabled")
        def is_pdf_block(block):
            if not block.get("source") or not block["source"].get("url"):
                return False
            url = block["source"]["url"].lower()
            content_type = block["source"].get("content_type", "")
            return is_pdf_url(url, content_type)
        
        blocks_to_parse = list(filter(is_pdf_block, blocks))
    elif args.wikipedia_only:
        logger.info("Wikipedia-only mode enabled")
        wikipedia_blocks = filter_blocks_by_hostname(blocks)
        blocks_to_parse = wikipedia_blocks
    else:
        logger.info("Processing all content types")
        blocks_to_parse = blocks

    blocks_by_id = {block["id"]: block for block in blocks_to_parse}

    # Check which blocks already exist in DB
    existing_blocks = get_existing_blocks_from_db(conn, list(blocks_by_id.keys()))

    # Filter to blocks that need parsing
    blocks_to_parse = [
        block for block in blocks_to_parse 
        if block["id"] not in existing_blocks 
        or existing_blocks[block["id"]]["crawled_text"] is None
    ]

    logger.info(f"Found {len(blocks_to_parse)} blocks to parse")

    # Parse content (passing pdf_only flag)
    parsed_content = parse_block_contents(blocks_to_parse, pdf_only=args.pdf_only)

    # Save to DB
    save_block_to_db(conn, 
        block_ids=list(blocks_by_id.keys()),
        block_data_by_id=blocks_by_id,
        parsed_block_content_by_url=parsed_content
    )

    # Save to vector store
    if not args.skip_vectors:
        # Get full block data including parsed content
        blocks_with_content = get_blocks_with_content_from_db(conn, list(blocks_by_id.keys()))
        vector_store.upsert_blocks(blocks_with_content)

    conn.close()

if __name__ == "__main__":
    main()