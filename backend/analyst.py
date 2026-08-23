"""
AI Analyst — IBM Granite (watsonx.ai) + LangChain with rule-based fallback
"""


import json
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Base analyst interface
# ---------------------------------------------------------------------------

class BaseAnalyst:
    def analyze(self, question: str, site_data: Dict, selected_site_id: Optional[str] = None) -> Dict:
        raise NotImplementedError

# ---------------------------------------------------------------------------
# Rule-based fallback (no LLM required)
# ---------------------------------------------------------------------------

class RuleBasedAnalyst(BaseAnalyst):
    """
    Fallback analyst that uses structured rules and templates.
    Works offline — no API keys needed.
    """

    def analyze(self, question: str, site_data: Dict, selected_site_id: Optional[str] = None) -> Dict:
        question_lower = question.lower()

        # Extract site info from context
        sites = site_data.get("sites", [])
        mission = site_data.get("mission", "settlement")
        selected = next((s for s in sites if s.get("id") == selected_site_id), None)

        if "best" in question_lower or "why" in question_lower:
            return self._explain_best(selected, mission)
        elif "compare" in question_lower or "top" in question_lower:
            return self._compare_top(sites, mission)
        elif "risk" in question_lower or "danger" in question_lower:
            return self._assess_risk(selected, mission)
        else:
            return {
                "text": "I can analyze Mars sites across five dimensions: terrain safety, water access, solar potential, science value, and EDL safety. Ask me why a site is ranked here, what the risks are, or how it compares to others.",
                "sources": [],
                "model": "rule-based"
            }

    def _explain_best(self, site, mission: str) -> Dict:
        if not site:
            return {"text": "No site selected.", "sources": [], "model": "rule-based"}

        name = site.get("name", "Unknown")
        features = site.get("features", {})

        strengths = []
        if features.get("water", 0) >= 90:
            strengths.append("exceptional water ice accessibility")
        if features.get("terrain", 0) >= 85:
            strengths.append("safe, flat terrain")
        if features.get("solar", 0) >= 85:
            strengths.append("strong solar potential")
        if features.get("science", 0) >= 90:
            strengths.append("high scientific value")
        if features.get("edl", 0) >= 85:
            strengths.append("favorable entry-descent-landing conditions")

        weaknesses = []
        if features.get("water", 0) < 60:
            weaknesses.append("limited water access")
        if features.get("terrain", 0) < 70:
            weaknesses.append("challenging terrain")
        if features.get("solar", 0) < 75:
            weaknesses.append("reduced solar output")

        text = f"For a {mission} mission, {name} is highly rated. "
        if strengths:
            text += f"Key strengths: {', '.join(strengths)}. "
        if weaknesses:
            text += f"Watchpoints: {', '.join(weaknesses)}."

        return {"text": text, "sources": ["NASA MOLA Product Spec", "SHARAD Ice Detection Catalog"], "model": "rule-based"}

    def _compare_top(self, sites: List[Dict], mission: str) -> Dict:
        if len(sites) < 2:
            return {"text": "Need at least two sites to compare.", "sources": [], "model": "rule-based"}

        # Simple sort by water + terrain for demo
        sorted_sites = sorted(sites, key=lambda s: s.get("features", {}).get("water", 0) + s.get("features", {}).get("terrain", 0), reverse=True)[:2]

        text = f"Top 2 for {mission}:\n"
        for i, s in enumerate(sorted_sites, 1):
            text += f"{i}. {s.get('name')} — water: {s.get('features', {}).get('water')}, terrain: {s.get('features', {}).get('terrain')}\n"

        return {"text": text, "sources": ["RedSite AI scoring engine"], "model": "rule-based"}

    def _assess_risk(self, site, mission: str) -> Dict:
        if not site:
            return {"text": "No site selected.", "sources": [], "model": "rule-based"}

        name = site.get("name", "Unknown")
        features = site.get("features", {})

        risks = []
        if features.get("terrain", 0) < 75:
            risks.append("rough terrain may limit habitat placement")
        if features.get("water", 0) < 60:
            risks.append("water extraction will require deeper drilling")
        if features.get("edl", 0) < 75:
            risks.append("EDL corridor has higher uncertainty")
        if not risks:
            risks.append("primary risk is long-term dust accumulation on solar arrays")

        text = f"Risk assessment for {name}:\n• " + "\n• ".join(risks)
        return {"text": text, "sources": ["NASA Human Research Program"], "model": "rule-based"}

# ---------------------------------------------------------------------------
# IBM Granite analyst (requires watsonx.ai credentials)
# ---------------------------------------------------------------------------

class GraniteAnalyst(BaseAnalyst):
    """
    Production analyst powered by IBM Granite on watsonx.ai.
    Uses LangChain for structured tool calling and RAG.
    """

    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id
        self.model_name = "ibm/granite-13b-instruct-v2"
        self._init_llm()

    def _init_llm(self):
        try:
            from langchain_ibm import WatsonxLLM
            from langchain_core.prompts import ChatPromptTemplate

            self.llm = WatsonxLLM(
                model_id=self.model_name,
                url="https://us-south.ml.cloud.ibm.com",
                apikey=self.api_key,
                project_id=self.project_id,
                params={
                    "max_new_tokens": 512,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 50
                }
            )

            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """You are RedSite AI, a Mars mission planning analyst.
You have access to structured site data and NASA mission documentation.
Rules:
- Use ONLY the provided site data and NASA docs. Do not invent scientific facts.
- Be concise but technically accurate.
- If uncertain, say so rather than hallucinating.
- Cite sources when possible."""),
                ("human", "Question: {question}\n\nSite data: {site_data}\n\nNASA context: {context}")
            ])

            self.available = True
        except Exception as e:
            print(f"Warning: Could not initialize Granite LLM: {e}")
            self.available = False

    def analyze(self, question: str, site_data: Dict, selected_site_id: Optional[str] = None) -> Dict:
        if not self.available:
            # Graceful fallback
            fallback = RuleBasedAnalyst()
            result = fallback.analyze(question, site_data, selected_site_id)
            result["model"] = "rule-based (granite unavailable)"
            return result

        try:
            # Build structured context
            context = self._build_context(site_data, selected_site_id)

            # Run chain
            chain = self.prompt | self.llm
            response = chain.invoke({
                "question": question,
                "site_data": json.dumps(context.get("sites", [])),
                "context": json.dumps(context.get("nasa_docs", []))
            })

            return {
                "text": response,
                "sources": ["NASA MOLA", "SHARAD Catalog", "NASA Mission Docs"],
                "model": self.model_name
            }
        except Exception as e:
            # Fallback on any error
            fallback = RuleBasedAnalyst()
            result = fallback.analyze(question, site_data, selected_site_id)
            result["model"] = f"rule-based (granite error: {str(e)[:50]})"
            return result

    def _build_context(self, site_data: Dict, selected_site_id: Optional[str]) -> Dict:
        """Build structured context for the LLM from site data."""
        sites = site_data.get("sites", [])
        selected = next((s for s in sites if s.get("id") == selected_site_id), None)

        context = {
            "sites": sites,
            "selected_site": selected,
            "nasa_docs": [
                "MOLA DEM Product Specification — NASA PDS",
                "SHARAD Ice Detection Catalog — WUSTL",
                "Mars Landing Site Selection Criteria — NASA Engineering Constraints"
            ]
        }
        return context
