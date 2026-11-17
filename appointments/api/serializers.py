from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from appointments.models import (Appointment, Department, Doctor, DoctorSchedule,Hospital, Patient)




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
            raise serializers.ValidationError("This username is already taken..")
        return value

    def validate_email(self, value):
        # Django me email by default unique nahi, isliye khud check
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
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

class DoctorSerializer(serializers.ModelSerializer):
    """Doctor list ke liye (halka data)"""

    # SerializerMethodField: custom logic se value, niche get_name() chalta
    name = serializers.SerializerMethodField()
    # source="a.b": related table se value uthao. Output-only isliye read_only
    department = serializers.CharField(source="department.name", read_only=True)
    department_id = serializers.IntegerField(source="department.id", read_only=True)
    hospital = serializers.CharField(source="department.hospital.name", read_only=True)
    hospital_id = serializers.IntegerField(source="department.hospital.id", read_only=True)

    class Meta:
        model = Doctor
        fields = ["id", "name", "qualification", "experience_years",
                  "consultation_fee", "department", "department_id",
                  "hospital", "hospital_id"]

    def get_name(self, obj):
        # Full name nahi hai to username
        return obj.user.get_full_name() or obj.user.username


class DoctorScheduleSerializer(serializers.ModelSerializer):
    # choices ka readable naam: 0 → "Mon"
    day = serializers.CharField(source="get_day_of_week_display", read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = ["day_of_week", "day", "start_time", "end_time"]


class DoctorDetailSerializer(DoctorSerializer):
    """Ek doctor ki detail: list wala data + weekly schedule"""

    # related_name="schedules" se nested list
    schedule = DoctorScheduleSerializer(source="schedules", many=True, read_only=True)

    class Meta(DoctorSerializer.Meta):
        fields = DoctorSerializer.Meta.fields + ["slot_minutes", "schedule"]


class BookingSerializer(serializers.Serializer):
    """Booking request ka input validate: format sahi hai ya nahi."""

    doctor_id = serializers.IntegerField()
    date = serializers.DateField()          # "2026-11-23"
    start_time = serializers.TimeField()    # "10:00"
    reason = serializers.CharField(max_length=255, required=False,
                                   allow_blank=True, default="")


class AppointmentSerializer(serializers.ModelSerializer):
    """Booking ka response / list me dikhane wala data."""

    doctor_name = serializers.SerializerMethodField()
    department = serializers.CharField(source="doctor.department.name", read_only=True)
    hospital = serializers.CharField(source="doctor.department.hospital.name", read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "doctor_name", "department", "hospital", "date",
                  "start_time", "end_time", "reason", "status", "created_at"]

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() or obj.doctor.user.username

class DoctorAppointmentSerializer(serializers.ModelSerializer):
    """
    Doctor ko patient ki zaruri info dikhti (naam, phone, gender).
    Email/DOB jaisa extra data nahi bhejte (privacy: need-to-know).
    """

    patient_name = serializers.SerializerMethodField()
    patient_phone = serializers.CharField(source="patient.phone", read_only=True)
    patient_gender = serializers.CharField(source="patient.gender", read_only=True)

    class Meta:
        model = Appointment
        fields = ["id", "patient_name", "patient_phone", "patient_gender",
                  "date", "start_time", "end_time", "reason", "status"]

    def get_patient_name(self, obj):
        u = obj.patient.user
        return u.get_full_name() or u.username

class StatusUpdateSerializer(serializers.Serializer):
    """Doctor sirf in do status me badal sakta. Cancel patient ka kaam hai."""

    status = serializers.ChoiceField(choices=["completed", "no_show"])

class AdminHospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ["id", "name", "city", "address", "phone"]

    def validate(self, attrs):
        # Same naam + same city ka duplicate hospital nahi.
        # validate(): saare fields ek saath milte, cross-field check ke liye.
        # PATCH me field na aaye to instance ki purani value use.
        name = attrs.get("name", getattr(self.instance, "name", None))
        city = attrs.get("city", getattr(self.instance, "city", None))
        qs = Hospital.objects.filter(name__iexact=name, city__iexact=city)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)  # edit me khud ko ignore
        if qs.exists():
            raise serializers.ValidationError("A hospital with this name already exists in this city.")
        return attrs


