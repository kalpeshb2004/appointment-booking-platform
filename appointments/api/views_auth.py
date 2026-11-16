from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginSerializer, RegisterSerializer


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
                "message": "Account ban gaya. Ab login karo.",
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