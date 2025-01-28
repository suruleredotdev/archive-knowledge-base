# archive-knowledge-base

Project to download are.na archives and progressively turn them to a searchable knowledgebase

Initially we'll download each block and metadata in a few key channels into a knowledge base in a SQL table,
mapping the relevant metadata and saving the raw JSON of the API response for successive syncs. We'll store
this in a `blocks` table, using the same etymology as [Are.na](https://are.na)

Then we'll transform the data into keyword cloud using known techniques, to index back back to the source blocks.

An additional index on the data will be for information fragments, the kind that might be suited for retrieval
from a RAG "Retriaval-Augmented Generation" system by a (LLM) Large Language Model


# Data Storage

## Blocks
Initial indexing table will take this form:

```sql
CREATE TABLE IF NOT EXISTS "block" (
  id                   string primary key,         -- Are.na block ID, or UUID, from another source 
  source_url           string,
  crawled_text         TEXT,                       -- crawled HTML inner text or PDF body
  title                string,
  description          string,
  metadata             string,                     -- Generic metadata
  created_at           timestamp DEFAULT CURRENT_TIMESTAMP,
  updated_at           timestamp DEFAULT CURRENT_TIMESTAMP,
  full_json            TEXT
);
```

The general algorithm for indexing from Are.na will involve readig a block from the Are.na API, and if it does not yet exist in the database, or hasn't yet been


# Project Tracker

## Projects

- Sync Are.na data to SQL database
- Create knowledge database compatible with LLMs (RAG)

## Dev Log

### Tuesday Jan 28 2025 10:00am

- [x] Generate and test data scraping and vector storage libraries
- [x] Generate and test local scripts
- [x] Generate and test API server
- [x] Setup Qdrant vector store (free 1GB cluster)
  - [ ] Run scripts to populate vector store
- [ ] Deploy API

### Wednesday Dec 18 2024 8:10pm
Goals:
- [x] Pull all block data, filter down to relevant data, get content and convert to Markdown
  - Did this for Wikipedia data only for now
  - Will later do other known text sites
  - Lastly will do PDF data extraction to 

- [] Push block data and content to SQL database

- [] Generate chunks of block content and build text embeddings

- [] Test cgenerating embeddings of data

### Fri Dec 13 2024 5:01pm

Goals:
- [x] Upsert block JSON data to SQL table, if updated_at is superseded
  - Take pulled JSON data and insert into database rows including
    all corresponding fields from above

Log:
- 6:10pm Successfully setup script to upsert rows based on Are.na blocks
  - Updated script to typescript and added types
  - Confirmed data in DB
    - Saw the following in the DB
      ```sql
      sqlite> select title from block;
      Yoruba Gurus: Indigenous Production of Knowledge in Africa By Toyin Falola
      Akure–Benin War - Wikipedia
      Finding Bàrà: History at an Empire Town - Olongo Africa
      Yoruba people - Wikipedia
      Ife (from ca. 6th Century) | Essay | The Metropolitan Museum of Art | Heilbrunn Timeline of Art History
      Collection of carved planks and beams from Yoruba Temples
      ```
    - Noticed what I've seen earlier with Are.na only returning a subset of data intermittently
  - NEXT: switching gears to see what actionable info can be pulled from this
    - Noticing that only some blocks have their crawled text indexed by Are.na. It seems Are.na does this optimistically
      based on user navigation. Can I do this via Are.na client/API?


### Wed Dec 11 2024 1:23am

So-far:
- Ported an earlier script to do the simple download of a date range 
  of blocks from Are.na. 
  - Confirmed this works, and can dump channel JSON to std-out
- Setup some stub functions for SQL work, but leave that

Next:
- Upsert block JSON data to SQL table, if updated_at is superseded
- Review data quality (on-going thing, check for general usability by querying)

More details in commit b732a57 message 


