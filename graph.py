# graph.py
from langgraph.graph import StateGraph, END
from tools import extract_text_from_docx,extract_text_from_pdf, chunk_text, store_embeddings_in_chromadb, rag_search, lead_gen, generate_with_gpt
import chromadb
from typing import TypedDict, List, Dict, Any
from openai import OpenAI
from langgraph.graph import StateGraph, START, END
from calendly_tool import schedule_calendly_meeting
import dateparser
from datetime import datetime, timedelta
import os
import time
import regex as re
import pytz



from chromadb import PersistentClient
chroma_client = PersistentClient(path="db")

client = OpenAI(api_key="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")




class RAGState(TypedDict, total=False):
    file_path: str
    content: str
    chunks_ingested: int
    docs: List[Dict[str, Any]]
    


class queryState(TypedDict, total=False):
    query: str
    answer: str

class LeadState(TypedDict, total=False):
    name:str
    mob:int
    query: str



class SchedulerSlots(TypedDict, total=False):
    """
    TypedDict for storing scheduling info (multi-turn slot filling)
    """
    name: str
    email: str
    start_time: str # ISO 8601 UTC format
    duration_minutes: int
    location: str


# Initialize graph
graph = StateGraph(RAGState)






def extract_slots_llm(user_input: str) -> SchedulerSlots:
    """
    Uses GPT-4o to extract name, email, start_time from natural language.
    Returns a SchedulerSlots dict with extracted values or None if missing.
    """
    prompt = f"""
Extract the following information from the user's message.
Return JSON only. If information is missing, set it to null.

Fields:
- name
- email
- start_time (natural language is fine, e.g., 'tomorrow 4 PM IST')

User message: "{user_input}"
"""
    print("In extract_slots_llm...\n")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        import json
        data = json.loads(response.choices[0].message.content)
        return SchedulerSlots(
            name=data.get("name"),
            email=data.get("email"),
            start_time=data.get("start_time")
        )
    except Exception:
        # fallback in case of parse error
        return SchedulerSlots()

IST = pytz.timezone("Asia/Kolkata")

