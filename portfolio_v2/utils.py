from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from django.core.mail import EmailMultiAlternatives
from django.conf import settings

# Send OTP email
def _send_otp_email(user, otp_code):
    subject = "OTP code for user verification"
    from_email = settings.EMAIL_HOST_USER
    to = user.email
    text_content = f"Your OTP code is {otp_code}.\n\nThis email is sent from the portfolio of Hadayetullah.\n\nMd. Hadayetullah\nWeb Developer"
    html_content = f"""
        <p style='font-size: 18px;'>Your OTP code <br/><span style='font-weight: bold; font-size: 24px;'>{otp_code}</span></p>
        <h3 style='color: #000;'>This email is sent from the portfolio of Hadayetullah</h3>
        <div style='margin-top: 50px; color: #000;'>
            <p>Md. Hadayetullah<br/>Web Developer<br/></p>
        </div>
    """

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        [to],  # main recipient
        # bcc=[settings.EMAIL_HOST_USER]  # hidden copy to myself
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


# Get client message email
def _get_email_client(email, name, purpose, message):
    subject = "Client Message (Portfolio)"
    from_email = settings.EMAIL_HOST_USER
    to = settings.EMAIL_HOST_USER

    text_content = f"""
        New message received from your portfolio website.

        Name: {name}
        Email: {email}
        Purpose: {purpose}

        Message:
        {message}

        ---
        This email was sent from the portfolio of Md. Hadayetullah
        Web Developer
    """

    html_content = f"""
        <div style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
            <h2 style="color: #111;">New Client Message (Portfolio)</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Purpose:</strong> {purpose}</p>
            <p><strong>Message:</strong></p>
            <p style="background: #f9f9f9; padding: 15px; border-radius: 8px;">{message}</p>
            <hr style="margin-top: 40px;"/>
            <p style="font-size: 14px; color: #555;">
                This email was sent from the portfolio of <strong>Md. Hadayetullah</strong><br/>
                Web Developer
            </p>
        </div>
    """

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        [to],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()



# Generate access token
def generate_access_token(user):
    token = AccessToken.for_user(user)
    return str(token)

