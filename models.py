from datetime import datetime, timezone
import re
import math
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text or 'post'


class User(UserMixin, db.Model):
    """User model representing registered users and administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    full_name = db.Column(db.String(100), default='', nullable=False)
    bio = db.Column(db.Text, default='', nullable=False)
    profile_pic = db.Column(db.String(255), default='default-avatar.svg', nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    posts = db.relationship('BlogPost', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str):
        """Hash and set user password using pbkdf2:sha256."""
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password: str) -> bool:
        """Verify user password hash."""
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        """Check if user has administrative privileges."""
        return self.role == 'admin'

    @property
    def total_likes_received(self) -> int:
        """Calculate total likes received across all user's blog posts."""
        return sum(post.likes.count() for post in self.posts)

    def to_dict(self) -> dict:
        """Serialize user object to JSON-compatible dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'full_name': self.full_name,
            'bio': self.bio,
            'profile_pic': self.profile_pic,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'total_posts': self.posts.count(),
            'total_comments': self.comments.count(),
            'total_likes_received': self.total_likes_received
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


class Category(db.Model):
    """Category model for classifying blog posts."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), default='', nullable=False)
    color = db.Column(db.String(30), default='primary', nullable=False)  # Badge theme color
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    posts = db.relationship('BlogPost', backref='category', lazy='dynamic')

    def to_dict(self) -> dict:
        """Serialize category object to JSON-compatible dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'color': self.color,
            'post_count': self.posts.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Category {self.name}>'


class BlogPost(db.Model):
    """BlogPost model representing articles published on BlogSphere."""
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    summary = db.Column(db.String(400), nullable=False)
    content = db.Column(db.Text, nullable=False)
    featured_image = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tags = db.Column(db.String(255), default='', nullable=False)  # Comma-separated tags
    is_featured = db.Column(db.Boolean, default=False, nullable=False)
    views = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan', order_by='Comment.created_at.desc()')
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def read_time(self) -> int:
        """Estimate reading time in minutes based on average 200 words per minute."""
        words = len(re.findall(r'\w+', self.content or ''))
        return max(1, math.ceil(words / 200))

    @property
    def tag_list(self) -> list:
        """Return parsed tag strings stripped of whitespace."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

    def is_liked_by(self, user) -> bool:
        """Check if a specific user has liked this blog post."""
        if not user or not user.is_authenticated:
            return False
        return self.likes.filter_by(user_id=user.id).first() is not None

    @property
    def total_likes(self) -> int:
        """Total number of likes for this post."""
        return self.likes.count()

    @property
    def total_comments(self) -> int:
        """Total number of comments on this post."""
        return self.comments.count()

    def to_dict(self, include_content: bool = True) -> dict:
        """Serialize blog post to JSON-compatible dictionary."""
        data = {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'summary': self.summary,
            'featured_image': self.featured_image,
            'category': {
                'id': self.category.id,
                'name': self.category.name,
                'slug': self.category.slug,
                'color': self.category.color
            } if self.category else None,
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'full_name': self.author.full_name,
                'profile_pic': self.author.profile_pic
            } if self.author else None,
            'tags': self.tag_list,
            'is_featured': self.is_featured,
            'views': self.views,
            'likes_count': self.total_likes,
            'comments_count': self.total_comments,
            'read_time': self.read_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_content:
            data['content'] = self.content
        return data

    def __repr__(self):
        return f'<BlogPost {self.title}>'


class Comment(db.Model):
    """Comment model for blog discussions."""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize comment object to JSON-compatible dictionary."""
        return {
            'id': self.id,
            'content': self.content,
            'post_id': self.post_id,
            'user_id': self.user_id,
            'author': {
                'id': self.author.id,
                'username': self.author.username,
                'full_name': self.author.full_name,
                'profile_pic': self.author.profile_pic,
                'role': self.author.role
            } if self.author else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Comment {self.id} on Post {self.post_id}>'


class Like(db.Model):
    """Like model recording user appreciation for blog posts."""
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', name='uq_post_user_like'),
    )

    def to_dict(self) -> dict:
        """Serialize like object to JSON-compatible dictionary."""
        return {
            'id': self.id,
            'post_id': self.post_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Like User {self.user_id} -> Post {self.post_id}>'
