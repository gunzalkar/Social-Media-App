import random
import os
import string
from app import mail
from flask_mail import Message
from flask import render_template, url_for
from app import app
import subprocess
from config import basedir
import secrets
from PIL import Image

def generate_verification_code(size=8):
    verification_code = ''.join(
        [
            random.choice(
                string.ascii_uppercase + string.ascii_lowercase + string.digits
            ) for n in range(size)
        ]
    )
    
    return verification_code

def send_mail(subject, sender, recipients, text_body, html_body):
    msg = Message(
        subject,
        sender=sender,
        recipients=recipients,
    )
    msg.text = text_body
    msg.html = html_body
    mail.send(msg)
    
def send_verification_email(user):
    token = user.generate_token()
    print(token)
    subject = '[FlaskBlog] User Verification'
    sender = app.config['ADMINS'][0]
    recipients = user.email
    text_body = render_template('emails/verification.txt', user=user, token=token)
    html_body = render_template('emails/verification.html', user=user, token=token)
    
    send_mail(subject, sender, recipients, text_body, html_body)

def after_register(user):
    
    folder_url = basedir+ '/app' + url_for('static', filename=f'img/{user.username}')
    
    if not os.path.isdir(folder_url):
        subprocess.run(['mkdir', folder_url])
        subprocess.run(['mkdir', folder_url + '/profile'])
        subprocess.run(['mkdir', folder_url + '/posts'])
        
    print(os.path.isdir(folder_url))
    

def save_profile_pic(form_profile_pic, user):
    token = str(secrets.token_hex(10))
    _, pic_ext = os.path.splitext(form_profile_pic.filename)
    profile_pic_name = token + pic_ext
    profile_pic_path = os.path.join(app.root_path, f'static/img/{user.username}/profile/', profile_pic_name)
    
    output_size = (125,125)
    i = Image.open(form_profile_pic)
    i.thumbnail(output_size)
    i.save(profile_pic_path)

    return profile_pic_name    