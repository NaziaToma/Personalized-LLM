from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from core.models import AiChatSession
from core.serializers import AiChatSessionSerializer


@api_view(['POST'])
def create_chat_session(request):
    """Create new chat session"""
    session = AiChatSession.objects.create()
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