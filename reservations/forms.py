# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from .models import User, Stade, StadeImage
from django.contrib.auth.forms import PasswordChangeForm

# ---------- Auth ----------
class SignUpForm(UserCreationForm):
    ROLE = (('False', "Locataire"), ('True', "Propriétaire"))
    phone    = forms.CharField(label="Téléphone", max_length=20)
    is_owner = forms.ChoiceField(label="Vous êtes", choices=ROLE, widget=forms.RadioSelect)

    class Meta:
        model  = User
        fields = ("username", "phone", "is_owner", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone    = self.cleaned_data['phone']
        user.is_owner = self.cleaned_data['is_owner'] == 'True'
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    username = forms.CharField(label="Utilisateur ou Téléphone")
    password = forms.CharField(widget=forms.PasswordInput, label="Mot de passe")


# ---------- Stade ----------
class StadeForm(forms.ModelForm):
    class Meta:
        model  = Stade
        fields = ["nom", "adresse", "capacite", "prix_par_personne", "est_ouvert"]


StadeImageFormSet = inlineformset_factory(
    parent_model = Stade,
    model        = StadeImage,
    fields       = ["image"],
    extra        = 5,
    max_num      = 5,
    can_delete   = True,
)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "phone", "age"]
        widgets = {
            "username": forms.TextInput(),
            "email":    forms.EmailInput(),
            "phone":    forms.TextInput(),
            "age":      forms.NumberInput(),
        }