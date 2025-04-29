# reservations/middleware.py
from django.utils.cache import add_never_cache_headers

class NoCacheAuthenticatedMiddleware:
    """
    Ajoute un header ‘no-cache’ quand l’utilisateur est connecté
    pour que le navigateur n’affiche plus les pages protégées
    après déconnexion (bouton « précédent »).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
