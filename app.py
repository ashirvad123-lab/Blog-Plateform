import os
import uuid
from functools import wraps
from datetime import datetime, timezone

from flask import (
    Flask, Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, abort, session
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc, func

from config import config_by_name, Config
from models import db, User, Category, BlogPost, Comment, Like, slugify
from forms import (
    RegistrationForm, LoginForm, ProfileForm, ChangePasswordForm,
    BlogPostForm, CommentForm, CategoryForm, ContactForm
)

login_manager = LoginManager()
csrf = CSRFProtect()
api_bp = Blueprint('api', __name__, url_prefix='/api')


def create_app(config_name=None):
    """Application factory for BlogSphere."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, Config))

    # Ensure upload and instance directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Configure login manager
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please sign in to access this page.'
    login_manager.login_message_category = 'warning'

    # Register API blueprint and exempt it from CSRF
    csrf.exempt(api_bp)
    app.register_blueprint(api_bp)

    # Register web route handlers
    register_web_routes(app)

    return app


# --------------------------------------------------------------------------
# Authentication Helpers & Decorators
# --------------------------------------------------------------------------
@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))


def admin_required(f):
    """Decorator to restrict route access exclusively to administrators."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.path))
        if not current_user.is_admin():
            flash('Access denied. Administrator privileges required.', 'danger')
            return render_template('errors/403.html'), 403
        return f(*args, **kwargs)
    return decorated_function


def save_upload_image(file_storage, upload_folder) -> str | None:
    """Safely sanitize, rename, and save an uploaded image file."""
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if '.' not in filename:
        return None

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        return None

    unique_filename = f"{uuid.uuid4().hex}_{int(datetime.now().timestamp())}.{ext}"
    target_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(target_path)
    return unique_filename


# --------------------------------------------------------------------------
# Route Registration
# --------------------------------------------------------------------------
def register_web_routes(app: Flask):

    # Context Processors for Templates
    @app.context_processor
    def inject_global_data():
        try:
            cats = Category.query.order_by(Category.name.asc()).all()
        except Exception:
            cats = []
        return {
            'global_categories': cats,
            'current_year': datetime.now().year
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Resource not found', 'status': 404}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(e):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden: Access denied', 'status': 403}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error', 'status': 500}), 500
        return render_template('errors/500.html'), 500

    # ----------------------------------------------------------------------
    # Web Routes: Public Pages & Auth
    # ----------------------------------------------------------------------
    @app.route('/')
    def index():
        """Homepage: Hero, search, featured blogs, latest blogs, categories, popular."""
        featured_posts = BlogPost.query.filter_by(is_featured=True)\
            .order_by(BlogPost.created_at.desc()).limit(4).all()

        latest_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(6).all()
        categories = Category.query.all()

        # Popular posts determined by views & like counts
        popular_posts = BlogPost.query.order_by(BlogPost.views.desc(), BlogPost.created_at.desc()).limit(5).all()

        return render_template(
            'index.html',
            featured_posts=featured_posts,
            latest_posts=latest_posts,
            categories=categories,
            popular_posts=popular_posts
        )

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration endpoint."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = RegistrationForm()
        if form.validate_on_submit():
            # Check duplicate email or username explicitly as secondary safety
            existing_user = User.query.filter(
                or_(User.username == form.username.data.strip(),
                    User.email == form.email.data.strip().lower())
            ).first()

            if existing_user:
                flash('An account with this username or email already exists.', 'danger')
                return render_template('register.html', form=form)

            # Assign first user as admin if no users exist yet
            is_first_user = User.query.count() == 0
            role = 'admin' if is_first_user else 'user'

            new_user = User(
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                full_name=form.full_name.data.strip() if form.full_name.data else '',
                role=role
            )
            new_user.set_password(form.password.data)

            db.session.add(new_user)
            db.session.commit()

            flash('Registration successful! Please sign in with your credentials.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login endpoint."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        form = LoginForm()
        if form.validate_on_submit():
            identifier = form.email_or_username.data.strip()
            user = User.query.filter(
                or_(User.email == identifier.lower(), User.username == identifier)
            ).first()

            if user and user.check_password(form.password.data):
                if not user.is_active:
                    flash('Your account has been deactivated. Please contact support.', 'danger')
                    return render_template('login.html', form=form)

                login_user(user, remember=form.remember_me.data)
                flash(f'Welcome back, {user.full_name or user.username}!', 'success')

                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('dashboard')
                return redirect(next_page)
            else:
                flash('Invalid username/email or password. Please try again.', 'danger')

        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        """User logout endpoint."""
        logout_user()
        flash('You have been signed out successfully.', 'info')
        return redirect(url_for('index'))

    @app.route('/about')
    def about():
        """About Us page."""
        return render_template('about.html')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        """Contact Us page."""
        form = ContactForm()
        if form.validate_on_submit():
            flash('Thank you for reaching out! Your message has been received.', 'success')
            return redirect(url_for('contact'))
        return render_template('contact.html', form=form)

    # ----------------------------------------------------------------------
    # Web Routes: Blogs Listing, Details & Management
    # ----------------------------------------------------------------------
    @app.route('/blogs')
    def blogs():
        """All Blogs listing with search, category filtering, sorting, and pagination."""
        query_text = request.args.get('q', '').strip()
        category_slug = request.args.get('category', '').strip()
        sort_by = request.args.get('sort', 'latest').strip()
        page = request.args.get('page', 1, type=int)
        per_page = app.config.get('POSTS_PER_PAGE', 6)

        posts_query = BlogPost.query

        # Filter by Search Query
        if query_text:
            posts_query = posts_query.filter(
                or_(
                    BlogPost.title.ilike(f'%{query_text}%'),
                    BlogPost.content.ilike(f'%{query_text}%'),
                    BlogPost.summary.ilike(f'%{query_text}%'),
                    BlogPost.tags.ilike(f'%{query_text}%')
                )
            )

        # Filter by Category Slug
        current_category = None
        if category_slug:
            current_category = Category.query.filter_by(slug=category_slug).first()
            if current_category:
                posts_query = posts_query.filter(BlogPost.category_id == current_category.id)

        # Sorting
        if sort_by == 'popular':
            # Subquery or outer join to order by like counts
            posts_query = posts_query.outerjoin(Like).group_by(BlogPost.id)\
                .order_by(func.count(Like.id).desc(), BlogPost.created_at.desc())
        elif sort_by == 'views':
            posts_query = posts_query.order_by(BlogPost.views.desc(), BlogPost.created_at.desc())
        elif sort_by == 'oldest':
            posts_query = posts_query.order_by(BlogPost.created_at.asc())
        else:
            # Default: latest
            posts_query = posts_query.order_by(BlogPost.created_at.desc())

        posts = posts_query.paginate(page=page, per_page=per_page, error_out=False)
        categories = Category.query.order_by(Category.name.asc()).all()

        return render_template(
            'blogs.html',
            posts=posts,
            categories=categories,
            query=query_text,
            current_category=current_category,
            sort_by=sort_by
        )

    @app.route('/blog/<slug>')
    def blog_detail(slug):
        """Single blog post detail page."""
        post = BlogPost.query.filter_by(slug=slug).first_or_404()

        # Increment view count (track per session to prevent rapid refresh abuse)
        viewed_posts = session.get('viewed_posts', [])
        if post.id not in viewed_posts:
            post.views += 1
            db.session.commit()
            viewed_posts.append(post.id)
            session['viewed_posts'] = viewed_posts

        comment_form = CommentForm()
        comments = post.comments.order_by(Comment.created_at.desc()).all()

        # Related posts in same category
        related_posts = BlogPost.query.filter(
            BlogPost.category_id == post.category_id,
            BlogPost.id != post.id
        ).order_by(BlogPost.created_at.desc()).limit(2).all()

        return render_template(
            'blog_detail.html',
            post=post,
            comment_form=comment_form,
            comments=comments,
            related_posts=related_posts
        )

    @app.route('/create-blog', methods=['GET', 'POST'])
    @login_required
    def create_blog():
        """Create new blog post."""
        form = BlogPostForm()
        # Populate category choices
        form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name.asc()).all()]

        if not form.category_id.choices:
            flash('Please create at least one category before publishing a blog.', 'warning')
            return redirect(url_for('dashboard'))

        if form.validate_on_submit():
            # Generate a unique slug
            base_slug = slugify(form.title.data)
            unique_slug = base_slug
            counter = 1
            while BlogPost.query.filter_by(slug=unique_slug).first() is not None:
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Handle featured cover image upload
            image_filename = None
            if form.featured_image.data:
                image_filename = save_upload_image(form.featured_image.data, app.config['UPLOAD_FOLDER'])

            # Only admin can feature a post directly
            is_featured = form.is_featured.data if current_user.is_admin() else False

            post = BlogPost(
                title=form.title.data.strip(),
                slug=unique_slug,
                category_id=form.category_id.data,
                summary=form.summary.data.strip(),
                content=form.content.data.strip(),
                tags=form.tags.data.strip() if form.tags.data else '',
                featured_image=image_filename,
                is_featured=is_featured,
                author=current_user
            )

            db.session.add(post)
            db.session.commit()

            flash('Your article has been published successfully!', 'success')
            return redirect(url_for('blog_detail', slug=post.slug))

        return render_template('create_blog.html', form=form)

    @app.route('/edit-blog/<int:post_id>', methods=['GET', 'POST'])
    @login_required
    def edit_blog(post_id):
        """Edit an existing blog post (Author or Admin only)."""
        post = BlogPost.query.get_or_404(post_id)

        # Authorization: Author or Admin
        if post.user_id != current_user.id and not current_user.is_admin():
            flash('You do not have permission to edit this post.', 'danger')
            return render_template('errors/403.html'), 403

        form = BlogPostForm(obj=post)
        form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name.asc()).all()]

        if form.validate_on_submit():
            post.title = form.title.data.strip()
            post.category_id = form.category_id.data
            post.summary = form.summary.data.strip()
            post.content = form.content.data.strip()
            post.tags = form.tags.data.strip() if form.tags.data else ''

            if current_user.is_admin():
                post.is_featured = form.is_featured.data

            # Handle image replacement
            if form.featured_image.data:
                new_image = save_upload_image(form.featured_image.data, app.config['UPLOAD_FOLDER'])
                if new_image:
                    post.featured_image = new_image

            post.updated_at = datetime.now(timezone.utc)
            db.session.commit()

            flash('Article updated successfully!', 'success')
            return redirect(url_for('blog_detail', slug=post.slug))

        return render_template('edit_blog.html', form=form, post=post)

    @app.route('/delete-blog/<int:post_id>', methods=['POST'])
    @login_required
    def delete_blog(post_id):
        """Delete an existing blog post (Author or Admin only)."""
        post = BlogPost.query.get_or_404(post_id)

        # Authorization: Author or Admin
        if post.user_id != current_user.id and not current_user.is_admin():
            flash('You do not have permission to delete this post.', 'danger')
            return render_template('errors/403.html'), 403

        post_title = post.title
        db.session.delete(post)
        db.session.commit()

        flash(f'Post "{post_title}" was deleted permanently.', 'info')
        return redirect(url_for('my_blogs'))

    # ----------------------------------------------------------------------
    # Web Routes: Comments & Likes
    # ----------------------------------------------------------------------
    @app.route('/blog/<int:post_id>/comment', methods=['POST'])
    @login_required
    def add_comment(post_id):
        """Add comment to a blog post."""
        post = BlogPost.query.get_or_404(post_id)
        form = CommentForm()

        if form.validate_on_submit():
            comment = Comment(
                content=form.content.data.strip(),
                post_id=post.id,
                user_id=current_user.id
            )
            db.session.add(comment)
            db.session.commit()
            flash('Your comment has been added!', 'success')
        else:
            flash('Failed to submit comment. Please ensure it is between 2 and 1000 characters.', 'danger')

        return redirect(url_for('blog_detail', slug=post.slug) + '#comments-section')

    @app.route('/comment/<int:comment_id>/edit', methods=['POST'])
    @login_required
    def edit_comment(comment_id):
        """Edit a comment (Author only)."""
        comment = Comment.query.get_or_404(comment_id)

        if comment.user_id != current_user.id and not current_user.is_admin():
            flash('Permission denied to edit this comment.', 'danger')
            return redirect(url_for('blog_detail', slug=comment.post.slug))

        content = request.form.get('content', '').strip()
        if not content or len(content) < 2 or len(content) > 1000:
            flash('Comment must be between 2 and 1000 characters.', 'danger')
        else:
            comment.content = content
            comment.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            flash('Comment updated successfully.', 'success')

        return redirect(url_for('blog_detail', slug=comment.post.slug) + f'#comment-{comment.id}')

    @app.route('/comment/<int:comment_id>/delete', methods=['POST'])
    @login_required
    def delete_comment(comment_id):
        """Delete a comment (Author or Admin only)."""
        comment = Comment.query.get_or_404(comment_id)

        if comment.user_id != current_user.id and not current_user.is_admin():
            flash('Permission denied to delete this comment.', 'danger')
            return redirect(url_for('blog_detail', slug=comment.post.slug))

        post_slug = comment.post.slug
        db.session.delete(comment)
        db.session.commit()

        flash('Comment deleted successfully.', 'info')
        # If redirected from my_comments view or admin view, redirect accordingly
        referrer = request.referrer or ''
        if 'my-comments' in referrer:
            return redirect(url_for('my_comments'))
        elif 'admin' in referrer:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('blog_detail', slug=post_slug) + '#comments-section')

    @app.route('/blog/<int:post_id>/like', methods=['POST'])
    @login_required
    def toggle_like(post_id):
        """Toggle like/unlike for a blog post."""
        post = BlogPost.query.get_or_404(post_id)
        existing_like = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first()

        if existing_like:
            db.session.delete(existing_like)
            db.session.commit()
            liked = False
        else:
            new_like = Like(post_id=post.id, user_id=current_user.id)
            db.session.add(new_like)
            db.session.commit()
            liked = True

        total_likes = post.total_likes

        # Return JSON if AJAX request
        if request.is_json or request.headers.get('Accept') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'status': 'success',
                'liked': liked,
                'total_likes': total_likes,
                'post_id': post.id
            })

        return redirect(url_for('blog_detail', slug=post.slug))

    # ----------------------------------------------------------------------
    # Web Routes: User Dashboard, My Blogs, My Comments, Profile
    # ----------------------------------------------------------------------
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """User personal dashboard overview."""
        total_posts = current_user.posts.count()
        total_likes_received = current_user.total_likes_received
        total_comments = current_user.comments.count()

        recent_posts = current_user.posts.order_by(BlogPost.created_at.desc()).limit(5).all()
        recent_comments = current_user.comments.order_by(Comment.created_at.desc()).limit(5).all()

        return render_template(
            'dashboard.html',
            total_posts=total_posts,
            total_likes_received=total_likes_received,
            total_comments=total_comments,
            recent_posts=recent_posts,
            recent_comments=recent_comments
        )

    @app.route('/my-blogs')
    @login_required
    def my_blogs():
        """User's blog management page."""
        page = request.args.get('page', 1, type=int)
        per_page = 10
        posts = current_user.posts.order_by(BlogPost.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return render_template('my_blogs.html', posts=posts)

    @app.route('/my-comments')
    @login_required
    def my_comments():
        """User's comments management page."""
        page = request.args.get('page', 1, type=int)
        per_page = 10
        comments = current_user.comments.order_by(Comment.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return render_template('my_comments.html', comments=comments)

    @app.route('/profile', methods=['GET', 'POST'])
    @login_required
    def profile():
        """User profile update page."""
        profile_form = ProfileForm(obj=current_user)
        password_form = ChangePasswordForm()

        if request.method == 'POST' and request.form.get('form_type') == 'profile':
            if profile_form.validate_on_submit():
                current_user.full_name = profile_form.full_name.data.strip() if profile_form.full_name.data else ''
                current_user.bio = profile_form.bio.data.strip() if profile_form.bio.data else ''

                if profile_form.profile_pic.data:
                    new_pic = save_upload_image(profile_form.profile_pic.data, app.config['UPLOAD_FOLDER'])
                    if new_pic:
                        current_user.profile_pic = new_pic

                db.session.commit()
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('profile'))

        return render_template(
            'profile.html',
            profile_form=profile_form,
            password_form=password_form
        )

    @app.route('/change-password', methods=['POST'])
    @login_required
    def change_password():
        """Handle password updates from profile page."""
        password_form = ChangePasswordForm()
        profile_form = ProfileForm(obj=current_user)

        if password_form.validate_on_submit():
            if not current_user.check_password(password_form.current_password.data):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html', profile_form=profile_form, password_form=password_form)

            current_user.set_password(password_form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully.', 'success')
            return redirect(url_for('profile'))

        flash('Password update failed. Please check the errors below.', 'danger')
        return render_template('profile.html', profile_form=profile_form, password_form=password_form)

    # ----------------------------------------------------------------------
    # Web Routes: Administrator Panel & Moderation
    # ----------------------------------------------------------------------
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        """Admin control panel displaying metrics and moderation tabs."""
        total_users = User.query.count()
        active_users_count = User.query.filter_by(is_active=True).count()
        total_posts = BlogPost.query.count()
        featured_posts_count = BlogPost.query.filter_by(is_featured=True).count()
        total_comments = Comment.query.count()
        total_likes = Like.query.count()

        users = User.query.order_by(User.created_at.desc()).all()
        posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
        comments = Comment.query.order_by(Comment.created_at.desc()).all()
        categories = Category.query.order_by(Category.name.asc()).all()

        return render_template(
            'admin_dashboard.html',
            total_users=total_users,
            active_users_count=active_users_count,
            total_posts=total_posts,
            featured_posts_count=featured_posts_count,
            total_comments=total_comments,
            total_likes=total_likes,
            users=users,
            posts=posts,
            comments=comments,
            categories=categories
        )

    @app.route('/admin/user/<int:user_id>/toggle-status', methods=['POST'])
    @admin_required
    def admin_toggle_user_status(user_id):
        """Activate or suspend user account."""
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot deactivate your own administrative account.', 'warning')
            return redirect(url_for('admin_dashboard'))

        user.is_active = not user.is_active
        db.session.commit()
        status_text = 'activated' if user.is_active else 'suspended'
        flash(f'User "{user.username}" has been {status_text}.', 'info')
        return redirect(url_for('admin_dashboard') + '#users')

    @app.route('/admin/user/<int:user_id>/toggle-role', methods=['POST'])
    @admin_required
    def admin_toggle_user_role(user_id):
        """Toggle user role between Admin and User."""
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot demote your own administrator role.', 'warning')
            return redirect(url_for('admin_dashboard'))

        user.role = 'user' if user.role == 'admin' else 'admin'
        db.session.commit()
        flash(f'User "{user.username}" role updated to {user.role.upper()}.', 'info')
        return redirect(url_for('admin_dashboard') + '#users')

    @app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_user(user_id):
        """Permanently delete user and their associated content."""
        user = User.query.get_or_404(user_id)
        if user.id == current_user.id:
            flash('You cannot delete your own administrative account.', 'warning')
            return redirect(url_for('admin_dashboard'))

        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{username}" and all their posts/comments were permanently deleted.', 'info')
        return redirect(url_for('admin_dashboard') + '#users')

    @app.route('/admin/post/<int:post_id>/toggle-feature', methods=['POST'])
    @admin_required
    def admin_toggle_feature_post(post_id):
        """Toggle featured status of an article."""
        post = BlogPost.query.get_or_404(post_id)
        post.is_featured = not post.is_featured
        db.session.commit()
        status = 'featured on homepage' if post.is_featured else 'removed from featured'
        flash(f'Post "{post.title}" is now {status}.', 'info')
        return redirect(url_for('admin_dashboard') + '#posts')

    @app.route('/admin/category/create', methods=['POST'])
    @admin_required
    def admin_create_category():
        """Create a new blog category."""
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        color = request.form.get('color', 'primary').strip()

        if not name or len(name) < 2 or len(name) > 50:
            flash('Category name must be between 2 and 50 characters.', 'danger')
            return redirect(url_for('admin_dashboard') + '#categories')

        existing = Category.query.filter(Category.name.ilike(name)).first()
        if existing:
            flash(f'Category "{name}" already exists.', 'warning')
            return redirect(url_for('admin_dashboard') + '#categories')

        base_slug = slugify(name)
        unique_slug = base_slug
        counter = 1
        while Category.query.filter_by(slug=unique_slug).first() is not None:
            unique_slug = f"{base_slug}-{counter}"
            counter += 1

        new_cat = Category(name=name, slug=unique_slug, description=description, color=color)
        db.session.add(new_cat)
        db.session.commit()

        flash(f'Category "{name}" created successfully.', 'success')
        return redirect(url_for('admin_dashboard') + '#categories')

    @app.route('/admin/category/<int:category_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_category(category_id):
        """Delete an empty category."""
        category = Category.query.get_or_404(category_id)
        if category.posts.count() > 0:
            flash(f'Cannot delete category "{category.name}" because it contains {category.posts.count()} articles.', 'danger')
            return redirect(url_for('admin_dashboard') + '#categories')

        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category.name}" deleted.', 'info')
        return redirect(url_for('admin_dashboard') + '#categories')

    # ----------------------------------------------------------------------
    # Web Routes registration completed in register_web_routes
    # ----------------------------------------------------------------------


# --------------------------------------------------------------------------
# RESTful API Endpoints (Blueprint with url_prefix='/api')
# Automatically exempt from CSRF
# --------------------------------------------------------------------------

# 1. API Auth
@api_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip()

    if not username or not email or not password:
        return jsonify({'error': 'username, email, and password are required', 'status': 400}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters', 'status': 400}), 400

    if User.query.filter(or_(User.username == username, User.email == email)).first():
        return jsonify({'error': 'Username or email already in use', 'status': 409}), 409

    is_first = User.query.count() == 0
    user = User(username=username, email=email, full_name=full_name, role='admin' if is_first else 'user')
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }), 201


@api_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    identifier = (data.get('email_or_username') or data.get('username') or data.get('email') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'error': 'Identifier and password are required', 'status': 400}), 400

    user = User.query.filter(
        or_(User.email == identifier.lower(), User.username == identifier)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials', 'status': 401}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is inactive', 'status': 403}), 403

    login_user(user)
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200


