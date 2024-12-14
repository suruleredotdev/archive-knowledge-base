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

## Dev Log

### Fri Dec 13 2024 5:01pm

Goals:
- [ ] Upsert block JSON data to SQL table, if updated_at is superseded
  - Take pulled JSON data and insert into database rows including
    all corresponding fields from above


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


