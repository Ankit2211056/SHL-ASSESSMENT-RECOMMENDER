import os
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI

from shl_catalog import shl_products, SHLProduct

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SHLConsultantFastAPI")

# Initialize FastAPI
app = FastAPI(
    title="SHL Assessment Consultant Service",
    description="An AI consultant that helps configure and match SHL evaluations for job roles.",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Groq Client (OpenAI-compatible API, generous free tier)
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    logger.warning("GROQ_API_KEY environment variable not set. Please set it before sending chat queries.")

try:
    ai_client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )
except Exception as e:
    logger.error(f"Failed to initialize Groq Client: {e}")
    ai_client = None

GROQ_MODEL = "llama-3.3-70b-versatile"

# Request and Response schemas
class Message(BaseModel):
    role: str  # "user" or "model" / "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class RecommendationItem(BaseModel):
    name: str
    url: str
    test_type: str

class ChatResponse(BaseModel):
    reply: str
    recommendations: List[RecommendationItem] = []
    end_of_conversation: bool = False
    slots: Optional[Dict[str, Any]] = None

@app.get("/health")
@app.get("/api/health")
def health_check():
    """Health check endpoint for container readiness."""
    return {"status": "ok"}

@app.get("/")
def read_root():
    """Serves the static single-page application."""
    return FileResponse("index.html")

@app.get("/api/catalog")
def get_catalog():
    """Returns the SHL product catalog from python."""
    return [p.dict() for p in shl_products]

PRODUCT_TEST_TYPE_MAPPING = {
    "opq32r": "P",
    "opq-ucr-2": "P",
    "opq-leadership-report": "P",
    "smart-interview-live-coding": "K",
    "linux-programming-general": "K",
    "networking-implementation-new": "K",
    "shl-verify-interactive-g": "A",
    "svar-spoken-english-us-new": "K",
    "contact-center-call-simulation-new": "S",
    "entry-level-customer-serv-retail": "P,C",
    "customer-service-phone-simulation": "B,S",
    "shl-verify-interactive-numerical": "A,S",
    "financial-accounting-new": "K",
    "basic-statistics-new": "K",
    "graduate-scenarios": "B",
    "global-skills-assessment": "C, K",
    "global-skills-development-report": "D",
    "opq-mq-sales-report": "P",
    "salestransformationreport2-0-ic": "P",
    "dependability-and-safety-instrument-dsi": "P",
    "safety-and-dependability-focus-8-0": "P",
    "workplace-health-and-safety-new": "K",
    "hipaa-security": "K",
    "medical-terminology-new": "K",
    "microsoft-word-365-essentials-new": "K,S",
    "ms-excel-new": "K",
    "ms-word-new": "K",
    "microsoft-excel-365-new": "K,S",
    "microsoft-word-365-new": "K,S",
    "core-java-advanced-level-new": "K",
    "spring-new": "K",
    "restful-web-services-new": "K",
    "sql-new": "K",
    "amazon-web-services-aws-development-new": "K",
    "docker-new": "K",
}

def get_test_type_code(type_str: str) -> str:
    """Maps a catalog product's `type` field to its short SHL test-type code
    (K=Knowledge&Skills, P=Personality, A=Ability&Aptitude, S=Simulations,
    B=Biodata&SituationalJudgment, C=Competencies, D=Development&360, E=AssessmentExercises).
    Falls back to 'K' only if the type is genuinely unrecognized."""
    mapping = {
        "ability & aptitude": "A",
        "knowledge & skills": "K",
        "personality & behavior": "P",
        "simulations": "S",
        "biodata & situational judgment": "B",
        "competencies": "C",
        "development & 360": "D",
        "assessment exercises": "E",
    }
    if not type_str:
        return "K"
    return mapping.get(type_str.strip().lower(), "K")

