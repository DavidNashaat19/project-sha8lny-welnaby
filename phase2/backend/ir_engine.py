import math
from collections import defaultdict
from typing import List, Dict, Set, Tuple

class InvertedIndex:
    def __init__(self):
        # term -> {doc_id: [positions]}
        self.index: Dict[str, Dict[int, List[int]]] = defaultdict(lambda: defaultdict(list))
        self.doc_lengths: Dict[int, int] = {}
        self.total_docs = 0

    def build(self, documents: List[dict]):
        self.total_docs = len(documents)
        for doc in documents:
            doc_id = doc['doc_id']
            tokens = doc.get('tokens', [])
            self.doc_lengths[doc_id] = len(tokens)
            for pos, term in enumerate(tokens):
                self.index[term][doc_id].append(pos)

    def lookup(self, term: str) -> Dict[int, List[int]]:
        return self.index.get(term, {})

class TFIDFScorer:
    def __init__(self, index: InvertedIndex, documents: List[dict] = None, k1=1.5, b=0.75):
        self.index = index
        self.documents = {d['doc_id']: d for d in documents} if documents else {}
        self.k1 = k1
        self.b = b
        self.avgdl = sum(index.doc_lengths.values()) / max(1, index.total_docs)

    def idf(self, term: str) -> float:
        df = len(self.index.lookup(term))
        if df == 0:
            return 0.0
        # standard Robertson IDF
        return math.log((self.index.total_docs - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query_terms: List[str], doc_id: int) -> float:
        score = 0.0
        doc_len = self.index.doc_lengths.get(doc_id, 0)
        if doc_len == 0:
            return 0.0

        doc = self.documents.get(doc_id, {})
        title_text = doc.get('title', '').lower()
        skills = [s.lower() for s in doc.get('skills', [])]

        for term in query_terms:
            tf = len(self.index.lookup(term).get(doc_id, []))
            if tf > 0:
                # Boosting logic
                boost = 1.0
                if term in title_text: boost += 1.5
                if any(term in s for s in skills): boost += 1.0

                idf_val = self.idf(term)
                # BM25 tf normalization
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl)))
                score += idf_val * tf_norm * boost
        return score

    def explain(self, term: str, doc_id: int) -> dict:
        tf_raw = len(self.index.lookup(term).get(doc_id, []))
        df = len(self.index.lookup(term))
        N = self.index.total_docs
        idf_val = self.idf(term)
        
        # Simple TF-IDF for explanation (as per prompt request for classic Robertson formula representation)
        tf_normalized = tf_raw / max(1, self.index.doc_lengths.get(doc_id, 1))
        tfidf = tf_normalized * idf_val

        return {
            "term": term,
            "doc_id": doc_id,
            "tf_raw": tf_raw,
            "tf_normalized": round(tf_normalized, 3),
            "df": df,
            "N": N,
            "idf": round(idf_val, 3),
            "tfidf": round(tfidf, 3),
            "formula": f"tf({tf_raw}/{max(1, self.index.doc_lengths.get(doc_id, 1))}) × log({N}/{df}) = {round(tfidf, 3)}"
        }

class VSMSearcher:
    def __init__(self, index: InvertedIndex, documents: List[dict]):
        self.index = index
        self.documents = {doc['doc_id']: doc for doc in documents}
        self.doc_vectors: Dict[int, Dict[str, float]] = {}
        self.vocabulary: Set[str] = set(self.index.index.keys())
        self.build_doc_vectors()

    def _idf(self, term: str) -> float:
        df = len(self.index.lookup(term))
        if df == 0: return 0.0
        return math.log(self.index.total_docs / df)

    def build_doc_vectors(self):
        for doc_id, doc in self.documents.items():
            vec = {}
            tokens = doc.get('tokens', [])
            term_counts = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1
            
            for term, count in term_counts.items():
                tf = count / len(tokens)
                idf = self._idf(term)
                vec[term] = tf * idf
            
            # Normalize vector
            norm = math.sqrt(sum(v**2 for v in vec.values()))
            if norm > 0:
                for term in vec:
                    vec[term] /= norm
            self.doc_vectors[doc_id] = vec

    def query_vector(self, query_terms: List[str]) -> Dict[str, float]:
        vec = {}
        term_counts = {}
        for t in query_terms:
            term_counts[t] = term_counts.get(t, 0) + 1
        
        for term, count in term_counts.items():
            if term in self.vocabulary:
                tf = count / len(query_terms)
                idf = self._idf(term)
                vec[term] = tf * idf
        
        # Normalize
        norm = math.sqrt(sum(v**2 for v in vec.values()))
        if norm > 0:
            for term in vec:
                vec[term] /= norm
        return vec

    def cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        common_terms = set(vec_a.keys()).intersection(set(vec_b.keys()))
        return sum(vec_a[t] * vec_b[t] for t in common_terms)

    def search(self, query_terms: List[str], top_k=20) -> List[dict]:
        q_vec = self.query_vector(query_terms)
        if not q_vec:
            return []
            
        results = []
        for doc_id, d_vec in self.doc_vectors.items():
            score = self.cosine_similarity(q_vec, d_vec)
            if score > 0:
                results.append({
                    "doc_id": doc_id,
                    "cosine_similarity": score,
                    "document_vector": d_vec,
                    "title": self.documents[doc_id].get("title", "")
                })
        
        results.sort(key=lambda x: x["cosine_similarity"], reverse=True)
        return results[:top_k]

