import json

from django.core.mail import EmailMultiAlternatives
from django.conf import settings


# Parse data
def _parse_json_or_post(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return request.POST


# Send OTP email
def _send_otp_email(user):
    subject = "OTP code for user verification"
    from_email = settings.EMAIL_HOST_USER
    to = user.email
    text_content = f"Your OTP code is {user.otp}.\n\nThis email is sent from the portfolio of Hadayetullah.\n\nMd. Hadayetullah\nWeb Developer"
    html_content = f"""
        <p style='font-size: 18px;'>Your OTP code <br/><br/><span style='font-weight: bold; font-size: 24px;'>{user.otp}</span></p>
        <h3 style='color: #000;'>This email is sent from the portfolio of Hadayetullah</h3>
        <div style='margin-top: 50px; color: #000;'>
            <p>Md. Hadayetullah<br/>Web Developer<br/></p>
        </div>
    """

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()