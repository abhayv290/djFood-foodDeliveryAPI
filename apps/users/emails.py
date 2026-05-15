from django.core.mail import send_mail,EmailMultiAlternatives
from django.conf import settings 


def text_email(name,link):
    return f"""
    Hi {name},
    Thanks for signing up with foodRevolut
    
    Please verify your email  address  by clicking  the link below:
    {link}
    
    this link will expires in within 10 minutes 
    
    If you didn't sent this request , ignore this 
    """.strip()
def text_email_reset_password(name,link):
    return f"""
    Hi {name},
    
    Click the link below to reset your password:
    {link}
    
    this link will expires in within 10 minutes 
    
    If you didn't sent this request , ignore this 
    """.strip()

def send_verification_email(user,token):
    link  = f"{settings.SERVER_URL}/api/v1/auth/email/verify/?token={token}"
    text_body = text_email(user.name,link)
    send_mail(
        subject='Verify Your FoodRevolut Account',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        message=text_body
    )


def send_password_reset_email(user,token):
    link = f"{settings.SERVER_URL}/api/v1/auth/password/reset/?token={token}"
    text_body = text_email_reset_password(user.name,link)
    send_mail(
        subject='Reset Your Old password ',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        message=text_body
    )


def send_html_email(to_email, subject, html_body, text_body):
    email = EmailMultiAlternatives(
        subject    = subject,
        body       = text_body,
        from_email = settings.DEFAULT_FROM_EMAIL,
        to         = [to_email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send()
 
    if settings.DEBUG:
        print(f"\n{'='*60}")
        print(f"  EMAIL: {subject}")
        print(f"  To: {to_email}")
        print(f"{'='*60}\n")
 
 
def wrap_email_html(content, title):
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background-color:#f4f4f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f5;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;">
        <tr><td style="background-color:#e85d30;padding:28px 40px;text-align:center;">
          <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">FoodRevolut</h1>
          <p style="margin:6px 0 0;color:#ffd4c2;font-size:13px;">{title}</p>
        </td></tr>
        <tr><td style="padding:36px 40px;">{content}</td></tr>
        <tr><td style="background-color:#f4f4f5;padding:20px 40px;text-align:center;border-top:1px solid #e8e8e8;">
          <p style="margin:0;font-size:12px;color:#9b9b9b;">&copy; 2026 FoodRevolut. All rights reserved.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""