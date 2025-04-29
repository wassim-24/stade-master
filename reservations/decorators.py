# reservations/decorators.py
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(owner_flag: bool):
    """
    owner_flag=True  → page réservée aux propriétaires
    owner_flag=False → page réservée aux locataires
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_owner is owner_flag:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied        # HTTP 403
        return _wrapped
    return decorator

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

def owner_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_owner:
            return view_func(request, *args, **kwargs)
        # → l’utilisateur connecté N’est PAS owner
        return redirect('home_player')
    return _wrapped


def player_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_owner:
            return view_func(request, *args, **kwargs)
        # → l’utilisateur connecté EST owner
        return redirect('home_owner')
    return _wrapped


from django.http import HttpResponseForbidden
from functools import wraps

def only_owner(view_func):
    """
    Autorise exclusivement les comptes propriétaire (is_owner=True).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # Laisser le @login_required gérer la redirection vers /login/
            return view_func(request, *args, **kwargs)

        if request.user.is_owner:
            return view_func(request, *args, **kwargs)

        # Joueur connecté qui tente d’accéder à une vue owner → 403
        return HttpResponseForbidden("Accès réservé aux propriétaires.")
    return _wrapped


def only_player(view_func):
    """
    Autorise exclusivement les comptes joueur (is_owner=False).
    """
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)

        if not request.user.is_owner:
            return view_func(request, *args, **kwargs)

        return HttpResponseForbidden("Accès réservé aux joueurs.")
    return _wrapped
