from django.urls import path
from .views import login_view, generate_view

urlpatterns = [
    path('', login_view, name='login'),
    path('login/', login_view, name='login'),
    path('generate/', generate_view, name='generate'),
]
