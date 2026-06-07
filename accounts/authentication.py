from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Medecin
from .utils import verifier_token


class MedecinAuthentication(BaseAuthentication):
    """
    Lit le token depuis le header Authorization: Bearer <token>
    et retourne le médecin correspondant.
    """
    def authenticate(self, request):
        header = request.headers.get('Authorization')
        if not header or not header.startswith('Bearer '):
            return None

        token = header.split(' ')[1]
        payload = verifier_token(token)

        if payload is None:
            raise AuthenticationFailed('Token invalide ou expiré')

        try:
            medecin = Medecin.objects.get(
                id=payload['medecin_id'],
                est_actif=True
            )
        except Medecin.DoesNotExist:
            raise AuthenticationFailed('Médecin introuvable')

        return (medecin, token)