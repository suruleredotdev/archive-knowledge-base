import sqlite3
from arena_utils import *

# Example channel configuration
ARENA_CHANNELS = [ 
    { "name": "Permaculture", "slug": "permaculture-gndkdg_ckpc" },
    { "name": "Historiography", "slug": "historiography-kr29u84pivs" },
    { "name": "African Empires+States", "slug": "african-empires-states" },
]

def main():
    # Initialize DB
    conn = sqlite3.connect('store.sqlite3')
    init_db(conn)

    # Get all blocks from channels
    channel_blocks = {}
    for channel in ARENA_CHANNELS:
        # Get channel info
        channel_blocks[channel["name"]] = get_channel(channel["slug"])
        # Override with full set of contents (paginated)
        channel_blocks[channel["name"]]["contents"] = get_channel_blocks_paginated(channel["slug"])

    # Convert to flat list and filter to Wikipedia blocks
    all_channel_blocks = [block for channel in channel_blocks.values() for block in channel["contents"]]
    wikipedia_blocks = filter_blocks_by_hostname(all_channel_blocks, {"https://en.wikipedia.org/"})

    # Create lookup by ID
    all_blocks_by_id = {block["id"]: block for block in all_channel_blocks}

    # Save to DB (note: parsed_block_content_by_url would need to be populated)
    parsed_block_content_by_url = {}  # Map of URL -> parsed content
    save_block_to_db(conn, 
        block_ids=list(all_blocks_by_id.keys()),
        block_data_by_id=all_blocks_by_id,
        parsed_block_content_by_url=parsed_block_content_by_url
    )

    conn.close()

if __name__ == "__main__":
    main()