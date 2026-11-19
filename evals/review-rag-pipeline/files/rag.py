# === index_build.py ===
from sentence_transformers import SentenceTransformer
import faiss, json

def build_index(docs, out_dir):
    enc = SentenceTransformer("intfloat/multilingual-e5-base")
    chunks = []
    for d in docs:
        for i in range(0, len(d["text"]), 512):          # chunk size
            chunks.append({"doc_id": d["id"], "text": "passage: " + d["text"][i:i + 512]})
    emb = enc.encode([c["text"] for c in chunks], normalize_embeddings=True)
    index = faiss.IndexFlatIP(emb.shape[1]); index.add(emb)
    faiss.write_index(index, f"{out_dir}/index.faiss")
    json.dump(chunks, open(f"{out_dir}/chunks.json", "w"))


# === retriever.py ===
class Retriever:
    def __init__(self, out_dir):
        self.enc = SentenceTransformer("intfloat/multilingual-e5-base")
        self.index = faiss.read_index(f"{out_dir}/index.faiss")
        self.chunks = json.load(open(f"{out_dir}/chunks.json"))

    def search(self, q, k=5):
        try:
            v = self.enc.encode(["query: " + q], normalize_embeddings=True)
            _, I = self.index.search(v, k)
            return [self.chunks[i] for i in I[0]]
        except Exception:
            return []


class RetrieverService:
    def __init__(self, retriever): self.retriever = retriever
    def search(self, q, k=5): return self.retriever.search(q, k)


# === answer.py ===
def build_prompt(question, hits, max_len=3000):
    # Assemble the context block: dedupe by doc, keep best-ranked chunks first,
    # stop when the budget is reached, then add citation markers [1], [2], ...
    seen, parts, total = set(), [], 0
    for h in hits:
        if h["doc_id"] in seen:
            continue
        body = h["text"].removeprefix("passage: ")
        if total + len(body) > max_len:
            break
        seen.add(h["doc_id"])
        parts.append(f"[{len(parts) + 1}] {body}")
        total += len(body)
    context = "\n\n".join(parts)
    return f"Answer using only the sources below. Cite as [n].\n\n{context}\n\nQuestion: {question}"

def answer(llm, svc, question):
    hits = svc.search(question)
    return llm.generate(build_prompt(question, hits))
