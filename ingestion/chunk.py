import re
import tiktoken

ENC = tiktoken.get_encoding("cl100k_base")
HEADING = re.compile(r"^(?:[A-Z][A-Za-z ,&'-]{3,80}|\d+(?:\.\d+)*\s+.+)$")


def chunk_document(meta: dict, pages: list[dict], size: int = 500, overlap: int = 75) -> list[dict]:
    chunks, buf, section, start_page = [], [], "Introduction", 1

    def flush():
        if not buf:
            return
        body = " ".join(buf)
        text = f"{meta['title']} - {section}\n\n{body}"   # each chunk carries its own context
        chunks.append({**meta, "chunk_id": f"{meta['doc_id']}-{len(chunks):04d}",
                       "section": section, "page": start_page, "content": text})

    for p in pages:
        for line in p["text"].splitlines():
            line = line.strip()
            if not line:
                continue
            if HEADING.match(line) and len(line.split()) < 12:
                flush()
                buf, section, start_page = [], line, p["page"]
                continue
            buf.append(line)
            if len(ENC.encode(" ".join(buf))) >= size:
                flush()
                tail = ENC.decode(ENC.encode(" ".join(buf))[-overlap:])
                buf, start_page = [tail], p["page"]
    flush()
    return chunks