def run_advisor(conversation_text: str) -> Dict[str, Any]:
    """Uses a single unified Groq (Llama 3.3 70B) call to determine intent, slots, text reply, and recommendations."""
    if not ai_client:
        return {
            "reply": "I am unable to connect to the assessment advisor service. Please check your configuration.",
            "recommended_product_ids": [],
            "end_of_conversation": False,
            "slots": {
                "role": "",
                "seniority": "",
                "skills": [],
                "testType": "",
                "intent": "CLARIFY",
                "selectedProductsForComparison": [],
                "isConfirmed": False
            }
        }

    # Format catalog as text
    catalog_text = ""
    for p in shl_products:
        catalog_text += f"- ID: {p.id}\n"
        catalog_text += f"  Name: {p.name}\n"
        catalog_text += f"  Type: {p.type}\n"
        catalog_text += f"  Description: {p.description}\n"
        catalog_text += f"  Duration: {p.duration}\n"
        catalog_text += f"  Job Levels: {', '.join(p.jobLevels)}\n"
        catalog_text += f"  Target Roles: {', '.join(p.targetRoles)}\n"
        catalog_text += f"  Skills: {', '.join(p.skills)}\n"
        catalog_text += f"  Languages: {', '.join(p.languages)}\n\n"

    prompt = f"""You are an elite SHL Assessment Consultant Expert System. Your goal is to guide clients to build the perfect shortlist of SHL assessment products for their hiring, reskilling, or talent auditing needs.

### STRICT CATALOG GROUNDING
You must ONLY recommend products that exist in our official catalog. Do not invent any new products, versions, durations, or URLs. Here is our official catalog of products:
{catalog_text}

### CONVERSATION STRATEGY (generic rules, not scripted):

You gather four things over the conversation before recommending: **role/title**, **seniority**, **key skills or focus areas**, and **any test-type preference** (technical, personality, cognitive, behavioral, simulation). You do not need all four in one turn, and you do not need to ask about things the user already told you or said they don't care about.

- **Clarify**: If the user's message is too vague to select from (e.g. just "I need an assessment" or a bare job title with no context), ask ONE focused follow-up question. Do not recommend yet (`recommended_product_ids` = []).
- **Recommend**: Once you have enough signal (role + at least one of seniority/skills/test-type, or a detailed job description), search the catalog above for the best-matching products by overlapping skills, target roles, job levels, and test type, and propose a shortlist (1-10 items). Briefly explain your reasoning in `reply`.
- **Refine**: If the user adds, removes, or changes a constraint ("also add personality", "drop the SQL test", "actually make it senior level"), update the existing shortlist accordingly — do not discard prior context or start over.
- **Compare**: If the user asks how two products differ, answer using ONLY the descriptions/attributes given in the catalog above. Do not invent distinctions. If comparing, keep `recommended_product_ids` as whatever the currently agreed shortlist is (don't wipe it) unless the user is still deciding.
- **Confirm / end**: When the user signals they are satisfied ("that works", "confirmed", "lock it in", "good"), keep the current shortlist and set `end_of_conversation` = true.
- **No match**: If the catalog has no good match for what's being asked (e.g. a niche language/tool with no dedicated test), say so honestly, suggest the closest available alternatives, and do not fabricate a product.
- **Turn budget**: The conversation is capped at 8 turns total. Don't drag out clarification for more than 1-2 questions before proposing something — converge to a shortlist reasonably quickly.

### OFF-TOPIC REFUSAL RULE:
If the user's latest query is completely unrelated to hiring, SHL evaluations, or talent assessment (e.g., asking for programming syntax help, recipes, random trivia, general-purpose questions), politely refuse to answer, guide them back to SHL, and return `[]` for `recommended_product_ids` with `end_of_conversation` = false.

### CONVERSATION HISTORY (Full context):
{conversation_text}

You MUST respond with a valid JSON object matching this schema. Make sure to populate the slot values based on the conversation history:
{{
  "reply": "Your professional conversational reply here. Write in the tone of an expert SHL consultant. Do not include markdown tables in the reply — the user will see the recommended tests in a clean sidebar/table rendered by the app.",
  "recommended_product_ids": ["id_from_catalog_1", "id_from_catalog_2", ...],
  "end_of_conversation": true/false,
  "slots": {{
    "role": "The target job role",
    "seniority": "The seniority level",
    "skills": ["skill1", "skill2"],
    "testType": "preferred test type",
    "intent": "OFF_TOPIC", "COMPARE", "CLARIFY", or "RECOMMEND",
    "selectedProductsForComparison": ["id1", "id2", ...],
    "isConfirmed": true/false
  }}
}}
"""

    try:
        response = ai_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a strict JSON API. Always respond with ONLY a single valid JSON object matching the schema given in the user prompt. No markdown, no code fences, no explanation text outside the JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        # Parse result safely
        raw_text = response.choices[0].message.content.strip()
        parsed = json.loads(raw_text)
        logger.info(f"Advisor generated output: {parsed}")
        return parsed
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in running advisor: {e}\n{tb}")
        try:
            with open("error_trace.log", "w") as f:
                f.write(f"Error: {e}\nTraceback:\n{tb}")
        except Exception as write_err:
            logger.error(f"Failed to write error log: {write_err}")
        return {
            "reply": "I apologize, but I had trouble processing your request. Could you please specify your target job role and the core skills you want to evaluate?",
            "recommended_product_ids": [],
            "end_of_conversation": False,
            "slots": {
                "role": "",
                "seniority": "",
                "skills": [],
                "testType": "",
                "intent": "CLARIFY",
                "selectedProductsForComparison": [],
                "isConfirmed": False
            }
        }

@app.post("/chat")
@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Stateless multi-turn agent handler matching candidates to SHL tests."""
    if not ai_client:
        raise HTTPException(
            status_code=500,
            detail="Groq API Client is not configured. Please set the GROQ_API_KEY environment variable."
        )

    try:
        messages = request.messages

        # Format conversation context
        conversation_text = ""
        for m in messages:
            sender = "User" if m.role == "user" else "Consultant"
            conversation_text += f"{sender}: {m.content}\n"

        # Run advisor model
        advisor_output = run_advisor(conversation_text)

        reply = advisor_output.get("reply", "")
        recommended_ids = advisor_output.get("recommended_product_ids", [])
        end_of_conversation = advisor_output.get("end_of_conversation", False)
        slots = advisor_output.get("slots", None)

        # Map IDs to actual SHL products
        recs_list = []
        for pid in recommended_ids:
            # Find in catalog
            prod = next((p for p in shl_products if p.id == pid), None)
            if prod:
                test_type_code = PRODUCT_TEST_TYPE_MAPPING.get(prod.id, get_test_type_code(prod.type))
                recs_list.append(
                    RecommendationItem(
                        name=prod.name,
                        url=prod.url,
                        test_type=test_type_code
                    )
                )

        return ChatResponse(
            reply=reply,
            recommendations=recs_list,
            end_of_conversation=end_of_conversation,
            slots=slots
        )

    except Exception as e:
        logger.error(f"Error handling chat query: {e}")
        return ChatResponse(
            reply="I encountered an error while matching SHL assessments. Let's try matching again based on your job role and key competencies.",
            recommendations=[],
            end_of_conversation=False,
            slots={
                "role": "",
                "seniority": "",
                "skills": [],
                "testType": "",
                "intent": "RECOMMEND",
                "selectedProductsForComparison": [],
                "isConfirmed": False
            }
        )

if __name__ == "__main__":
    import uvicorn
    # Port 3000 is mapped for container ingress routing
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
