import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import BlogPost

client = app.test_client()

# 1. Fetch login page and extract CSRF token
login_page = client.get('/login')
assert login_page.status_code == 200
match = re.search(r'name="csrf_token" value="([^"]+)"', login_page.data.decode('utf-8'))
assert match is not None, "CSRF token not found in login form"
csrf_token = match.group(1)
print("1. CSRF token extracted successfully from rendered login form.")

# 2. Submit login with CSRF token
login_res = client.post('/login', data={
    'csrf_token': csrf_token,
    'email_or_username': 'admin@blogsphere.com',
    'password': 'Admin@123'
}, follow_redirects=True)
assert login_res.status_code == 200
assert b'Welcome back' in login_res.data
print("2. Admin login authenticated and session created successfully.")

# 3. Test Admin Protected Routes
admin_routes = ['/dashboard', '/admin', '/my-blogs', '/my-comments', '/profile', '/create-blog']
for r in admin_routes:
    res = client.get(r)
    assert res.status_code == 200, f"Route {r} returned {res.status_code}"
    print(f"   Route {r:<20} -> Status: {res.status_code}")

# 4. Test Single Blog Detail
with app.app_context():
    first_post = BlogPost.query.first()
    slug = first_post.slug

detail_res = client.get(f'/blog/{slug}')
assert detail_res.status_code == 200
assert first_post.title.encode('utf-8') in detail_res.data
print(f"4. Article detail view for '{slug}' verified with status 200.")

print("\n>>> ALL FULL-STACK WORKFLOWS TESTED AND PASSED WITH FLYING COLORS! <<<")