class BooleanSearcher:
    def __init__(self, index: InvertedIndex):
        self.index = index

    def evaluate(self, query_str: str, preprocess_func=None) -> Set[int]:
        import re
        tokens = re.findall(r'\(|\)|AND|OR|NOT|[\w]+', query_str)
        
        def precedence(op):
            if op == 'NOT': return 3
            if op == 'AND': return 2
            if op == 'OR': return 1
            return 0
            
        def apply_op(op, val2, val1=None):
            if op == 'NOT':
                return set(self.index.doc_lengths.keys()) - val2
            elif op == 'AND':
                return val1.intersection(val2)
            elif op == 'OR':
                return val1.union(val2)
            return set()

        # Shunting-yard algorithm simplified for boolean sets
        values = []
        ops = []
        
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t == '(':
                ops.append(t)
            elif t == ')':
                while ops and ops[-1] != '(':
                    op = ops.pop()
                    if op == 'NOT':
                        val = values.pop()
                        values.append(apply_op(op, val))
                    else:
                        val2 = values.pop()
                        val1 = values.pop()
                        values.append(apply_op(op, val2, val1))
                ops.pop()
            elif t in ['AND', 'OR', 'NOT']:
                while ops and precedence(ops[-1]) >= precedence(t):
                    op = ops.pop()
                    if op == 'NOT':
                        val = values.pop()
                        values.append(apply_op(op, val))
                    else:
                        val2 = values.pop()
                        val1 = values.pop()
                        values.append(apply_op(op, val2, val1))
                ops.append(t)
            else:
                # operand
                if preprocess_func:
                    # Apply preprocessing but keep only the first token if it splits
                    _, clean_tokens = preprocess_func(t)
                    t_clean = clean_tokens[0] if clean_tokens else t.lower()
                else:
                    t_clean = t.lower()
                docs = set(self.index.lookup(t_clean).keys())
                values.append(docs)
            i += 1
            
        while ops:
            op = ops.pop()
            if op == 'NOT':
                val = values.pop()
                values.append(apply_op(op, val))
            else:
                val2 = values.pop()
                val1 = values.pop()
                values.append(apply_op(op, val2, val1))
                
        return values[0] if values else set()

class PositionalSearcher:
    def __init__(self, index: InvertedIndex):
        self.index = index

    def phrase_search(self, phrase_terms: List[str]) -> List[int]:
        if not phrase_terms: return []
        if len(phrase_terms) == 1:
            return list(self.index.lookup(phrase_terms[0]).keys())

        # Initialize with documents containing the first term
        first_term = phrase_terms[0]
        docs_with_first = self.index.lookup(first_term)
        
        result_docs = []
        for doc_id, positions in docs_with_first.items():
            valid_starts = positions
            
            for i in range(1, len(phrase_terms)):
                term = phrase_terms[i]
                term_positions = self.index.lookup(term).get(doc_id, [])
                if not term_positions:
                    valid_starts = []
                    break
                    
                new_valid_starts = []
                for start_pos in valid_starts:
                    if (start_pos + i) in term_positions:
                        new_valid_starts.append(start_pos)
                valid_starts = new_valid_starts
                
                if not valid_starts:
                    break
            
            if valid_starts:
                result_docs.append(doc_id)
                
        return result_docs
