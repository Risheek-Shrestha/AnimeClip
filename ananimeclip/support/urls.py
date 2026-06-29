from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("faq/", views.faq, name="faq"),
    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/reply/", views.ticket_reply, name="ticket_reply"),
]