class AdminDepartmentSerializer(serializers.ModelSerializer):
    # Model ke unique_together se DRF khud duplicate (hospital + name) check lagata
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)

    class Meta:
        model = Department
        fields = ["id", "hospital", "hospital_name", "name"]


class AdminDoctorCreateSerializer(serializers.Serializer):
    """Doctor banane ka input: User account + Doctor profile ek saath."""

    # --- User fields ---
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, default="")

    # --- Doctor fields ---
    # PrimaryKeyRelatedField: id se Department object khud dhundta, galat id par 400
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    qualification = serializers.CharField(max_length=150)
    experience_years = serializers.IntegerField(min_value=0, default=0)
    consultation_fee = serializers.DecimalField(max_digits=8, decimal_places=2, min_value=0)
    slot_minutes = serializers.IntegerField(min_value=5, max_value=120, default=15)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken..")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        doctor_data = {
            key: validated_data.pop(key)
            for key in ("department", "qualification", "experience_years",
                        "consultation_fee", "slot_minutes")
        }
        # atomic: User bana, Doctor fail hua → User bhi rollback
        with transaction.atomic():
            # is_staff default False. True hota to get_role() "admin" bana deta.
            user = User.objects.create_user(**validated_data)
            return Doctor.objects.create(user=user, **doctor_data)


class AdminDoctorSerializer(serializers.ModelSerializer):
    """Doctor ka read + update. (username/password yahan badalte nahi.)"""

    name = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    # source="user.email": User table ki field, isliye update() me alag handle
    email = serializers.EmailField(source="user.email", required=False)
    first_name = serializers.CharField(source="user.first_name", required=False)
    last_name = serializers.CharField(source="user.last_name", required=False,
                                      allow_blank=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    hospital_name = serializers.CharField(source="department.hospital.name",
                                          read_only=True)

    class Meta:
        model = Doctor
        fields = ["id", "name", "username", "email", "first_name", "last_name",
                  "department", "department_name", "hospital_name",
                  "qualification", "experience_years", "consultation_fee",
                  "slot_minutes", "is_active"]
        extra_kwargs = {
            "slot_minutes": {"min_value": 5, "max_value": 120},
            "consultation_fee": {"min_value": 0},
        }

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def validate_email(self, value):
        # Edit me khud ka email allowed, dusre ka nahi
        taken = User.objects.filter(email__iexact=value).exclude(pk=self.instance.user_id)
        if taken.exists():
            raise serializers.ValidationError("This email belongs to another account.")
        return value.lower()

    def update(self, instance, validated_data):
        # Dotted source ki wajah se user ka data nested dict me aata: {"user": {...}}
        user_data = validated_data.pop("user", {})
        with transaction.atomic():
            user = instance.user
            for field, value in user_data.items():
                setattr(user, field, value)
            instance = super().update(instance, validated_data)
            # Doctor deactivate/activate ho to login bhi band/chalu (dono sync)
            user.is_active = instance.is_active
            user.save()
            return instance


class ScheduleItemSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)  # Mon=0 ... Sun=6
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs["end_time"] <= attrs["start_time"]:
            raise serializers.ValidationError("end_time must be after start_time.")
        return attrs


class ScheduleInputSerializer(serializers.Serializer):
    schedule = ScheduleItemSerializer(many=True, allow_empty=False)

    def validate_schedule(self, items):
        # Ek hi din ki shifts overlap na karein (10-1 aur 12-3 galat)
        by_day = {}
        for item in items:
            by_day.setdefault(item["day_of_week"], []).append(item)
        for day, shifts in by_day.items():
            shifts.sort(key=lambda s: s["start_time"])
            for prev, cur in zip(shifts, shifts[1:]):
                if cur["start_time"] < prev["end_time"]:
                    raise serializers.ValidationError(
                        f"Shifts on day {day} overlap."
                    )
        return items


class LeaveInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    reason = serializers.CharField(max_length=200, required=False,allow_blank=True, default="")