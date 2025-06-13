from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.models import AiChatSession, get_default_user_profile
from core.serializers import AiChatSessionSerializer

def determine_conversation_style(choices):
    style = "mixed"
    
    if choices[0] =="Direct steps" and choices[1] == "Checklist":
        style = "action_based"
    elif choices[0] =="Detailed discussion" and choices[1] == "Conversation":
        style = "relationship_based"
        
    return style


@api_view(['POST'])
def create_chat_session(request):
    """Create new chat session"""
    # 1. Get the array of choices from the React frontend
    user_choices = request.data.get('choices', [])

    # 2. Get the default profile structure
    profile_data = get_default_user_profile()

    # 3. Determine the initial style using our new logic
    initial_style = determine_conversation_style(user_choices)
    profile_data['preferred_conversation_style'] = initial_style
    
    if initial_style == "action_based":
        profile_data["ph1"] = .90
        profile_data["ph2"] = .10
    elif initial_style == "relationship_based":
        profile_data["ph1"] = .10
        profile_data["ph2"] = .90
    else:
        profile_data["ph1"]=.60
        profile_data["ph2"]=.40
    
    # --- FIXED: Set the initial posterior to equal the initial prior ---
    profile_data["ph1e"] = profile_data["ph1"]
    profile_data["ph2e"] = profile_data["ph2"]  
    
    # 5. Create the session with the completed profile and choices
    session = AiChatSession.objects.create(
        choice_results=user_choices,
        user_profile=profile_data
    )
    serializer = AiChatSessionSerializer(session)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET','POST'])
def chat_session(request, session_id):
    """REtrieve a chat session and its message"""
    session = get_object_or_404(AiChatSession, id=session_id)
    serializer= AiChatSessionSerializer(session)
    
    if request.method == 'POST':
        message = request.data.get('message')
        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        session.send(message)
    return Response(serializer.data)