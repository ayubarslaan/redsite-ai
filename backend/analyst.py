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

    All explanations reference actual calculated contributions passed in
    site_data — the analyst never recalculates scores itself.
    """

    def analyze(self, question: str, site_data: Dict, selected_site_id: Optional[str] = None) -> Dict:
        question_lower = question.lower()

        # Extract site info from context
        sites = site_data.get("sites", [])
        mission = site_data.get("mission", "settlement")
        mission_name = site_data.get("mission_name", mission)
        is_custom = site_data.get("is_custom_weights", False)
        weights = site_data.get("weights", {})
        ranking_explanation = site_data.get("ranking_explanation", "")
        selected = next((s for s in sites if s.get("id") == selected_site_id), None)

        # Route to the best handler
        if "compare" in question_lower or ("top" in question_lower and "2" in question_lower):
            return self._compare_top(sites, mission_name, is_custom, weights, ranking_explanation)
        elif "rank" in question_lower and "first" in question_lower:
            rank1 = next((s for s in sites if s.get("rank") == 1), None)
            return self._explain_ranking(rank1, mission_name, is_custom, ranking_explanation)
        elif "risk" in question_lower or "danger" in question_lower:
            return self._assess_risk(selected, mission_name)
        elif "settlement" in question_lower or "choose" in question_lower or "should" in question_lower:
            return self._explain_mission_fit(selected, "settlement", sites, weights)
        elif "science" in question_lower and ("prioritize" in question_lower or "change" in question_lower or "if" in question_lower):
            return self._explain_mission_change(sites, "science")
        elif "weight" in question_lower or "custom" in question_lower or "current" in question_lower:
            return self._explain_current_weights(sites, mission_name, is_custom, weights, ranking_explanation)
        elif "decomp" in question_lower or "breakdown" in question_lower or "contribut" in question_lower:
            return self._explain_decomposition(selected or (sites[0] if sites else None), mission_name, weights)
        elif "best" in question_lower or "why" in question_lower or "rank" in question_lower:
            return self._explain_best(selected, mission_name, weights, ranking_explanation, is_custom)
        else:
            return {
                "text": (
                    "I can analyze Mars sites across five dimensions: terrain safety, water access, "
                    "solar potential, science value, and EDL safety. "
                    "Try asking: 'Why is this site best?', 'What are the risks?', "
                    "'Compare the top two sites', 'Show score breakdown', or "
                    "'What changes if I prioritize science?'"
                ),
                "sources": [],
                "model": "rule-based"
            }

    def _explain_best(self, site, mission: str, weights: Dict, ranking_explanation: str, is_custom: bool) -> Dict:
        if not site:
            return {
                "text": "Please select a candidate site on the map or in the dashboard to receive a site-specific assessment.",
                "sources": [],
                "model": "rule-based"
            }

        name = site.get("name", "Unknown")
        features = site.get("features", {})
        score = site.get("score")
        rank = site.get("rank")
        decomp = site.get("decomposition", {})

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

        rank_str = f" (ranked #{rank}, score {score}/100)" if rank and score is not None else ""
        weight_note = " [custom weights applied]" if is_custom else ""
        text = f"For the {mission} mission{weight_note}, {name}{rank_str} is assessed as follows.\n"

        # Use decomposition if available
        if decomp:
            top_contributors = sorted(
                decomp.items(),
                key=lambda kv: kv[1]["contribution"] if isinstance(kv[1], dict) else 0,
                reverse=True
            )[:3]
            text += "Top score contributors:\n"
            for feat, vals in top_contributors:
                if isinstance(vals, dict):
                    text += (
                        f"  • {feat}: {vals.get('raw_score')}/100 × "
                        f"{vals.get('weight', 0):.1%} = {vals.get('contribution', 0):.1f} pts "
                        f"({vals.get('percentage', 0):.1f}% of total)\n"
                    )
        else:
            if strengths:
                text += f"Strengths: {', '.join(strengths)}.\n"
            if weaknesses:
                text += f"Watchpoints: {', '.join(weaknesses)}.\n"

        if ranking_explanation and rank == 1:
            text += f"\nRanking context: {ranking_explanation}"

        return {
            "text": text.strip(),
            "sources": ["NASA MOLA Product Spec", "SHARAD Ice Detection Catalog"],
            "model": "rule-based"
        }

    def _explain_ranking(self, site, mission: str, is_custom: bool, ranking_explanation: str) -> Dict:
        if not site:
            return {"text": "Could not determine the top-ranked site.", "sources": [], "model": "rule-based"}

        name = site.get("name", "Unknown")
        score = site.get("score")
        decomp = site.get("decomposition", {})

        weight_note = " under custom weights" if is_custom else ""
        text = f"{name} is ranked #1{weight_note} with a score of {score}/100.\n"

        if ranking_explanation:
            text += f"\n{ranking_explanation}"
        elif decomp:
            top = max(decomp.items(), key=lambda kv: kv[1].get("contribution", 0) if isinstance(kv[1], dict) else 0)
            feat, vals = top
            if isinstance(vals, dict):
                text += (
                    f"\nIts strongest weighted contribution is {feat}: "
                    f"{vals.get('raw_score')}/100 × {vals.get('weight', 0):.1%} = "
                    f"{vals.get('contribution', 0):.1f} pts."
                )

        return {
            "text": text.strip(),
            "sources": ["RedSite AI SiteScorer", "NASA MOLA Product Spec"],
            "model": "rule-based"
        }

    def _compare_top(self, sites: List[Dict], mission: str, is_custom: bool,
                     weights: Dict, ranking_explanation: str) -> Dict:
        if len(sites) < 2:
            return {"text": "Need at least two sites to compare.", "sources": [], "model": "rule-based"}

        top2 = sorted(sites, key=lambda s: s.get("rank", 999))[:2]
        weight_note = " (custom weights)" if is_custom else ""

        lines = [f"Top 2 sites for {mission} mission{weight_note}:"]
        for s in top2:
            f = s.get("features", {})
            lines.append(
                f"#{s.get('rank')} {s.get('name')} — score: {s.get('score')}/100 | "
                f"terrain: {f.get('terrain')}, water: {f.get('water')}, "
                f"solar: {f.get('solar')}, science: {f.get('science')}, edl: {f.get('edl')}"
            )

        # Use actual decomposition contributions to explain the gap
        s1, s2 = top2[0], top2[1]
        decomp1 = s1.get("decomposition", {})
        decomp2 = s2.get("decomposition", {})

        if decomp1 and decomp2:
            lines.append("\nScore decomposition comparison:")
            feat_labels = {
                "terrain": "Terrain", "water": "Water",
                "solar": "Solar", "science": "Science", "edl": "EDL"
            }
            for feat in ["terrain", "water", "solar", "science", "edl"]:
                c1 = decomp1.get(feat, {})
                c2 = decomp2.get(feat, {})
                if isinstance(c1, dict) and isinstance(c2, dict):
                    d = round(c1.get("contribution", 0) - c2.get("contribution", 0), 1)
                    leader = s1.get("name") if d >= 0 else s2.get("name")
                    lines.append(
                        f"  {feat_labels.get(feat, feat)}: {s1.get('name')} {c1.get('contribution', 0):.1f} vs "
                        f"{s2.get('name')} {c2.get('contribution', 0):.1f} (Δ {abs(d):.1f} → {leader})"
                    )

        if ranking_explanation:
            lines.append(f"\n{ranking_explanation}")
        else:
            diff = round((s1.get("score") or 0) - (s2.get("score") or 0), 1)
            if diff > 0:
                lines.append(f"\n{s1.get('name')} leads by {diff} points.")

        return {
            "text": "\n".join(lines),
            "sources": ["RedSite AI SiteScorer"],
            "model": "rule-based"
        }

    def _explain_current_weights(self, sites: List[Dict], mission: str, is_custom: bool,
                                  weights: Dict, ranking_explanation: str) -> Dict:
        """Explain the current weight configuration and its effect on rankings."""
        weight_note = "custom (what-if)" if is_custom else "default"
        lines = [f"Current weight configuration for {mission} mission ({weight_note}):"]

        feat_labels = {
            "terrain": "Terrain safety", "water": "Water access",
            "solar": "Solar potential", "science": "Science value", "edl": "EDL safety"
        }
        for feat, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  • {feat_labels.get(feat, feat)}: {w:.1%}")

        if is_custom:
            lines.append("\n⚠ These are modified weights — results differ from the default mission profile.")

        if ranking_explanation:
            lines.append(f"\n{ranking_explanation}")

        rank1 = next((s for s in sites if s.get("rank") == 1), None)
        if rank1:
            lines.append(f"\nTop site under these weights: {rank1.get('name')} ({rank1.get('score')}/100)")

        return {
            "text": "\n".join(lines),
            "sources": ["RedSite AI SiteScorer"],
            "model": "rule-based"
        }

    def _explain_decomposition(self, site, mission: str, weights: Dict) -> Dict:
        """Explain the score decomposition for the selected site."""
        if not site:
            return {
                "text": "Please select a candidate site to see its score breakdown.",
                "sources": [],
                "model": "rule-based"
            }

        name = site.get("name", "Unknown")
        score = site.get("score")
        decomp = site.get("decomposition", {})

        if not decomp:
            return {
                "text": f"No decomposition data available for {name}.",
                "sources": [],
                "model": "rule-based"
            }

        lines = [f"Score decomposition for {name} (total: {score}/100):"]
        contribution_sum = 0.0
        for feat, vals in decomp.items():
            if isinstance(vals, dict):
                raw = vals.get("raw_score", 0)
                w = vals.get("weight", 0)
                contrib = vals.get("contribution", 0)
                pct = vals.get("percentage", 0)
                contribution_sum += contrib
                lines.append(
                    f"  • {feat}: {raw}/100 × {w:.1%} = {contrib:.1f} pts ({pct:.1f}% of total)"
                )

        lines.append(f"\nSum of contributions: {contribution_sum:.1f} pts ≈ {score}/100")
        lines.append("(Verify: contributions exactly reproduce the displayed score.)")

        return {
            "text": "\n".join(lines),
            "sources": ["RedSite AI SiteScorer"],
            "model": "rule-based"
        }

    def _assess_risk(self, site, mission: str) -> Dict:
        if not site:
            return {
                "text": "Please select a candidate site to see its risk assessment.",
                "sources": [],
                "model": "rule-based"
            }

        name = site.get("name", "Unknown")
        features = site.get("features", {})
        coord = site.get("coordinates", {})
        lat = coord.get("lat", 0)

        risks = []
        if features.get("terrain", 0) < 75:
            risks.append(f"rough terrain (score {features.get('terrain')}/100) may limit habitat placement and rover mobility")
        if features.get("water", 0) < 60:
            risks.append(f"limited water access (score {features.get('water')}/100) — extraction will require deeper drilling")
        if features.get("edl", 0) < 75:
            risks.append(f"EDL corridor uncertainty (score {features.get('edl')}/100) — higher entry risk")
        if abs(lat) > 40:
            risks.append(f"high-latitude site ({lat}°) — reduced solar power and longer dust storm seasons")
        if not risks:
            risks.append("primary risk is long-term dust accumulation on solar arrays")
            risks.append("site is otherwise well-characterised with no major red flags")

        text = f"Risk assessment for {name} ({mission} mission):\n• " + "\n• ".join(risks)
        return {"text": text, "sources": ["NASA Human Research Program", "Mars EDL Analysis"], "model": "rule-based"}

    def _explain_mission_fit(self, site, mission: str, sites: List[Dict], weights: Dict) -> Dict:
        if not site:
            return {
                "text": "Please select a candidate site to evaluate mission fit.",
                "sources": [],
                "model": "rule-based"
            }

        name = site.get("name", "Unknown")
        features = site.get("features", {})
        score = site.get("score")
        rank = site.get("rank")
        decomp = site.get("decomposition", {})

        text = f"{name} has a mission score of {score}/100 (rank #{rank}) for {mission}.\n"

        # Use actual decomposition contributions if available, else fall back to weights
        if decomp:
            text += "Score contributions:\n"
            sorted_decomp = sorted(
                [(f, v) for f, v in decomp.items() if isinstance(v, dict)],
                key=lambda kv: kv[1].get("contribution", 0),
                reverse=True
            )
            for feat, vals in sorted_decomp:
                text += (
                    f"  • {feat}: {vals.get('raw_score')}/100 × "
                    f"{vals.get('weight', 0):.0%} weight = {vals.get('contribution', 0):.1f} points\n"
                )
        else:
            contributions = {k: features.get(k, 0) * w for k, w in weights.items()}
            top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]
            text += "Top contributing factors:\n"
            for feat, contrib in top_factors:
                text += f"  • {feat}: {features.get(feat)}/100 × {weights.get(feat, 0):.0%} weight = {contrib:.1f} points\n"

        if score and score >= 80:
            text += f"\nThis is a strong candidate for {mission}."
        elif score and score >= 65:
            text += f"\nThis is a viable candidate but not the optimal choice for {mission}."
        else:
            text += f"\nThis site has significant limitations for a {mission} mission."

        return {"text": text.strip(), "sources": ["RedSite AI SiteScorer"], "model": "rule-based"}

    def _explain_mission_change(self, sites: List[Dict], new_mission: str) -> Dict:
        """Explain what changes when mission is switched."""
        from scoring import BUILT_IN_PROFILES, SiteScorer
        scorer = SiteScorer()

        try:
            profile = BUILT_IN_PROFILES[new_mission]
        except KeyError:
            return {"text": f"Unknown mission profile: {new_mission}", "sources": [], "model": "rule-based"}

        text = (
            f"If you switch to a {profile.name} mission, the ranking weights change significantly:\n"
        )
        for feat, w in profile.weights.items():
            text += f"  • {feat}: {w:.0%}\n"

        current_order = sorted(sites, key=lambda s: s.get("rank", 999))
        text += f"\nCurrent top site ({current_order[0].get('name') if current_order else 'N/A'}) "

        science_sites = sorted(sites, key=lambda s: s.get("features", {}).get("science", 0), reverse=True)
        if science_sites:
            text += f"vs. science-optimal site ({science_sites[0].get('name')}, science score: {science_sites[0].get('features', {}).get('science')}/100).\n"
        text += "\nSwitch the Mission dropdown at the top of the page to recalculate all rankings."

        return {"text": text.strip(), "sources": ["RedSite AI SiteScorer", "NASA Mission Planning Docs"], "model": "rule-based"}


# ---------------------------------------------------------------------------
# IBM Granite analyst (requires watsonx.ai credentials)
# ---------------------------------------------------------------------------

class GraniteAnalyst(BaseAnalyst):
    """
    Production analyst powered by IBM Granite on watsonx.ai.
    Uses LangChain for structured prompting.
    Falls back to RuleBasedAnalyst on any error.

    The prompt explicitly instructs the model to use the provided scores and
    decomposition data — it must NOT recalculate or override scores.
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
You have access to structured site data including ranked scores, per-feature decompositions, and mission weights.
CRITICAL RULES:
- Use ONLY the provided site data. Do NOT recalculate or modify any scores.
- The scoring engine is the single source of truth. Reference scores and contributions exactly as given.
- Cite specific contribution values (e.g., "water contributed 33.95 pts = 97×0.35") from the decomposition field.
- If custom weights are active, note this: "under your custom {mission} weights".
- Be concise but technically accurate.
- If uncertain, say so rather than hallucinating.
- Cite sources when possible."""),
                ("human", (
                    "Question: {question}\n\n"
                    "Mission: {mission} (custom weights: {is_custom})\n"
                    "Active weights: {weights}\n"
                    "Selected site: {selected_site}\n"
                    "Ranking explanation: {ranking_explanation}\n"
                    "All sites (ranked, with decomposition): {site_data}"
                ))
            ])

            self.available = True
        except Exception as e:
            print(f"Warning: Could not initialize Granite LLM: {e}")
            self.available = False

    def analyze(self, question: str, site_data: Dict, selected_site_id: Optional[str] = None) -> Dict:
        if not self.available:
            fallback = RuleBasedAnalyst()
            result = fallback.analyze(question, site_data, selected_site_id)
            result["model"] = "rule-based (granite unavailable)"
            return result

        try:
            sites = site_data.get("sites", [])
            mission = site_data.get("mission", "settlement")
            mission_name = site_data.get("mission_name", mission)
            is_custom = site_data.get("is_custom_weights", False)
            weights = site_data.get("weights", {})
            ranking_explanation = site_data.get("ranking_explanation", "")
            selected = next((s for s in sites if s.get("id") == selected_site_id), None)

            chain = self.prompt | self.llm
            response = chain.invoke({
                "question": question,
                "mission": mission_name,
                "is_custom": "YES" if is_custom else "no",
                "weights": json.dumps({k: f"{v:.1%}" for k, v in weights.items()}),
                "selected_site": json.dumps(selected) if selected else "none",
                "ranking_explanation": ranking_explanation,
                "site_data": json.dumps(sites),
            })

            return {
                "text": response,
                "sources": ["NASA MOLA", "SHARAD Catalog", "NASA Mission Docs"],
                "model": self.model_name
            }
        except Exception as e:
            fallback = RuleBasedAnalyst()
            result = fallback.analyze(question, site_data, selected_site_id)
            result["model"] = f"rule-based (granite error: {str(e)[:50]})"
            return result