@api_bp.route('/logout', methods=['POST'])
def api_logout():
    if current_user.is_authenticated:
        logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200


@api_bp.route('/me', methods=['GET'])
def api_me():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Unauthorized', 'status': 401}), 401
    return jsonify(current_user.to_dict()), 200


# 2. API Blog Posts
@api_bp.route('/posts', methods=['GET'])
def api_get_posts():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    query_text = request.args.get('search', '').strip()
    cat_slug = request.args.get('category', '').strip()

    posts_query = BlogPost.query
    if query_text:
        posts_query = posts_query.filter(
            or_(BlogPost.title.ilike(f'%{query_text}%'), BlogPost.content.ilike(f'%{query_text}%'))
        )
    if cat_slug:
        cat = Category.query.filter_by(slug=cat_slug).first()
        if cat:
            posts_query = posts_query.filter(BlogPost.category_id == cat.id)

    paginated = posts_query.order_by(BlogPost.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'total': paginated.total,
        'page': paginated.page,
        'pages': paginated.pages,
        'posts': [p.to_dict(include_content=False) for p in paginated.items]
    }), 200


@api_bp.route('/posts/<int:post_id>', methods=['GET'])
def api_get_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return jsonify(post.to_dict(include_content=True)), 200


@api_bp.route('/posts', methods=['POST'])
def api_create_post():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    summary = (data.get('summary') or '').strip()
    content = (data.get('content') or '').strip()
    category_id = data.get('category_id')
    tags = (data.get('tags') or '').strip()

    if not title or not summary or not content or not category_id:
        return jsonify({'error': 'title, summary, content, and category_id are required', 'status': 400}), 400

    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({'error': 'Invalid category_id', 'status': 400}), 400

    base_slug = slugify(title)
    unique_slug = base_slug
    counter = 1
    while BlogPost.query.filter_by(slug=unique_slug).first() is not None:
        unique_slug = f"{base_slug}-{counter}"
        counter += 1

    post = BlogPost(
        title=title,
        slug=unique_slug,
        summary=summary,
        content=content,
        category_id=category_id,
        tags=tags,
        author=current_user,
        is_featured=bool(data.get('is_featured', False)) if current_user.is_admin() else False
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({
        'message': 'Post created successfully',
        'post': post.to_dict()
    }), 201


@api_bp.route('/posts/<int:post_id>', methods=['PUT', 'PATCH'])
def api_update_post(post_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    post = BlogPost.query.get_or_404(post_id)
    if post.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden: You do not own this post', 'status': 403}), 403

    data = request.get_json() or {}
    if 'title' in data and data['title'].strip():
        post.title = data['title'].strip()
    if 'summary' in data and data['summary'].strip():
        post.summary = data['summary'].strip()
    if 'content' in data and data['content'].strip():
        post.content = data['content'].strip()
    if 'category_id' in data:
        cat = db.session.get(Category, data['category_id'])
        if cat:
            post.category_id = cat.id
    if 'tags' in data:
        post.tags = data['tags'].strip()
    if 'is_featured' in data and current_user.is_admin():
        post.is_featured = bool(data['is_featured'])

    post.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'message': 'Post updated successfully',
        'post': post.to_dict()
    }), 200


