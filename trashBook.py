from openai import OpenAI

# Initialize OpenAI client
openai_client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

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







@app.route("/admission-message", methods=["POST"])
def admission_message():
    data = request.get_json(silent=True) or {}

    user_message = data.get("message", "").lower()
    user_name = data.get("name")
    user_mobile = data.get("mobile")

    now = datetime.utcnow()

    # ---------------------------
    # SESSION INITIALIZATION
    # ---------------------------
    if "queries" not in session or session.get("lead_generated", False):
        session["queries"] = []
        session["lead_generated"] = False
        session["last_activity"] = now.isoformat()

    session["queries"].append({"role": "user", "message": user_message})
    last_activity = datetime.fromisoformat(session.get("last_activity", now.isoformat()))
    session["last_activity"] = now.isoformat()

    # ---------------------------
    # INTENT DECISION
    # ---------------------------
    intent = detect_intent(user_message)

    if intent == "instruction":
        # Use Calendly tool / scheduler node
        bot_reply_data = scheduler_node(user_message, session.get("scheduler_state", {}))
        bot_reply = bot_reply_data["response"]
        session["scheduler_state"] = bot_reply_data["state"]
        done = bot_reply_data.get("done", False)
        if done:
            # Reset scheduler state for next scheduling
            session["scheduler_state"] = {}
    else:
        # Use RAG tool
        history_text = ""
        for q in session["queries"]:
            role = q.get("role", "user")
            msg = q.get("message", "")
            history_text += f"{role}: {msg}\n"
        bot_reply = admission_enquiry(history_text)

    # ---------------------------
    # CLEAN UP RESPONSE
    # ---------------------------
    clean_reply = re.sub(r'(\*{1,3}|#{1,6}|_{1,2}|~{2}|`{1,3})', '', bot_reply)
    clean_reply = '\n'.join(line.strip() for line in clean_reply.splitlines())

    session["queries"].append({"role": "bot", "message": clean_reply})

    # ---------------------------
    # FINAL CONDITIONS: LEAD GENERATION
    # ---------------------------
    keyword_trigger = any(k in user_message for k in FINAL_KEYWORDS)
    timeout_trigger = (now - last_activity) > INACTIVITY_TIMEOUT

    if not session["lead_generated"] and (keyword_trigger or timeout_trigger):
        lead_state = {
            "name": user_name,
            "mob": user_mobile,
            "queries": session["queries"]
        }
        lead_res = lead_gen_node(lead_state)
        session["lead_generated"] = True
        print("✅ Lead generated:", lead_res)

    return jsonify({"reply": clean_reply})





# --------------------------------------------------------------------------

# ---------------------------
# INTENT DECISION AND RESPONSE
# ---------------------------
intent = detect_intent(user_message)

if intent == "instruction":
    # Use Calendly tool / scheduler node
    bot_reply_data = scheduler_node(user_message, session.get("scheduler_state", {}))
    bot_reply = bot_reply_data["response"]
    # Update scheduler state for multi-turn slot filling
    session["scheduler_state"] = bot_reply_data["state"]
    done = bot_reply_data.get("done", False)
    if done:
        # Reset scheduler state for next scheduling
        session["scheduler_state"] = {}
else:
    # Use RAG tool
    history_text = ""
    for q in session["queries"]:
        role = q.get("role", "user")
        msg = q.get("message", "")
        history_text += f"{role}: {msg}\n"
    bot_reply = admission_enquiry(history_text)

# ---------------------------
# STORE BOT REPLY IN SESSION
# ---------------------------
clean_reply = re.sub(r'(\*{1,3}|#{1,6}|_{1,2}|~{2}|`{1,3})', '', bot_reply)
clean_reply = '\n'.join(line.strip() for line in clean_reply.splitlines())

# Store in session["queries"] regardless of source (RAG or Calendly)
session["queries"].append({"role": "bot", "message": clean_reply})

# ---------------------------
# RETURN FINAL REPLY
# ---------------------------
return jsonify({"reply": clean_reply})
