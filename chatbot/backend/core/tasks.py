from celery import shared_task
from openai import OpenAI
from core import models
import json



#handling tasks when AI is generating responses so that the window is not frozen
#wrapper  around handle method to cover asynchronous tasks
@shared_task
def handle_ai_request_job(ai_request_id):
    from core.models import AiRequest
    models.AiRequest.objects.get(id = ai_request_id).handle()
    
@shared_task
def update_user_profile_task(session_id, user_message):
    from core.models import AiChatSession
    try:
        session = AiChatSession.objects.get(id=session_id)
    except AiChatSession.DoesNotExist:
        return
    
    client = OpenAI()
    
    analysis_prompt= f"""
    You are a conversation analyst. Estimate two probabilities:
    - peh1 = probability (0 to 1) that the user is Action-Based(prefers lists, steps, directness)
    - peh2 = probability (0 to 1) that the user is Relationship-Based (prefers conversation, questions, narrative)

    Here are some examples:

    Example 1:
    User: "Tell me the fastest way to finish this project."
    peh1: 0.90
    peh2: 0.10

    Example 2:
    User: "Before we start, can we discuss what's most important to focus on together?"
    peh1: 0.20
    peh2: 0.80

    Example 3:
    User: "I just want to get this over with quickly."
    peh1: 0.85
    peh2: 0.15
        
    Return your analysis as a JSON object with keys "peh1" and "peh2", where values are between 0.0 and 1.0.

    User Message: "{user_message}"
    """
        
    try:    
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": analysis_prompt}],
            response_format={"type": "json_object"}
        )
        response_data = json.loads(completion.choices[0].message.content)
        peh1 = response_data.get('peh1', 0.5)
        peh2 = response_data.get('peh2', 0.5)

        # --- FIXED: Call the update method on the session object ---
        session.update_posterior(peh1, peh2)

    except Exception as e:
        print(f"Error during profile update for session {session_id}: {e}")
# --- UPDATED TASK TO MAKE A DECISION AND RESET THE CYCLE ---
@shared_task
def final_style_determination_task(session_id):
    """
    Analyzes the most recent batch of messages, makes a stable decision,
    and then resets the learning cycle.
    """
    try:
        session = models.AiChatSession.objects.get(id=session_id)
    except models.AiChatSession.DoesNotExist:
        return

    history = session.user_profile.get("posterior_history", [])
    if not history:
        return

    # Use a weighted average on the current batch of messages
    weights = range(1, len(history) + 1)
    weighted_sum = sum(p * w for p, w in zip(history, weights))
    total_weight = sum(weights)

    if total_weight == 0:
        return

    final_belief = weighted_sum / total_weight

    if final_belief > 0.65:
        final_style = "action_based"
    elif final_belief < 0.35:
        final_style = "relationship_based"
    else:
        final_style = "mixed"
    
    # Update the style based on this cycle's analysis
    session.user_profile["preferred_conversation_style"] = final_style
    
    # --- RESET THE LEARNING CYCLE ---
    # Reset message count to start the next 5-message cycle
    session.user_profile["message_count"] = 0
    # Clear the history for the next batch of analysis
    session.user_profile["posterior_history"] = []
    
    session.save()
    print(f"Cycle complete for session {session_id}. New style: {final_style} with belief {final_belief}. Resetting count.")

@shared_task
def hello_task(name):
    print(f"Hello {name}. You have {len(name)} characters in your name.")
