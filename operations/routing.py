from django.urls import path
from operations import consumers
from crm import consumers as crm_consumers

websocket_urlpatterns = [
    path('ws/fleet/live-radar/', consumers.FleetLiveRadarConsumer.as_asgi()),
    path('ws/emergency/sos/', consumers.EmergencySOSConsumer.as_asgi()),
    path('ws/crm/kanban/', crm_consumers.CRMKanbanConsumer.as_asgi()),
]

