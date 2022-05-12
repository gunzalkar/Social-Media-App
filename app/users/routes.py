from flask import render_template, url_for, redirect, flash, request
from app.users import users
from app.users.utils import send_verification_email
from app import db, app, moment
from flask_login import login_user, current_user, logout_user, login_required
from app.users.forms import LoginForm, RegistrationForm, EmptyForm, EditProfileForm
from app.models import User
from werkzeug.urls import url_parse
from app.users.utils import generate_verification_code, after_register, save_profile_pic
import subprocess
import os
from datetime import datetime


@users.before_app_request
def check_confirmation_before_app_request():
    if current_user.is_authenticated: 
        current_user.last_seen = datetime.utcnow()
        if not current_user.is_verified \
     and request.blueprint != 'users' and request.endpoint != 'static':
            return redirect(url_for(verification_pending, username=current_user.username))


# -------------------------------- ALL USERS -----------------------------------------------------


@users.route('/users/all')
@login_required
def all_users():
    all_users = User.query.all()
    return render_template('users/all_users.html', title='All Users', all_users=all_users)

# -------------------------------- LOGIN -----------------------------------------------------


@users.route('/users/login', methods=['GET', 'POST'])
def login():
    
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user is None or not user.verify_password(form.password.data):
            flash('Invalid Credentials. Please re-enter', 'danger')
            return redirect(url_for('users.login'))
        
        login_user(user, remember=form.remember_me.data)
        if not user.is_verified:
            next_url = url_for('users.verification_pending', username=user.username)
        else:
            next_url = request.args.get('next')
        
        if not next_url or url_parse(next_url).netloc != '':
            if not user.is_verified:
                next_url = url_for('users.verification_pending', username=user.username)
            else:
                next_url = url_for('main.index')
                
        flash('Login Successfull', 'success')
        return redirect(next_url)

    return render_template('users/login.html', title='Login', form=form)



# -------------------------------- REGISTER -----------------------------------------------------



@users.route('/users/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            fname = form.fname.data,
            lname = form.lname.data,
            username = form.username.data,
            email = form.email.data,
            about_me = form.about_me.data
        )
        after_register(user)
        
        if form.profile_pic.data:
            profile_pic_name = save_profile_pic(form.profile_pic.data, user)
            user.profile_pic = profile_pic_name
            
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        send_verification_email(user)
        flash('Congratulations. You are now a registered user.', 'success')
        return redirect(url_for('users.login'))
    
    return render_template('users/register.html', title='Register', form=form)



# -------------------------------- LOGOUT -----------------------------------------------------


@users.route('/users/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out of session.', 'info')
    return redirect(url_for('main.index'))



# -------------------------------- VERIFICATION PENDING -----------------------------------------------


@users.route('/users/<username>/verification_pending', methods=['GET', 'POST'])
@login_required
def verification_pending(username):
    user = User.query.filter_by(username=username).first()
    
    if user.is_verified:
        flash('User already verified', 'info')
        return redirect(url_for('main.index'))
    
    form = EmptyForm()
    if form.validate_on_submit():
        send_verification_email(user)
        flash('Verification Email sent. Please check your inbox', 'success')
        return redirect(url_for('users.verification_pending', username=user.username))
    
    return render_template('users/verification_pending.html',title='Verify User', user=user, form=form)



# -------------------------------- VERIFY -----------------------------------------------------


@users.route('/users/<username>/verify/<token>')
@login_required
def verify_user(username, token):
    user = User.verify_token(token)
    if user is None:
        flash('Sorry. Invalid Token', 'info')
        return redirect(url_for('users.verification_pending', username=username))
    
    if user.is_verified:
        flash('You are already verified', 'info')
        return redirect(url_for('users.profile', username=user.username))
    user.is_verified = True
    db.session.commit()
    flash('User Verified', 'info')
    return redirect(url_for('main.index'))


# -------------------------------- PROFILE -----------------------------------------------------


