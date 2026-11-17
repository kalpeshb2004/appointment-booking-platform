from rest_framework import status
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginSerializer, RegisterSerializer, get_role



class RegisterView(APIView):
    """POST /api/auth/register : naya patient account"""

    permission_classes = [AllowAny]  # register ke liye login nahi chahiye
    authentication_classes = []      # expired token bheja to bhi fail nahi

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # galat data → auto 400
        user = serializer.save()                   # create() chalta

        # password kabhi wapas nahi
        return Response(
            {
                "message": "Account created. Please log in.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """POST /api/auth/login : username+password → access + refresh token"""
    # Baaki kaam simplejwt ka view karta. Hum sirf apna serializer lagate.
    serializer_class = LoginSerializer

class MeView(APIView):
    """GET /api/auth/me : token wala user kaun hai, uski info"""

    # Token zaruri. Bina token / galat token → 401 auto.
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # JWTAuthentication token verify karke request.user set kar deta
        user = request.user
        role = get_role(user)

        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": role,
            "profile": None,  # admin ka profile nahi hota
        }

        # Role ke hisaab se extra info
        if role == "patient" and hasattr(user, "patient"):
            p = user.patient
            data["profile"] = {
                "phone": p.phone,
                "gender": p.gender,
                "date_of_birth": p.date_of_birth,
            }
        elif role == "doctor":
            d = user.doctor
            data["profile"] = {
                "hospital": d.department.hospital.name,
                "department": d.department.name,
                "qualification": d.qualification,
                "consultation_fee": str(d.consultation_fee),  # Decimal → string
            }

        return Response(data)