@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
def api_delete_post(post_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    post = BlogPost.query.get_or_404(post_id)
    if post.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden: You do not own this post', 'status': 403}), 403

    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted successfully'}), 200


# 3. API Comments
@api_bp.route('/posts/<int:post_id>/comments', methods=['GET'])
def api_get_comments(post_id):
    post = BlogPost.query.get_or_404(post_id)
    comments = post.comments.order_by(Comment.created_at.desc()).all()
    return jsonify([c.to_dict() for c in comments]), 200


@api_bp.route('/posts/<int:post_id>/comments', methods=['POST'])
def api_add_comment(post_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    post = BlogPost.query.get_or_404(post_id)
    data = request.get_json() or {}
    content = (data.get('content') or '').strip()

    if not content or len(content) < 2:
        return jsonify({'error': 'Comment content must be at least 2 characters', 'status': 400}), 400

    comment = Comment(content=content, post_id=post.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()

    return jsonify({
        'message': 'Comment added successfully',
        'comment': comment.to_dict()
    }), 201


@api_bp.route('/comments/<int:comment_id>', methods=['PUT', 'PATCH'])
def api_update_comment(comment_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden: You do not own this comment', 'status': 403}), 403

    data = request.get_json() or {}
    content = (data.get('content') or '').strip()
    if not content or len(content) < 2:
        return jsonify({'error': 'Comment content must be at least 2 characters', 'status': 400}), 400

    comment.content = content
    comment.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        'message': 'Comment updated successfully',
        'comment': comment.to_dict()
    }), 200


@api_bp.route('/comments/<int:comment_id>', methods=['DELETE'])
def api_delete_comment(comment_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    comment = Comment.query.get_or_404(comment_id)
    if comment.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Forbidden: You do not own this comment', 'status': 403}), 403

    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': 'Comment deleted successfully'}), 200


# 4. API Like / Unlike
@api_bp.route('/posts/<int:post_id>/like', methods=['POST'])
def api_like_post(post_id):
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'status': 401}), 401

    post = BlogPost.query.get_or_404(post_id)
    existing = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        liked = False
    else:
        like = Like(post_id=post.id, user_id=current_user.id)
        db.session.add(like)
        db.session.commit()
        liked = True

    return jsonify({
        'post_id': post.id,
        'liked': liked,
        'total_likes': post.total_likes
    }), 200


# 5. API Categories
@api_bp.route('/categories', methods=['GET'])
def api_categories():
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify([c.to_dict() for c in categories]), 200


# Primary WSGI Application Instance
app = create_app()

if __name__ == '__main__':
    # Initialize DB tables automatically on local startup
    with app.app_context():
        db.create_all()
    app.run(host='127.0.0.1', port=5000, debug=True)
