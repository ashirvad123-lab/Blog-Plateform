"""
Unit and Integration Tests for BlogSphere Application
Covers Authentication, Blog CRUD, Comments, Likes, Authorization, Search, and REST APIs.
"""

import os
import unittest
from datetime import datetime, timezone

from app import create_app
from models import db, User, Category, BlogPost, Comment, Like


class BlogSphereTestCase(unittest.TestCase):
    """Test suite for BlogSphere."""

    def setUp(self):
        """Set up test environment before each test."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

        db.create_all()

        # Create basic test category
        self.category = Category(name='Technology', slug='technology', description='Tech news', color='primary')
        db.session.add(self.category)

        # Create Admin user
        self.admin = User(username='test_admin', email='admin@test.com', full_name='Admin User', role='admin')
        self.admin.set_password('AdminPass123')
        db.session.add(self.admin)

        # Create Normal User 1
        self.user1 = User(username='test_user1', email='user1@test.com', full_name='Test User 1', role='user')
        self.user1.set_password('UserPass123')
        db.session.add(self.user1)

        # Create Normal User 2
        self.user2 = User(username='test_user2', email='user2@test.com', full_name='Test User 2', role='user')
        self.user2.set_password('UserPass123')
        db.session.add(self.user2)

        db.session.commit()

    def tearDown(self):
        """Clean up database after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ----------------------------------------------------------------------
    # 1. Authentication Tests
    # ----------------------------------------------------------------------
    def test_user_registration(self):
        """Test successful user registration."""
        response = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'newuser@test.com',
            'full_name': 'New User',
            'password': 'Password123',
            'confirm_password': 'Password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registration successful', response.data)

        user = User.query.filter_by(username='newuser').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('Password123'))

    def test_duplicate_registration_prevented(self):
        """Test that registering duplicate email or username is rejected."""
        response = self.client.post('/register', data={
            'username': 'test_user1',  # Duplicate username
            'email': 'different@test.com',
            'password': 'Password123',
            'confirm_password': 'Password123'
        }, follow_redirects=True)
        self.assertIn(b'already taken', response.data)

        response2 = self.client.post('/register', data={
            'username': 'unique_user',
            'email': 'user1@test.com',  # Duplicate email
            'password': 'Password123',
            'confirm_password': 'Password123'
        }, follow_redirects=True)
        self.assertIn(b'already exists', response2.data)

    def test_login_and_logout(self):
        """Test login with credentials and subsequent logout."""
        # Valid login
        response = self.client.post('/login', data={
            'email_or_username': 'user1@test.com',
            'password': 'UserPass123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome back', response.data)

        # Logout
        response_logout = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response_logout.status_code, 200)
        self.assertIn(b'signed out successfully', response_logout.data)

    def test_personal_dashboard_renders_styled_sections(self):
        """Test the personal dashboard renders its redesigned sections."""
        self.client.post('/login', data={
            'email_or_username': 'user1@test.com',
            'password': 'UserPass123'
        })

        response = self.client.get('/dashboard')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'class="dashboard-page py-5"', response.data)
        self.assertIn(b'class="dashboard-heading', response.data)
        self.assertIn(b'class="stat-card dashboard-stat-card"', response.data)
        self.assertIn(b'class="card card-custom p-4 dashboard-panel"', response.data)

    def test_invalid_login(self):
        """Test login failure with wrong password."""
        response = self.client.post('/login', data={
            'email_or_username': 'user1@test.com',
            'password': 'WrongPassword!'
        }, follow_redirects=True)
        self.assertIn(b'Invalid username/email or password', response.data)

    # ----------------------------------------------------------------------
    # 2. Blog Post CRUD Tests
    # ----------------------------------------------------------------------
    def test_create_and_view_blog_post(self):
        """Test creating a new blog post and viewing its details."""
        # Log in as user 1
        self.client.post('/login', data={'email_or_username': 'user1@test.com', 'password': 'UserPass123'})

        response = self.client.post('/create-blog', data={
            'title': 'Test Blog Post Title',
            'category_id': self.category.id,
            'summary': 'This is a brief summary of the test post.',
            'content': 'This is the extended content for the test blog post. It must exceed twenty characters.',
            'tags': 'testing, python'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Blog Post Title', response.data)

        post = BlogPost.query.filter_by(title='Test Blog Post Title').first()
        self.assertIsNotNone(post)
        self.assertEqual(post.author.username, 'test_user1')

    def test_edit_own_blog_post(self):
        """Test author editing their own blog post."""
        self.client.post('/login', data={'email_or_username': 'user1@test.com', 'password': 'UserPass123'})

        post = BlogPost(
            title='Original Title Here',
            slug='original-title-here',
            summary='Original summary text.',
            content='Original content of the post with sufficient length.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add(post)
        db.session.commit()

        response = self.client.post(f'/edit-blog/{post.id}', data={
            'title': 'Updated Blog Title Here',
            'category_id': self.category.id,
            'summary': 'Updated summary text for the post.',
            'content': 'Updated content with more than twenty characters of detailed information.',
            'tags': 'updated, tags'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Updated Blog Title Here', response.data)

        updated_post = db.session.get(BlogPost, post.id)
        self.assertEqual(updated_post.title, 'Updated Blog Title Here')

    def test_unauthorized_edit_forbidden(self):
        """Test that user2 cannot edit user1's blog post."""
        post = BlogPost(
            title='User 1 Secret Post',
            slug='user-1-secret-post',
            summary='Summary text.',
            content='User 1 private article content with enough length.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add(post)
        db.session.commit()

        # Log in as user2
        self.client.post('/login', data={'email_or_username': 'user2@test.com', 'password': 'UserPass123'})

        response = self.client.post(f'/edit-blog/{post.id}', data={
            'title': 'Hacked Title By User 2',
            'category_id': self.category.id,
            'summary': 'Summary',
            'content': 'Content of the unauthorized modification attempt.'
        })
        self.assertEqual(response.status_code, 403)

    def test_delete_blog_post(self):
        """Test post deletion."""
        self.client.post('/login', data={'email_or_username': 'user1@test.com', 'password': 'UserPass123'})

        post = BlogPost(
            title='Post to be deleted',
            slug='post-to-be-deleted',
            summary='Summary for deletion test.',
            content='Detailed content to be deleted shortly.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

        response = self.client.post(f'/delete-blog/{post_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(BlogPost, post_id))

    # ----------------------------------------------------------------------
    # 3. Comment System Tests
    # ----------------------------------------------------------------------
    def test_comment_creation_and_deletion(self):
        """Test adding and deleting comments."""
        post = BlogPost(
            title='Discussion Topic Post',
            slug='discussion-topic-post',
            summary='Summary for discussion.',
            content='Content for discussion topic with sufficient length.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add(post)
        db.session.commit()

        # User 2 logs in and comments
        self.client.post('/login', data={'email_or_username': 'user2@test.com', 'password': 'UserPass123'})

        response = self.client.post(f'/blog/{post.id}/comment', data={
            'content': 'This is a thoughtful comment on the post.'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your comment has been added', response.data)

        comment = Comment.query.filter_by(post_id=post.id).first()
        self.assertIsNotNone(comment)
        self.assertEqual(comment.content, 'This is a thoughtful comment on the post.')

        # User 2 deletes comment
        del_response = self.client.post(f'/comment/{comment.id}/delete', follow_redirects=True)
        self.assertEqual(del_response.status_code, 200)
        self.assertIsNone(db.session.get(Comment, comment.id))

    # ----------------------------------------------------------------------
    # 4. Likes Functionality Tests
    # ----------------------------------------------------------------------
    def test_like_and_unlike_toggle(self):
        """Test liking and unliking a post via AJAX endpoint."""
        post = BlogPost(
            title='Appreciated Post',
            slug='appreciated-post',
            summary='Summary for like test.',
            content='Content for like testing with sufficient length.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add(post)
        db.session.commit()

        # User 2 logs in
        self.client.post('/login', data={'email_or_username': 'user2@test.com', 'password': 'UserPass123'})

        # 1st click: Like
        res1 = self.client.post(f'/blog/{post.id}/like', headers={'Accept': 'application/json'})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1['liked'])
        self.assertEqual(data1['total_likes'], 1)

        # 2nd click: Unlike
        res2 = self.client.post(f'/blog/{post.id}/like', headers={'Accept': 'application/json'})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertFalse(data2['liked'])
        self.assertEqual(data2['total_likes'], 0)

    # ----------------------------------------------------------------------
    # 5. Search and Filtering Tests
    # ----------------------------------------------------------------------
    def test_search_and_category_filter(self):
        """Test searching blogs and filtering by category."""
        p1 = BlogPost(
            title='Deep Learning Networks Guide',
            slug='deep-learning-networks-guide',
            summary='Machine learning algorithms.',
            content='Detailed deep learning explanations.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        p2 = BlogPost(
            title='Cooking Delicious Italian Pasta',
            slug='cooking-delicious-italian-pasta',
            summary='Food recipes and cooking tips.',
            content='How to boil pasta and make sauce from scratch.',
            category_id=self.category.id,
            user_id=self.user1.id
        )
        db.session.add_all([p1, p2])
        db.session.commit()

        # Search for 'Pasta'
        res = self.client.get('/blogs?q=Pasta')
        self.assertIn(b'Cooking Delicious Italian Pasta', res.data)
        self.assertNotIn(b'Deep Learning Networks Guide', res.data)

        # Filter by Category
        res_cat = self.client.get(f'/blogs?category={self.category.slug}')
        self.assertEqual(res_cat.status_code, 200)
        self.assertIn(b'Deep Learning Networks Guide', res_cat.data)

    # ----------------------------------------------------------------------
    # 6. Admin Role and Permission Tests
    # ----------------------------------------------------------------------
    def test_admin_dashboard_access(self):
        """Test admin access control."""
        # Non-admin user denied
        self.client.post('/login', data={'email_or_username': 'user1@test.com', 'password': 'UserPass123'})
        res_user = self.client.get('/admin')
        self.assertEqual(res_user.status_code, 403)

        # Admin allowed
        self.client.get('/logout')
        self.client.post('/login', data={'email_or_username': 'admin@test.com', 'password': 'AdminPass123'})
        res_admin = self.client.get('/admin')
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Platform Administration', res_admin.data)

    # ----------------------------------------------------------------------
    # 7. RESTful APIs Tests
    # ----------------------------------------------------------------------
    def test_rest_api_posts_lifecycle(self):
        """Test REST API get, create, and like endpoints."""
        # API Login
        login_res = self.client.post('/api/login', json={
            'email_or_username': 'user1@test.com',
            'password': 'UserPass123'
        })
        self.assertEqual(login_res.status_code, 200)

        # API Create Post
        create_res = self.client.post('/api/posts', json={
            'title': 'API Created Blog Post',
            'summary': 'Created through REST API call.',
            'content': 'This post was submitted to the REST API test endpoint.',
            'category_id': self.category.id,
            'tags': 'api, json, test'
        })
        self.assertEqual(create_res.status_code, 201)
        post_data = create_res.get_json()['post']
        post_id = post_data['id']

        # API Get Single Post
        get_res = self.client.get(f'/api/posts/{post_id}')
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.get_json()['title'], 'API Created Blog Post')

        # API Toggle Like
        like_res = self.client.post(f'/api/posts/{post_id}/like')
        self.assertEqual(like_res.status_code, 200)
        self.assertTrue(like_res.get_json()['liked'])
        self.assertEqual(like_res.get_json()['total_likes'], 1)


if __name__ == '__main__':
    unittest.main()
