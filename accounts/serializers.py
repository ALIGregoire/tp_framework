from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "telephone",
            "role",
        ]
        read_only_fields = ["id", "email", "username", "role"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    # Le frontend n'envoie pas forcément un champ de confirmation.
    password2 = serializers.CharField(write_only=True, required=False)
    username = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "telephone",
            "role",
            "password",
            "password2",
        ]

    def validate(self, attrs):
        password2 = attrs.get("password2")
        if password2 is not None and attrs.get("password") != password2:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

    def _generate_unique_username(self, email: str) -> str:
        base = (email.split("@")[0] or "user")[:150]
        candidate = base
        suffix = 1
        while User.objects.filter(username=candidate).exists():
            tail = str(suffix)
            candidate = f"{base[: max(0, 150 - len(tail))]}{tail}"
            suffix += 1
        return candidate

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password2", None)

        username = (validated_data.get("username") or "").strip()
        email = validated_data.get("email")
        if not username:
            validated_data["username"] = self._generate_unique_username(email)

        # Inscription publique = compte citoyen uniquement.
        validated_data["role"] = User.Role.CITOYEN

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "telephone",
            "role",
            "is_active",
        ]
        read_only_fields = ["id", "email", "username"]
