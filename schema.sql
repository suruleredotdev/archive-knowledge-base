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