@users.route('/users/<username>/profile', methods=['GET', 'POST'])
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(f'No user found with username {username}', 'info')
        return redirect(url_for('main.index'))
    
    accept_form = EmptyForm()   
    reject_form = EmptyForm()
    cancel_request_form = EmptyForm()
    remove_friend_form = EmptyForm()
    send_request_form = EmptyForm()
    
    if user == current_user:
        form = EditProfileForm()
        if form.validate_on_submit():
            
            if form.profile_pic.data:
                old_profile_pic = user.profile_pic
                profile_pic_name = save_profile_pic(form.profile_pic.data, user)
                user.profile_pic = profile_pic_name
                old_profile_pic_path = os.path.join(app.root_path, f'static/img/{user.username}/profile/', old_profile_pic)
                print(old_profile_pic_path)
                subprocess.run(['rm', old_profile_pic_path])
            
            user.username = form.username.data
            user.email = form.email.data
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('users.profile', username=username))

        else:
            form.username.data = user.username
            form.email.data = user.email
    else:
        form=None
    
    if user.profile_pic != 'default.jpg':
        image_src = url_for('static', filename=f'img/{user.username}/profile/{user.profile_pic}')
    else:
        image_src = None
    
    return render_template('users/profile.html', 
                           user=user, 
                           form=form, 
                           image_src=image_src, 
                           accept_form=accept_form, 
                           reject_form=reject_form,
                           cancel_request_form=cancel_request_form,
                           remove_friend_form=remove_friend_form,
                           send_request_form=send_request_form
                           )


# -------------------------------- VIEW REQUESTS -----------------------------------------------------

@users.route('/users/<username>/requests')
@login_required
def view_requests(username):
    
    user = User.query.filter_by(username=username).first()
    
    if user is None:
            flash(f'No user found with username: {username}', 'info')
            return redirect(url_for('users.profile', username=current_user.username))
    if user == current_user:
        accept_form = EmptyForm()
        reject_form = EmptyForm()
        pending_requests = user.requests.all()
        
        return render_template('users/requests.html', 
                            title='requests', 
                            user=user,
                            pending_requests=pending_requests,
                            accept_form = accept_form,
                            reject_form = reject_form
                            )
    else:
        flash('Access denied', 'danger')
        return redirect(url_for('users.profile', username=current_user.username))


# -------------------------------- SEND REQUEST -----------------------------------------------------

@users.route('/users/<username>/send_request', methods=['POST'])
@login_required
def send_request(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            flash(f'No user found with username: {username}', 'info')
            return redirect(url_for('users.profile', username=current_user.username))
        
        if user == current_user:
            flash('Sorry, you cannot send yourself a friend request', 'info')
            return redirect(url_for('users.profile', username=current_user.username))
        
        current_user.send_request(user)
        db.session.commit()
        flash('Request sent successfully', 'success')
        return redirect(url_for('users.profile', username=user.username))
    else:
        return redirect(url_for('main.index'))
    
    
# -------------------------------- CANCEL REQUEST -----------------------------------------------------

    
    
@users.route('/users/<username>/cancel_request', methods=['POST'])
@login_required
def cancel_request(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        
        if user is None:
            flash(f'No user found with username: {username}', 'info')
            return redirect(url_for('users.profile', username=current_user.username))
        
        if user == current_user:
            flash('Sorry, you cannot send yourself a friend request', 'info')
            return redirect(url_for('users.profile', username=current_user.username))
        
        current_user.cancel_request(user)
        db.session.commit()
        flash('Request cancelled', 'info')
        return redirect(url_for('users.profile', username=user.username))
    else:
        return redirect(url_for('main.index'))
    
    
# -------------------------------- ACCEPT REQUEST -----------------------------------------------------

@users.route('/users/<username>/accept_request/<sender_username>', methods=['POST'])
@login_required
def accept_request(username, sender_username):
    accept_form = EmptyForm()
    if accept_form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(f'No user found with username: {username}', 'info')
            return redirect(url_for('main_index'))
        sender_user = User.query.filter_by(username=sender_username).first()
        if sender_user is None:
            flash(f'No user found with username: {sender_username}', 'info')
            return redirect(url_for('main_index'))
        
        if user == current_user:
            if sender_user == user:
                flash(f'Invalid Operation', 'danger')
                return redirect(url_for('main_index'))
            
            if sender_user.has_requested(user):
                sender_user.cancel_request(user)
                user.make_friend(sender_user)
                db.session.commit()
                flash(f'You are now friends with {sender_user.fname} {sender_user.lname}', 'success')
                return redirect(url_for('users.profile', username=sender_username))
            else:
                flash(f'No request from {sender_username} to You', 'info')
        else:
            flash('Invalid operation', 'danger')
            return redirect(url_for('main.index'))