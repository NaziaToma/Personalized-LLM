from openai import OpenAI
from django.db import models
from core.tasks import handle_ai_request_job


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
    
    def target_question(self):
        """RQ1: Step 1 - Setting up a prior belief based on targeted question
        """
        question1 = "Do you prefer direct next steps or detailed discussion first?"
        question1_options=["1. direct steps", "2. detailed discussion"]

        question2= "Would you prefer a checklist or conversation?"
        question2_options=["1. checklist", "2. conversation"]
    
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
        """send a message to the AI"""
        last_request = self.get_last_request()
        
        if not last_request:
            AiRequest.objects.create(
                session=self, messages=self.create_first_message(message)
            )
        elif last_request.status in [AiRequest.COMPLETE, AiRequest.FAILED]:
            AiRequest.objects.create(
                session = self,
                messages = self.messages() + [
                    self._create_message(message, "user")
                ]
            )
        else:
            return 

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