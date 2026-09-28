from modules.authentication.presentation.serializers.set_new_password_serializer import SetNewPasswordSerializer


def reset_password(data):
    """
    Thin wrapper preserving the exact existing shape documented in
    docs/migrations/user-authentication.md 4.1: the real workflow (token
    re-validation + password persistence) lives inside
    SetNewPasswordSerializer.validate(), not here. This use case exists only
    to give the workflow a named entry point in application/use_cases/,
    matching the other three authentication flows, without relocating the
    side effect out of the serializer (a deliberate V1 decision -- see
    docs/migrations/user-authentication.md 9 item 7 for the V2 alternative).

    Raises whatever serializer.is_valid(raise_exception=True) raises
    (rest_framework.exceptions.AuthenticationFailed on an invalid token,
    propagated from inside the serializer's validate()).
    """
    serializer = SetNewPasswordSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer
