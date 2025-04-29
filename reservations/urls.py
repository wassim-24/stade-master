from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('',            views.login_view,     name='login'),
    path('signup/',     views.signup,         name='signup'),
    path('logout/',     views.logout_view,    name='logout'),

    # Stades
    path("stade/<int:pk>/",         views.stade_detail,    name="stade_detail"),
    path("stade/<int:pk>/reserve/", views.reserver_slot,   name="reserve_slot"),

    # Dashboards
    path('owner/',  views.owner_home,  name='home_owner'),
    path('player/', views.player_home, name='home_player'),

    # Player
    path('player/profile/',  views.player_profile, name='player_profile'),
    path('player/bookings/', views.player_bookings, name='player_bookings'),
    path('player/search/',   views.player_search, name='player_search'),

    # Owner
    path("owner/bookings/", views.owner_bookings, name="owner_bookings"),
    path('owner/profile/',  views.owner_profile,  name='owner_profile'),
    path('owner/manage/',   views.owner_manage,   name='owner_manage'),
]
