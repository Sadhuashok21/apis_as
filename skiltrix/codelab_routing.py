"""
WebSocket URL routing for SkilTrix CodeLab.
"""

from django.urls import path
from . import codelab_consumers

websocket_urlpatterns = [
    path('ws/codelab/terminal/<str:project_id>/', codelab_consumers.CodeLabTerminalConsumer.as_asgi()),
    path('ws/codelab/logs/<str:project_id>/', codelab_consumers.CodeLabLogStreamConsumer.as_asgi()),
]
