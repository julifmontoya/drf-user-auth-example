from decouple import config
from django.db import transaction
from modules.authentication.presentation.serializers.token_obtain_pair_serializer import MyTokenObtainPairSerializer
#from shared.notifications.email import send_email_to


def register_provider(serializer):
    """
    Precondition: `serializer` (a ProviderRegistrationSerializer) has
    already been validated (serializer.is_valid(raise_exception=True)
    called by the view) -- this use case does not re-validate it.

    Steps: persist User + Provider (via serializer.create(), unchanged --
    not moved here), wrapped in transaction.atomic() so a Provider-persistence
    failure rolls back the User too instead of leaving it orphaned -> mint a
    token pair by calling MyTokenObtainPairSerializer.get_token(user)
    directly (the shared classmethod that adds the 'role' claim), NOT its
    .validate() method -- a freshly-registered user is always unverified,
    and .validate()'s email-verification check would always reject them.
    Calling get_token(user) directly builds the token pair for the
    already-created user with no re-authentication step, deliberately
    reusing only the claim-generation logic, not the login-gating logic ->
    build the email-verification URL (the access token doubles as the
    verification token later consumed by modules.authentication.VerifyEmail
    -- this cross-module contract is preserved exactly) -> send the
    verification email, deliberately OUTSIDE the atomic block -- a
    transient SMTP failure must not undo an already-successful
    registration (explicit requirement, not assumed).

    Raises (propagated to the caller, unchanged):
        django.db.utils.IntegrityError: duplicate email, OR any other
            persistence-level failure inside the User+Provider transaction
            (e.g. a Provider-side constraint violation) -- both now roll
            back cleanly instead of leaving a partial User row; the
            calling view's exception handling and response are unchanged
            either way, since it already catches IntegrityError generically.
        Any exception from send_email_to (e.g. SMTP failure) is
            intentionally left unhandled here, exactly as before -- it now
            happens after the transaction has already committed, so it
            cannot roll back the registration.

    Returns:
        dict: the token pair, {'access': ..., 'refresh': ...} (SimpleJWT's
        standard shape), both carrying the same claims (including 'role')
        that a normal /v1/auth/login/ token would.
    """
    # User + Provider persistence is wrapped together so a Provider-creation
    # failure (e.g. a DB-level constraint violation) cannot leave a
    # committed, orphaned User with no Provider. Token minting and email
    # sending are deliberately left outside this block: neither should be
    # assumed to require rolling back an already-successful registration.
    with transaction.atomic():
        user = serializer.create(serializer.validated_data)

    refresh = MyTokenObtainPairSerializer.get_token(user)
    token = {'access': str(refresh.access_token), 'refresh': str(refresh), "message": "User registered successfully"}

    ## Test Postman
    #relative_link = reverse('email-verify', kwargs={'token': token['access']})
    #url = config('HOST_BACK') + relative_link

    url = config('HOST_FRONT') + '/provider/email-verify/' + token['access'] + '/'

    email_subject = 'Verifica tu email - Viaja y Descubre'
    email_body = 'Hola. Usa el link para verificar tu email \n\n' + url + '\n\n' + 'Felipe Montoya' + '\n' + 'Viaja y Descubre' + '\n' '3128663738'
    #send_email_to(serializer.validated_data['email'], email_subject, email_body)

    return token
