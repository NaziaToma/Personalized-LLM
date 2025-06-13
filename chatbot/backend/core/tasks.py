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


@shared_task
def hello_task(name):
    print(f"Hello {name}. You have {len(name)} characters in your name.")
