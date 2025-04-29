# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils.translation import gettext_lazy as _
from django.conf import settings

# ---------- Utilisateur ----------
class User(AbstractUser):
    # éviter le clash de related_name
    groups = models.ManyToManyField(
        Group, related_name='reservations_users', blank=True,
        help_text=_('Groupes …'), verbose_name=_('groups')
    )
    user_permissions = models.ManyToManyField(
        Permission, related_name='reservations_user_permissions', blank=True,
        help_text=_('Permissions …'), verbose_name=_('user permissions')
    )

    phone    = models.CharField("Téléphone", max_length=20, blank=True)
    is_owner = models.BooleanField("Propriétaire de stade", default=False)
    age      = models.PositiveIntegerField("Âge (joueur)", null=True, blank=True)

    def __str__(self):
        role = "Propriétaire" if self.is_owner else "Locataire"
        return f"{self.username} ({role})"


# ---------- Stade ----------
class Stade(models.Model):
    owner             = models.OneToOneField(User, on_delete=models.CASCADE)
    nom               = models.CharField(max_length=100)
    adresse           = models.CharField(max_length=255)
    CAPACITY          = [('6x6','6×6'), ('7x7','7×7'), ('8x8','8×8'), ('9x9','9×9')]
    capacite          = models.CharField(max_length=3, choices=CAPACITY)
    prix_par_personne = models.DecimalField(max_digits=6, decimal_places=2)
    est_ouvert        = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nom} – {self.owner.username}"


# ---------- Photos ----------
def stade_upload_path(instance, filename):
    return f"stade_{instance.stade.id}/{filename}"

class StadeImage(models.Model):
    stade       = models.ForeignKey(Stade, on_delete=models.CASCADE, related_name="images")
    image       = models.ImageField(upload_to=stade_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]          # plus anciennes d’abord


class Booking(models.Model):
    stade   = models.ForeignKey("Stade", on_delete=models.CASCADE,
                                related_name="bookings")
    user    = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)
    jour    = models.DateField()
    heure   = models.TimeField()

    class Meta:
        unique_together = ("stade", "jour", "heure")      # 1 seule résa / slot
        ordering        = ("jour", "heure")

    def __str__(self):
        return (f"{self.stade.nom} – {self.jour} {self.heure} "
                f"par {self.user.username}")