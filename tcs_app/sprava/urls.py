from django.urls import path
from . import views

app_name = "sprava"

urlpatterns = [
    path("", views.dashboard, name="sprava_dashboard"),
    path("upload-contacts/", views.upload_contacts, name="sprava_upload_contacts"),
    #path("returns/import/", views.returns_import, name="sprava_returns_import"),  
    path("contacts/", views.contacts_list, name="contacts_list"),
    path('kontakt/<int:kontakt_id>/', views.kontakt_detail, name='kontakt_detail'),
]