import csv
import json
from ingestion.extract import extract_pages
from ingestion.chunk import chunk_document

total = 0
with open("data/sources.csv", encoding="utf-8") as f, \
     open("data/chunks.jsonl", "w", encoding="utf-8") as out:
    for row in csv.DictReader(f):
        row["year"] = int(row["year"])
        chunks = chunk_document(row, extract_pages(f"data/raw/{row['doc_id']}.pdf"))
        for c in chunks:
            out.write(json.dumps(c, ensure_ascii=False) + "\n")
        total += len(chunks)
        print(f"{row['doc_id']}: {len(chunks)} chunks")
print(f"Total: {total} chunks")