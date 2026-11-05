from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, TextAreaField, BooleanField,
    SelectField, SubmitField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, ValidationError,
    Regexp, Optional
)
from models import User, Category


class RegistrationForm(FlaskForm):
    """User account registration form."""
    username = StringField('Username', validators=[
        DataRequired(message="Username is required."),
        Length(min=3, max=30, message="Username must be between 3 and 30 characters."),
        Regexp(r'^[a-zA-Z0-9_]+$', message="Username can only contain letters, numbers, and underscores.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email address is required."),
        Email(message="Please enter a valid email address."),
        Length(max=120)
    ])
    full_name = StringField('Full Name', validators=[
        Optional(),
        Length(max=80, message="Full name cannot exceed 80 characters.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, max=100, message="Password must be at least 6 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords do not match.")
    ])
    submit = SubmitField('Create Account')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.strip()).first()
        if user:
            raise ValidationError('This username is already taken. Please choose another.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.strip().lower()).first()
        if user:
            raise ValidationError('An account with this email already exists.')


class LoginForm(FlaskForm):
    """User login form."""
    email_or_username = StringField('Email or Username', validators=[
        DataRequired(message="Please enter your email or username.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Please enter your password.")
    ])
    remember_me = BooleanField('Remember me on this device')
    submit = SubmitField('Sign In')


class ProfileForm(FlaskForm):
    """Profile editing form."""
    full_name = StringField('Full Name', validators=[
        Optional(),
        Length(max=80, message="Full name cannot exceed 80 characters.")
    ])
    bio = TextAreaField('About You / Bio', validators=[
        Optional(),
        Length(max=500, message="Bio cannot exceed 500 characters.")
    ])
    profile_pic = FileField('Profile Avatar', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp', 'gif'], 'Images only (jpg, png, webp, gif).')
    ])
    submit = SubmitField('Save Changes')


class ChangePasswordForm(FlaskForm):
    """Password modification form."""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message="Current password is required.")
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message="New password is required."),
        Length(min=6, max=100, message="New password must be at least 6 characters.")
    ])
    confirm_new_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your new password."),
        EqualTo('new_password', message="New passwords do not match.")
    ])
    submit = SubmitField('Update Password')


class BlogPostForm(FlaskForm):
    """Create and edit blog post form."""
    title = StringField('Blog Title', validators=[
        DataRequired(message="Title is required."),
        Length(min=5, max=200, message="Title must be between 5 and 200 characters.")
    ])
    category_id = SelectField('Category', coerce=int, validators=[
        DataRequired(message="Please select a category.")
    ])
    summary = TextAreaField('Short Summary', validators=[
        DataRequired(message="Short summary is required."),
        Length(min=10, max=400, message="Summary must be between 10 and 400 characters.")
    ])
    content = TextAreaField('Blog Content', validators=[
        DataRequired(message="Blog content is required."),
        Length(min=20, message="Content must be at least 20 characters.")
    ])
    tags = StringField('Tags (comma-separated)', validators=[
        Optional(),
        Length(max=200, message="Tags cannot exceed 200 characters.")
    ])
    featured_image = FileField('Featured Cover Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp', 'gif'], 'Images only (jpg, png, webp, gif).')
    ])
    is_featured = BooleanField('Feature this post on homepage')
    submit = SubmitField('Publish Post')


class CommentForm(FlaskForm):
    """Blog post comment form."""
    content = TextAreaField('Add a comment...', validators=[
        DataRequired(message="Comment cannot be empty."),
        Length(min=2, max=1000, message="Comment must be between 2 and 1000 characters.")
    ])
    submit = SubmitField('Post Comment')


class CategoryForm(FlaskForm):
    """Category management form for Admin."""
    name = StringField('Category Name', validators=[
        DataRequired(message="Category name is required."),
        Length(min=2, max=50, message="Category name must be between 2 and 50 characters.")
    ])
    description = StringField('Description', validators=[
        Optional(),
        Length(max=255, message="Description cannot exceed 255 characters.")
    ])
    color = SelectField('Badge Theme Color', choices=[
        ('primary', 'Royal Blue (Primary)'),
        ('indigo', 'Indigo (Deep Purple)'),
        ('success', 'Emerald Green (Success)'),
        ('info', 'Sky Cyan (Info)'),
        ('warning', 'Amber Orange (Warning)'),
        ('danger', 'Crimson Red (Danger)'),
        ('dark', 'Dark Slate (Dark)')
    ], default='primary')
    submit = SubmitField('Save Category')


class ContactForm(FlaskForm):
    """Contact feedback form."""
    name = StringField('Your Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=80)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    subject = StringField('Subject', validators=[
        DataRequired(message="Subject is required."),
        Length(min=3, max=150)
    ])
    message = TextAreaField('Your Message', validators=[
        DataRequired(message="Message is required."),
        Length(min=10, max=2000, message="Message must be between 10 and 2000 characters.")
    ])
    submit = SubmitField('Send Message')
