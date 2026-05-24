from flask import Flask, render_template, request, jsonify, session
from main import admission_enquiry
from graph import lead_gen_node, scheduler_node
from datetime import datetime, timedelta
import re
from flask_session import Session
from openai import OpenAI




app = Flask(__name__)
app.secret_key = "super-secret-key"

app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
Session(app)

FINAL_KEYWORDS = [
    "thank you", "thanks", "done",
    "no more questions", "that's all"
]

INACTIVITY_TIMEOUT = 60 * 60 # 1 hour in seconds

openai_client = OpenAI(api_key="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")

def detect_intent(user_message: str) -> str:
    """
    Uses GPT-4o to decide intent.
    Returns only one word:
    - 'prompt' for general queries (RAG)
    - 'instruction' for scheduling requests (Calendly)
    """
    prompt = f"""
Decide if the user's message is asking to schedule an appointment/call or a general query.
Respond with only one word: 'instruction' if user wants to schedule an appointment,
or 'prompt' if it's a general question.
User message: "{user_message}"
Answer with only one word.
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    word = response.choices[0].message.content.strip().lower()
    return "instruction" if word == "instruction" else "prompt"

@app.route("/")
def AdmissionEnquiry():
    return render_template('admission_agent.html')


# @app.route("/admission-message", methods=["POST"])
# def admission_message():
#     data = request.get_json(silent=True) or {}

#     user_message = data.get("message", "").lower()
#     user_name = data.get("name")
#     user_mobile = data.get("mobile")

#     now = datetime.utcnow()

#     # Initialize session state (only for current session)
#     if "queries" not in session or session.get("lead_generated", False):
#         # Clear previous session history
#         session["queries"] = []
#         session["lead_generated"] = False
#         session["last_activity"] = now.isoformat()

#     # Store current user message
#     session["queries"].append({"role": "user", "message": user_message})
#     last_activity = datetime.fromisoformat(session.get("last_activity", now.isoformat()))
#     session["last_activity"] = now.isoformat()

#     # Create conversation history string for bot
#     history_text = ""
#     for q in session["queries"]:
#         role = q.get("role", "user")
#         msg = q.get("message", "")
#         history_text += f"{role}: {msg}\n"

#     # Generate response using full history
#     bot_reply = admission_enquiry(history_text)

#     clean_reply = re.sub(r'(\*{1,3}|#{1,6}|_{1,2}|~{2}|`{1,3})', '', bot_reply)

#     # Optional: Remove leading/trailing spaces on each line
#     clean_reply = '\n'.join(line.strip() for line in clean_reply.splitlines())
        
#     # Store bot reply in session too
#     session["queries"].append({"role": "bot", "message": clean_reply})

#     # ---------------------------
#     # FINAL CONDITIONS
#     # ---------------------------
#     keyword_trigger = any(k in user_message for k in FINAL_KEYWORDS)
#     timeout_trigger = (now - last_activity) > INACTIVITY_TIMEOUT

#     if not session["lead_generated"] and (keyword_trigger or timeout_trigger):
#         lead_state = {
#             "name": user_name,
#             "mob": user_mobile,
#             "queries": session["queries"]
#         }
#         lead_res = lead_gen_node(lead_state)
#         session["lead_generated"] = True
#         print("✅ Lead generated:", lead_res)

#     return jsonify({"reply": clean_reply})




@app.route("/admission-message", methods=["POST"])
def admission_message():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()
    user_name = data.get("name")
    user_mobile = data.get("mobile")
    now = datetime.utcnow()

    print(f"\n[LOG] Incoming message: {user_message}")

    # ---------------------------
    # SESSION INITIALIZATION
    # ---------------------------
    if "queries" not in session:
        session["queries"] = []
        session["scheduler_slots"] = {}

    # Reset session if inactive
    last_activity = session.get("last_activity", now.isoformat())
    last_activity_dt = datetime.fromisoformat(last_activity)
    if (now - last_activity_dt).total_seconds() > INACTIVITY_TIMEOUT:
        print("[LOG] Session inactive. Clearing old queries and scheduler slots.")
        session["queries"] = []
        session["scheduler_slots"] = {}
    session["last_activity"] = now.isoformat()

    # Store current user message
    session["queries"].append({"role": "user", "message": user_message})

    # ---------------------------
    # SCHEDULER FLOW (multi-turn)
    # ---------------------------
    if session.get("scheduler_slots"):  # ongoing scheduling
        print("[LOG] Using scheduler block (multi-turn ongoing)")
        bot_reply_data = scheduler_node(user_message, session["scheduler_slots"])
        bot_reply = bot_reply_data["response"]
        session["scheduler_slots"] = bot_reply_data["scheduler_slots"]

        if bot_reply_data.get("done", False):
            print("[LOG] Scheduler completed. Resetting scheduler state.")
            session["scheduler_slots"] = {}

    else:
        # ---------------------------
        # INTENT DETECTION
        # ---------------------------
        intent = detect_intent(user_message)
        print(f"[LOG] Intent detected: {intent}")

        if intent == "instruction":
            print("[LOG] Starting scheduler flow")
            bot_reply_data = scheduler_node(
                user_message,
                session.get("scheduler_slots", {}),
                user_name=user_name
            )

            bot_reply = bot_reply_data["response"]
            session["scheduler_slots"] = bot_reply_data["scheduler_slots"]

            if bot_reply_data.get("done", False):
                print("[LOG] Scheduler completed. Resetting scheduler state.")
                session["scheduler_slots"] = {}

        else:
            # ---------------------------
            # RAG FLOW
            # ---------------------------
            print("[LOG] Using RAG block")
            history_text = "\n".join(f"{q['role']}: {q['message']}" for q in session["queries"])
            bot_reply = admission_enquiry(history_text)

    # ---------------------------
    # CLEAN REPLY
    # ---------------------------
    clean_reply = re.sub(r'(\*{1,3}|#{1,6}|_{1,2}|~{2}|`{1,3})', '', bot_reply)
    clean_reply = "\n".join(line.strip() for line in clean_reply.splitlines())

    # Store bot reply in session
    session["queries"].append({"role": "bot", "message": clean_reply})

    print(f"[LOG] Bot reply: {clean_reply}")

    # ---------------------------
    # FINAL LEAD GENERATION
    # ---------------------------
    keyword_trigger = any(k in user_message for k in FINAL_KEYWORDS)
    timeout_trigger = (now - last_activity_dt).total_seconds() > INACTIVITY_TIMEOUT

    if not session.get("lead_generated", False) and (keyword_trigger or timeout_trigger):
        print("[LOG] Triggering lead generation")
        lead_state = {
            "name": user_name,
            "mob": user_mobile,
            "queries": session["queries"]
        }
        lead_res = lead_gen_node(lead_state)
        session["lead_generated"] = True
        print("✅ Lead generated:", lead_res)
        session.clear()

    return jsonify({"reply": clean_reply})






if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)  # bind to localhost only
