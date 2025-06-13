from openai import OpenAI
from django.db import models


def get_default_user_profile():
    return {
        "preferred_conversation_style": None,
        "ph1": None,
        "ph2": None,
        "peh1": None,
        "peh2": None,
        "message_count": 0,
        "ph1e": .50, #posterior action based
        "ph2e": .50  #posterior relationship based 
    }
    
    
class Recipe(models.Model):
    name = models.CharField(max_length=255)
    steps = models.TextField()

    def __str__(self):
        return self.name

#AI chat session model

class AiChatSession(models.Model):
    """_summary_

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    choice_results = models.JSONField(default=list, blank=True)
    user_profile = models.JSONField(default=get_default_user_profile)
    
    def update_posterior(self, new_peh1, new_peh2):
        """
        Performs a Bayesian update using the current posterior as the new prior.
        """
        # 1. Get the current posterior, which serves as the prior for this update.
        current_posterior_h1 = self.user_profile.get("ph1e", 0.5)
        
        # 2. Calculate the marginal likelihood (total probability of the new evidence)
        marginal_likelihood = (new_peh1 * current_posterior_h1) + (new_peh2 * (1 - current_posterior_h1))

        # 3. Calculate the new posterior for H1 (action-based)
        if marginal_likelihood > 0:
            updated_ph1e = (new_peh1 * current_posterior_h1) / marginal_likelihood
        else:
            updated_ph1e = current_posterior_h1 # Avoid division by zero

        # 4. Update the profile with the new, refined beliefs and the evidence used.
        self.user_profile["ph1e"] = updated_ph1e
        self.user_profile["ph2e"] = 1 - updated_ph1e
        self.user_profile["peh1"] = new_peh1
        self.user_profile["peh2"] = new_peh2
        
        # 5. Update the conversational style based on the new belief.
        if updated_ph1e > 0.7:
             self.user_profile["preferred_conversation_style"] = "action_based"
             self.user_profile["ph1"] = updated_ph1e
             self.user_profile["ph2"] = 1-self.user_profile["ph1"]
        elif updated_ph1e < 0.3:
            self.user_profile["preferred_conversation_style"] = "relationship_based"
            self.user_profile["ph2"] = 1-updated_ph1e
            self.user_profile["ph1"] = 1-self.user_profile["ph2"]
        else:
            self.user_profile["preferred_conversation_style"] = "mixed"

        self.save()
    
    # --- NEW: A method to generate a system prompt that adapts ---
    def _get_dynamic_system_prompt(self):
        style = self.user_profile.get("preferred_conversation_style", "mixed")
        if style == "action_based":
            prompt = f"""You're a friendly Computer Science coding note maker and you reply with only python learning materials.When the user is action based, give output in the following format -
                        1. direct and simple sentence
                        2. short and concise sentence
                        3. task focused and in bullet points"""
        elif style == "relationship_based":
            prompt = f"""You're a friendly Computer Science coding note maker and you reply with only python learning materials. When the user is action based, give output in the following format -
            1. direct and simple sentence
            2. storyline conversation
            3. focus on emotion and in paragraph style"""
        else: # mixed
            prompt = "You're a friendly Computer Science coding note maker and you reply with only python learning materials."
        return self._create_message(prompt, "system")
    
    #last request in the session
    def get_last_request(self):
        """return the most recent req or None """
        return self.airequest_set.all().order_by('-created_at').first()
        
    def _create_message(self, message, role="user"):
        """create a message for the AI"""
        return {"role": role, "content": message}

    def create_first_message(self, message):
        """Creating first message in the session"""
        return [
            self._create_message("You're a CS note maker and you reply with concise learning materials.", "system"),
            self._create_message(message, "user")
        ]
    def messages(self):
        """Return messages in the conversation including the AI response"""
        all_messages = []
        request = self.get_last_request()
        
        if request:
            all_messages.extend(request.messages)
            try:
                all_messages.append(request.response["choices"][0]["message"])
            except (KeyError, TypeError, IndexError):
                pass
        return all_messages
    
    def send(self, message):
        from core.tasks import update_user_profile_task
        if self.user_profile.get("message_count", 0) < 5:
            self.user_profile["message_count"] += 1
            self.save()
            update_user_profile_task.delay(self.id, message)

        last_request = self.get_last_request()
        system_prompt = self._get_dynamic_system_prompt()
        
        messages_to_send = []
        if not last_request:
            # For the first message, we can just use the dynamic prompt directly
            messages_to_send = [system_prompt, self._create_message(message, "user")]
        elif last_request.status in [AiRequest.COMPLETE, AiRequest.FAILED]:
            # For subsequent messages, rebuild history but inject the NEWEST system prompt
            history = [msg for msg in self.messages() if msg.get("role") != "system"]
            messages_to_send = [system_prompt] + history + [self._create_message(message, "user")]
        else:
            # A request is already running, do nothing
            return
            
        AiRequest.objects.create(session=self, messages=messages_to_send)

#AI request model
class AiRequest(models.Model):
    
    #adding status
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETE = 'complete'
    FAILED = 'failed'
    #user will see this
    STATUS_OPTIONS = (
        (PENDING, 'Pending'),
        (RUNNING, 'Running'),
        (COMPLETE, 'Complete'),
        (FAILED, 'Failed')
    )

    status = models.CharField(choices=STATUS_OPTIONS, default=PENDING)
    
    #this stores each chat session's id  
    session = models.ForeignKey(
        AiChatSession,
        on_delete=models.CASCADE,
        null = True,
        blank= True
    )
    #This stores user input
    messages = models.JSONField()
    
    #This stores AI's response 
    response = models.JSONField(null = True, blank = True)
    
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def _queue_job(self):
        """add job to queue, asynchronous task"""
        from core.tasks import handle_ai_request_job
        handle_ai_request_job.delay(self.id)
    
    
    def handle(self):
        """Handle request"""
        
        self.status = self.RUNNING
        self.save()
        client = OpenAI()
        try:
            completion = client.chat.completions.create(
                model= "gpt-4o-mini",
                messages=self.messages
            )
            self.response = completion.to_dict()
            self.status = self.COMPLETE
        except:
            self.status=self.FAILED
        self.save()
    
    
    def save(self, **kwargs):
        is_new =self._state.adding
        super().save(**kwargs)
        if is_new:
            self._queue_job()