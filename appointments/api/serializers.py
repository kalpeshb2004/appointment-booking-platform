from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from appointments.models import Patient, Department, Hospital


def get_role(user):
    """User ka role nikaalta: admin / doctor / patient"""
    if user.is_staff:
        return "admin"
    # reverse OneToOne: doctor row na ho to hasattr False deta
    if hasattr(user, "doctor"):
        return "doctor"
    return "patient"


class RegisterSerializer(serializers.Serializer):
    # Ek request se 2 table (User + Patient) bharte, isliye normal Serializer

    # --- User table fields ---
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)  # response me nahi jayega
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, default="")

    # --- Patient table fields (optional) ---
    phone = serializers.CharField(max_length=15, required=False, default="")
    gender = serializers.ChoiceField(choices=["M", "F", "O"], required=False, default="")
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)

    # validate_<field>: DRF us field ke liye khud chalata
    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ye username pehle se le liya gaya hai.")
        return value

    def validate_email(self, value):
        # Django me email by default unique nahi, isliye khud check
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Is email se account pehle se hai.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)  # Django built-in: common/numeric password rokta
        return value

    def create(self, validated_data):
        # Patient fields alag nikaal, baaki User ke
        patient_data = {
            "phone": validated_data.pop("phone"),
            "gender": validated_data.pop("gender"),
            "date_of_birth": validated_data.pop("date_of_birth"),
        }
        # atomic: User bana, Patient fail hua → dono rollback
        with transaction.atomic():
            user = User.objects.create_user(**validated_data)  # password HASH hota
            Patient.objects.create(user=user, **patient_data)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """
    simplejwt ka default login serializer extend kiya.
    Default kaam: username+password check, access+refresh token banana.
    Extra: token ke andar role daalna, response me user info bhejna.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Custom claims token ke payload me jaate.
        # Frontend decode karke role dekh sakta (admin page dikhana ya nahi).
        token["role"] = get_role(user)
        token["username"] = user.username
        return token

    def validate(self, attrs):
        # super().validate: credentials check. Galat → 401 auto.
        data = super().validate(attrs)

        # Tokens ke saath user info bhi, taaki frontend ko alag call na karni pade
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "first_name": self.user.first_name,
            "role": get_role(self.user),
        }
        return data


class HospitalSerializer(serializers.ModelSerializer):
    # ModelSerializer: model ke fields se khud serializer banata (validation + conversion)
    class Meta:
        model = Hospital
        fields = ["id", "name", "city", "address", "phone"]  # sirf ye fields bahar jaayenge


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]