def parse_start_time(text: str):
    text = text.lower().strip()

    # Already ISO (assume UTC)
    if "t" in text and text.endswith("z"):
        return text

    now_ist = datetime.now(IST)

    # Day resolution
    if "tomorrow" in text:
        base_date = now_ist + timedelta(days=1)
    elif "today" in text:
        base_date = now_ist
    else:
        return None

    # Time extraction (supports 2pm, 2:30 pm, 14:30)
    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2)) if match.group(2) else 0
    meridian = match.group(3)

    if meridian == "pm" and hour != 12:
        hour += 12
    if meridian == "am" and hour == 12:
        hour = 0

    ist_dt = base_date.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    utc_dt = ist_dt.astimezone(pytz.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# def scheduler_node(
#     user_message: str,
#     scheduler_slots: dict = None,
#     user_name: str = None,
#     user_mobile: str = None
# ) -> dict:
#     """
#     Multi-turn Calendly scheduling node:
#     - Extracts info from user input
#     - Fills missing slots
#     - Calls Calendly tool when all required info is collected
#     Returns:
#         {
#             "response": str,            # Bot reply to user
#             "scheduler_slots": dict,    # Updated slots
#             "done": bool                # True if appointment scheduled
#         }
#     """
#     print("In scheduler_node...\n")
#     if scheduler_slots is None:
#         scheduler_slots = SchedulerSlots()

#     # Ensure default keys exist
#     for key in ["name", "email", "start_time"]:
#         if key not in scheduler_slots:
#             scheduler_slots[key] = None
#     # if scheduler_slots["duration_minutes"] is None:
#     #     scheduler_slots["duration_minutes"] = 30  # default duration

#     # Step 1: Extract slots from user input using LLM
#     extracted_slots = extract_slots_llm(user_message)
#     for key in ["name", "email"]:
#         if not scheduler_slots.get(key) and extracted_slots.get(key):
#             scheduler_slots[key] = extracted_slots[key]

#     # Step 1b: Handle start_time conversion
#     if not scheduler_slots.get("start_time") and extracted_slots.get("start_time"):
#         iso_time = parse_start_time(extracted_slots["start_time"])
#         scheduler_slots["start_time"] = iso_time

#     # Also parse user_message if responding to missing start_time prompt
#     if not scheduler_slots.get("start_time"):
#         iso_time = parse_start_time(user_message)
#         if iso_time:
#             scheduler_slots["start_time"] = iso_time

#     # Step 2: Check for missing slots
#     missing_slots = [k for k in ["name", "email", "start_time"] if not scheduler_slots.get(k)]
#     if missing_slots:
#         next_question = {
#             "name": "May I know your name?",
#             "email": "Can I have your email address?",
#             "start_time": "What date and time works best for you?"
#         }
#         return {"response": next_question[missing_slots[0]], "scheduler_slots": scheduler_slots, "done": False}

#     # Step 3: All required slots filled → call Calendly tool
#     result = schedule_calendly_meeting(
#         event_type_uri="https://api.calendly.com/event_types/3677b0d0-1e8d-458e-98ea-575bb00c1cb0",
#         name=scheduler_slots["name"],
#         email=scheduler_slots["email"],
#         start_time=scheduler_slots["start_time"]
#     )

#     # Step 4: Generate bot reply
#     if result.get("success"):
#         response = result.get("message", "Your call has been scheduled successfully!")
#     else:
#         response = f"Oops! Could not schedule the call. {result.get('message', '')}"

#     return {"response": response, "scheduler_slots": scheduler_slots, "done": True}




def extract_email_regex(text: str):
    match = re.search(
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        text
    )
    return match.group(0) if match else None






def scheduler_node(
    user_message: str,
    scheduler_slots: Dict = None,
    user_name: str = None
) -> Dict:
    """
    Multi-turn scheduling node (Calendly)

    Required slots:
    - name
    - email
    - start_time

    Returns:
    {
        "response": str,
        "scheduler_slots": dict,
        "done": bool
    }
    """

    print("In scheduler_node...\n")

    # ----------------------------
    # Initialize state safely
    # ----------------------------
    if scheduler_slots is None or not isinstance(scheduler_slots, dict):
        scheduler_slots = {}

    for key in ["name", "email", "start_time"]:
        scheduler_slots.setdefault(key, None)

    # ----------------------------
    # Pre-fill name if already known
    # ----------------------------
    if not scheduler_slots["name"] and user_name:
        scheduler_slots["name"] = user_name

    # ----------------------------
    # Slot extraction (deterministic)
    # ----------------------------
    if not scheduler_slots["email"]:
        email = extract_email_regex(user_message)
        if email:
            scheduler_slots["email"] = email

    if not scheduler_slots["start_time"]:
        parsed_time = parse_start_time(user_message)
        if parsed_time:
            scheduler_slots["start_time"] = parsed_time

    if not scheduler_slots["name"]:
        # Short messages assumed as name
        if len(user_message.split()) <= 3:
            scheduler_slots["name"] = user_message.strip()

    print("[LOG] Scheduler slots:", scheduler_slots)

    # ----------------------------
    # Ask for missing slot (ONE AT A TIME)
    # ----------------------------
    if not scheduler_slots["name"]:
        return {
            "response": "May I know your name?",
            "scheduler_slots": scheduler_slots,
            "done": False
        }

    if not scheduler_slots["email"]:
        return {
            "response": "Please share your email address so I can send the meeting invite.",
            "scheduler_slots": scheduler_slots,
            "done": False
        }

    if not scheduler_slots["start_time"]:
        return {
            "response": "What date and time would work best for you?",
            "scheduler_slots": scheduler_slots,
            "done": False
        }

    # ----------------------------
    # All slots collected → Call Calendly
    # ----------------------------
    print("[LOG] Calling Calendly tool...")

    result = schedule_calendly_meeting(
        event_type_uri="https://api.calendly.com/event_types/3677b0d0-1e8d-458e-98ea-575bb00c1cb0",
        name=scheduler_slots["name"],
        email=scheduler_slots["email"],
        start_time=scheduler_slots["start_time"]
    )

    if result.get("success"):
        response = (
            f"✅ Your call has been scheduled successfully!\n\n"
            f"📅 Time: {scheduler_slots['start_time']}\n"
            f"📧 Confirmation sent to: {scheduler_slots['email']}"
        )
    else:
        response = f"❌ I couldn't schedule the call. {result.get('message', '')}"

    return {
        "response": response,
        "scheduler_slots": scheduler_slots,
        "done": True
    }











def read_document(state: RAGState) -> RAGState:
    file_path = state["file_path"]
    _, extension = os.path.splitext(file_path)
    extension = extension.lower() # Convert to lowercase for reliable comparison

    # --- 3. Conditional execution (if/elif/else) ---
    if extension == '.pdf':
        # Your code for PDF extraction goes here
        text = extract_text_from_pdf(file_path)
        
    elif extension == '.docx':
        # Your code for DOCX extraction goes here
        text = extract_text_from_docx(file_path)
    state["content"] = text
    return state

def toVector(state: RAGState) -> RAGState:
    text = state["content"]
    chunks = chunk_text(text, chunk_size=1000)
    store_embeddings_in_chromadb(chunks)
    state["chunks_ingested"] = len(chunks)
    return state

def rag_query(state: queryState) -> queryState:
    query = state["query"]
    response = rag_search(query)
    state["answer"] = response
    # print("Response:", response)
    return state 

def check_node(state: RAGState):
    # Example check: Ensure that at least one chunk was ingested
    state["query"] = input("Enter your query: ")
    end_statement = ["exit", "quit", "done","bye"]
    if state["query"].lower() in end_statement:
        return END
    else:
        return rag_query(state)

def lead_gen_node(state: LeadState) -> LeadState:
    prompt = """
Your sole function is to act as an advanced lead scoring engine for a coaching admissions assistant.

You must analyze the user's query to determine the quality and seriousness of their interest (conversion likelihood).

**Scoring Criteria (0-100):**
* **Score 90-100 (High Quality/High Intent):** Queries focusing on immediate commitment factors such as specific application deadlines, exact fees for a named course (e.g., "How much is the B.A. History fee?"), required documents for admission, or direct requests for the application link.
* **Score 50-89 (Medium Quality/Medium Intent):** Queries asking for general course details, campus visits, faculty information, general eligibility criteria, or comparing two specific programs. The intent is clear but not immediately focused on conversion.
* **Score 0-49 (Low Quality/Low Intent):** Vague, broad, or purely informational queries (e.g., "Tell me about the college," "What city is the campus in?"). These indicate low immediate commitment.

**Strict Output Instruction:**
Return *only* a single integer between 0 and 100. Do not include any text, explanations, markdown, or punctuation other than the integer itself.

USER QUERY TO SCORE: {{LeadState["query"]}}


"""
    lead_score = generate_with_gpt(prompt)
    
    lead_gen(state["name"], state["mob"], lead_score)
    return state   

def scheduler_node_wrapper(user_message: str, scheduler_slots: SchedulerSlots = None) -> Dict[str, Any]:
    """
    Graph-friendly wrapper for the scheduler node.
    Returns same dict structure for graph edges.
    """
    return scheduler_node(user_message, scheduler_slots)


RAGAgent = StateGraph(RAGState)
queryAgent = StateGraph(queryState)

RAGAgent.add_node("read_document", read_document)
RAGAgent.add_node("toVector", toVector)
queryAgent.add_node("rag_query", rag_query)
RAGAgent.add_node("check_node", check_node)
# --- Add conditional routing ---
# RAGAgent.add_conditional_edges(
#     "check_node",
#     check_node,                 # routing function
#     {
#         "rag_query": "rag_query",
#         END: END
#     }
# )

# --- Connect the graph ---
RAGAgent.add_edge(START, "read_document")
RAGAgent.add_edge("read_document", "toVector")
RAGAgent.add_edge("toVector", END)

queryAgent.add_edge(START, "rag_query")
queryAgent.add_edge("rag_query", END)

# Compile
rag_app = RAGAgent.compile()
res = queryAgent.compile()



schedulerAgent = StateGraph(SchedulerSlots)
schedulerAgent.add_node("scheduler_node", scheduler_node_wrapper)
schedulerAgent.add_edge(START, "scheduler_node")
schedulerAgent.add_edge("scheduler_node", END)
scheduler_app = schedulerAgent.compile()