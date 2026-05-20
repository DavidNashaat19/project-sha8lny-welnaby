import httpx
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # free tier, ~0.5s response

SYSTEM_PROMPT = """You are a concise freelance market analyst.
Given search results from a freelance job platform, write exactly 2 sentences in the SAME LANGUAGE as the search query (Arabic if Arabic, English if English).
Sentence 1: What skills/technologies the market is currently demanding based on these results.
Sentence 2: Budget context — range and average if available, or note if budget data is limited.
Be specific. Use numbers. No bullet points. No headers. Max 60 words total."""

class MarketInsightEngine:
    async def generate(self, query: str, results: list[dict]) -> str:
        """
        query: user's search string
        results: top search results (list of job dicts)
        Returns: 2-sentence insight string, or "" on any failure.
        Never raises — always fails silently.
        """
        if not GROQ_API_KEY or not results:
            return ""

        # Build compact summary — never send full descriptions to API
        titles = [r.get("title", "") for r in results[:8]]
        budgets = [r["budget_extracted"] for r in results if r.get("budget_extracted")]
        all_skills = []
        for r in results[:10]:
            skills = r.get("skills") or r.get("inferred_skills") or []
            all_skills.extend(skills[:3])
        top_skills = list(dict.fromkeys(all_skills))[:8]  # deduplicated top 8

        budget_line = (
            f"Budget range: ${min(budgets):.0f}–${max(budgets):.0f}, "
            f"avg ${sum(budgets)/len(budgets):.0f}"
            if budgets else "Budget data not available for most results"
        )

        user_message = (
            f'Search query: "{query}"\n'
            f"Top job titles: {' | '.join(titles)}\n"
            f"Top skills mentioned: {', '.join(top_skills)}\n"
            f"{budget_line}\n"
            f"Total results: {len(results)}\n\n"
            f"Write the 2-sentence market insight now."
        )

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user",   "content": user_message},
                        ],
                        "max_tokens": 120,
                        "temperature": 0.4,
                    },
                )
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return ""  # fail silently — never break the search experience

market_insight_engine = MarketInsightEngine()
