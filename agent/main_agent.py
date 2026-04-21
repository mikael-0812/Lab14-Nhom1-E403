"""
agent/main_agent.py - RAG Agent hai phiên bản cho bài lab regression testing.
BƯỚC 6: Tạo Version 1 (Cũ hơn, dễ hallucinate)
BƯỚC 7: Tạo Version 2 (Hybrid, Reranking, Strict Prompt)
Tham khảo: main_agent_1.py
"""
import asyncio
import json
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Optional, Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ---------------------------------------------------------------------------
# VectorDB loader & Tokenizer (BM25 mô phỏng)
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "vector_db.json"

def _load_db() -> List[Dict]:
    try:
        return json.loads(_DB_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("CẢNH BÁO: Không tìm thấy data/vector_db.json")
        return []

VECTOR_DB: List[Dict] = _load_db()
CHUNK_MAP: Dict[str, Dict] = {str(c["chunk_id"]): c for c in VECTOR_DB}

def _tok(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())

def _bm25(query_tokens: List[str], doc_text: str, k1: float = 1.5, b: float = 0.75) -> float:
    doc_tokens = _tok(doc_text)
    if not doc_tokens: return 0.0
    avgdl = 120
    score = 0.0
    tf_map: Dict[str, int] = {}
    for t in doc_tokens: 
        tf_map[t] = tf_map.get(t, 0) + 1
    dl = len(doc_tokens)
    for qt in set(query_tokens):
        tf = tf_map.get(qt, 0)
        if tf > 0:
            score += (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score

# ---------------------------------------------------------------------------
# Retrieval strategies
# ---------------------------------------------------------------------------
def _dense_retrieve(query: str, top_k: int = 5) -> List[Dict]:
    tokens = _tok(query)
    ranked = sorted(VECTOR_DB, key=lambda c: _bm25(tokens, c["text"]), reverse=True)
    return ranked[:top_k]

def _sparse_retrieve(query: str, top_k: int = 5) -> List[Dict]:
    keywords = [w for w in _tok(query) if len(w) >= 3]
    scored = []
    for c in VECTOR_DB:
        hits = sum(1 for kw in keywords if kw in c["text"].lower())
        scored.append((hits, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]

def _hybrid_rrf(queries: List[str], top_k: int = 5, rrf_k: int = 60) -> List[Dict]:
    """Sử dụng Reciprocal Rank Fusion kết hợp BM25 (dense) và Keyword (sparse)"""
    scores: Dict[str, float] = {}
    for query in queries:
        dense = _dense_retrieve(query, top_k=15)
        sparse = _sparse_retrieve(query, top_k=15)
        for rank, c in enumerate(dense):
            cid = str(c["chunk_id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, c in enumerate(sparse):
            cid = str(c["chunk_id"])
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
    
    top_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    res = []
    for cid in top_ids:
        if cid in CHUNK_MAP:
            c = dict(CHUNK_MAP[cid])
            c['rrf_score'] = scores[cid]
            res.append(c)
    return res

def _rerank(query: str, chunks: List[Dict]) -> List[Dict]:
    """Mô phỏng Reranking sử dụng Exact Match và Keyword Density"""
    query_lower = query.lower()
    scored = []
    for c in chunks:
        text = c["text"].lower()
        score = c.get("rrf_score", 0.0) * 10.0
        # Thưởng nếu cụm từ truy vấn xuất hiện liền kề (exact match)
        if query_lower in text:
            score += 2.0
        # Mật độ keyword
        tokens = _tok(query)
        matches = sum(1 for t in tokens if t in text and len(t) > 2)
        score += matches * 0.5
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored]

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_V1 = (
    "Bạn là một trợ lý AI thông minh. Hãy trả lời câu hỏi sau dựa trên kiến thức "
    "của bạn và các tài liệu tham khảo nêu dưới."
)

SYSTEM_PROMPT_V2 = (
    "Bạn là trợ lý AI nội bộ đáng tin cậy. Chỉ trả lời DỰA HOÀN TOÀN vào phần <context> bên dưới. "
    "Tuyệt đối không sử dụng kiến thức ngoài lề. "
    "Nếu thông tin không có trong tài liệu, trả lời chuẩn cấu trúc: 'Không tìm thấy trong tài liệu.' "
    "Không được suy đoán."
)

class MainAgent:
    def __init__(self, version: str = "V1"):
        self.version = version.upper()
        self.name = f"SupportAgent-{self.version}"
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key, timeout=30.0) if api_key else None
        self.model = "gpt-4o-mini"
        if not api_key:
            print(f"⚠️ [Cảnh báo MainAgent {self.version}] Thiếu thư viện OpenAI API KEY. Chuyển sang MOCK.")

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> tuple[str, int]:
        if not self.client:
            return "Mocking answer vì không tìm thấy OPENAI_API_KEY ở .env", 0
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            text = resp.choices[0].message.content or ""
            tokens = resp.usage.prompt_tokens + resp.usage.completion_tokens if resp.usage else 0
            return text, tokens
        except Exception as e:
            return f"Error Gọi LLM: {e}", 0

    async def query(self, question: str) -> Dict:
        """Giao diện chuẩn cho BenchmarkRunner"""
        if self.version == "V1":
            return await self._query_v1(question)
        else:
            return await self._query_v2(question)

    async def _query_v1(self, question: str) -> Dict:
        # ❌ BƯỚC 6: Tạo Version 1 yếu hơn
        # 1. Retrieval yếu hơn: Bị nhiễu nặng, chỉ lấy 1 chunk random hoặc dense chunk nhưng bị cắt xén
        # Mô phỏng một legacy retriever rất yếu
        pool = VECTOR_DB.copy()
        random.shuffle(pool)
        chunks = pool[:2] # Trả về toàn chunk random -> Không thể có Context đúng
            
        retrieved_ids = [str(c["chunk_id"]) for c in chunks]
        context_texts = [c["text"] for c in chunks]
        
        # 2. Logic cũ: Không có RRF, rác có thể nhiều.
        # 3. Prompt chưa tối ưu: Trộn lẫn kiến thức LLM và Context -> Có thể Hallucinate
        context_str = "\n".join([f"[{i+1}] {t}" for i, t in enumerate(context_texts)])
        user_prompt = f"Tài liệu tham khảo:\n{context_str}\n\nCâu hỏi: {question}"
        
        answer, tokens = await self._call_openai(SYSTEM_PROMPT_V1, user_prompt)
        
        return {
            "answer": answer,
            "retrieved_ids": retrieved_ids,
            "contexts": context_texts,
            "metadata": {"version": self.version, "tokens_used": tokens}
        }

    async def _query_v2(self, question: str) -> Dict:
        # ✅ BƯỚC 7: Tạo Version 2 tối ưu (Mục tiêu: V2 > V1)
        # 1. Retrieval tốt hơn: Tạo biến thể câu hỏi
        variants = [question, question + " chi tiết", "giải thích " + question]
        
        # 2. Dùng Hybrid RRF mạnh mẽ
        candidates = _hybrid_rrf(variants, top_k=15)
        
        # 3. Reranking tốt hơn: Ưu tiên top 3 chunks có keyword chuẩn
        reranked = _rerank(question, candidates)
        chunks = reranked[:3]
        retrieved_ids = [str(c["chunk_id"]) for c in chunks]
        context_texts = [c["text"] for c in chunks]
        
        # 4. Prompt tốt hơn: Dùng <context> tags chống jailbreak nội dung ngoài
        # 5. Final Answer tốt hơn do được ground chặt chẽ.
        context_blocks = []
        for c in chunks:
            context_blocks.append(f"[{c['source']} - {c['section']}]\n{c['text']}")
        context_str = "\n\n".join(context_blocks)
        user_prompt = f"<context>\n{context_str}\n</context>\n\nCâu hỏi: {question}"
        
        answer, tokens = await self._call_openai(SYSTEM_PROMPT_V2, user_prompt)
        
        # Format "Khong tim thay trong tai lieu" thanh NOT_FOUND chuẩn nếu LLM bảo thế
        if "Không tìm thấy trong tài liệu" in answer:
            answer = "Không tìm thấy thông tin trong tài liệu."

        return {
            "answer": answer,
            "retrieved_ids": retrieved_ids,
            "contexts": context_texts,
            "metadata": {"version": self.version, "tokens_used": tokens}
        }

if __name__ == "__main__":
    async def local_test():
        q = "Chính sách nghỉ dưỡng của kĩ sư năm 2024?"
        v1 = MainAgent(version="v1")
        print("--- V1 ---")
        print((await v1.query(q))["answer"])
        
        v2 = MainAgent(version="v2")
        print("\n--- V2 ---")
        print((await v2.query(q))["answer"])
        
    asyncio.run(local_test())
