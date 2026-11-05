"""
seed.py - Database Seeding Script for BlogSphere
Populates initial categories, administrators, standard users, realistic blog posts,
comments, and engagement likes.
Run via: python seed.py
"""

import sys
import os
from datetime import datetime, timedelta, timezone

from app import create_app
from models import db, User, Category, BlogPost, Comment, Like, slugify


def seed_database():
    app = create_app()

    with app.app_context():
        print("Initializing database tables...")
        db.create_all()

        # Check if database already has content
        if User.query.count() > 0:
            print("Database already contains data.")
            choice = input("Do you wish to reset and re-seed the database? [y/N]: ").strip().lower()
            if choice not in ('y', 'yes'):
                print("Seeding aborted. Existing data preserved.")
                return
            print("Dropping and recreating all tables...")
            db.drop_all()
            db.create_all()

        print("\n1. Creating Categories...")
        categories_data = [
            {
                'name': 'Technology',
                'description': 'Latest breakthroughs, computing hardware, consumer tech, and industry trends.',
                'color': 'primary'
            },
            {
                'name': 'Web Development',
                'description': 'Modern web engineering, frontend frameworks, backend APIs, and database performance.',
                'color': 'indigo'
            },
            {
                'name': 'Artificial Intelligence',
                'description': 'Machine learning models, generative AI, neural networks, and algorithmic breakthroughs.',
                'color': 'info'
            },
            {
                'name': 'Design & UI/UX',
                'description': 'Product design thinking, typography, accessibility, and delightful user interfaces.',
                'color': 'warning'
            },
            {
                'name': 'Career & Growth',
                'description': 'Software engineering career paths, interview prep, productivity, and leadership.',
                'color': 'success'
            },
            {
                'name': 'Tutorials & Guides',
                'description': 'Step-by-step practical walk-throughs, sample projects, and technical how-tos.',
                'color': 'dark'
            }
        ]

        categories_map = {}
        for cat in categories_data:
            c = Category(
                name=cat['name'],
                slug=slugify(cat['name']),
                description=cat['description'],
                color=cat['color']
            )
            db.session.add(c)
            categories_map[cat['name']] = c

        db.session.commit()
        print(f"Created {len(categories_map)} categories.")

        print("\n2. Creating Users...")
        # 1 Admin
        admin = User(
            username='admin',
            email='admin@blogsphere.com',
            full_name='System Administrator',
            bio='Lead Administrator for BlogSphere. Maintaining community integrity, publishing guidelines, and platform architecture.',
            role='admin'
        )
        admin.set_password('Admin@123')
        db.session.add(admin)

        # 3 Standard Users
        alex = User(
            username='alex_dev',
            email='alex@example.com',
            full_name='Alex Chen',
            bio='Senior Full-Stack Engineer working with Python, Flask, TypeScript, and distributed systems. Lifelong learner and open-source enthusiast.',
            role='user'
        )
        alex.set_password('Alex@123')
        db.session.add(alex)

        sarah = User(
            username='sarah_connor',
            email='sarah@example.com',
            full_name='Sarah Connor',
            bio='AI Research Scientist and Technical Writer focusing on natural language processing, LLMs, and ethical computing.',
            role='user'
        )
        sarah.set_password('Sarah@123')
        db.session.add(sarah)

        elena = User(
            username='elena_ux',
            email='elena@example.com',
            full_name='Elena Rostova',
            bio='Lead UI/UX Designer passionate about building accessible design systems, intuitive visual hierarchies, and micro-interactions.',
            role='user'
        )
        elena.set_password('Elena@123')
        db.session.add(elena)

        db.session.commit()
        print("Created 4 users (1 Admin: admin@blogsphere.com, 3 Users: alex_dev, sarah_connor, elena_ux).")

        print("\n3. Creating Realistic Blog Posts...")
        now = datetime.now(timezone.utc)

        posts_data = [
            {
                'title': 'Building Scalable Full-Stack Web Applications with Python and Flask',
                'category': 'Web Development',
                'author': alex,
                'is_featured': True,
                'views': 240,
                'created_at': now - timedelta(days=12),
                'tags': 'python, flask, webdev, architecture, backend',
                'summary': 'Explore essential architectural patterns, ORM practices, and database optimization techniques for production-ready Flask applications.',
                'content': """Building scalable web backends requires careful planning across application structure, database design, and caching layers. In this comprehensive guide, we examine how Python Flask delivers enterprise-grade performance when paired with clean architectural patterns.

### Why Flask Remains a Top Choice in Modern Engineering

While heavier frameworks enforce opinionated scaffolding, Flask provides total architectural freedom. This allows engineering teams to implement domain-driven design, maintainable blueprints, and lightweight REST APIs without unnecessary overhead.

### Key Tenets of Clean Flask Architecture

1. **The Application Factory Pattern**: Utilizing `create_app()` ensures flexible configuration switching across development, testing, and production environments without global state pollution.
2. **Defensive Database Modeling**: By defining foreign key cascades, unique constraints, and optimized indexes in SQLAlchemy, data integrity remains enforced at the engine level.
3. **Session and Authentication Security**: Storing passwords with modern cryptographic algorithms such as Argon2 or Scrypt guarantees protection against rainbow table attacks.
4. **Decoupled API Layers**: Exposing clean RESTful endpoints alongside server-rendered views enables gradual migration toward decoupled client architectures.

By adhering to these principles, our application can scale comfortably to handle thousands of concurrent readers with minimal infrastructure costs."""
            },
            {
                'title': 'The Next Frontier: Understanding Generative AI and Reasoning Models',
                'category': 'Artificial Intelligence',
                'author': sarah,
                'is_featured': True,
                'views': 385,
                'created_at': now - timedelta(days=9),
                'tags': 'ai, machinelearning, reasoning, llm, technology',
                'summary': 'A technical dive into chain-of-thought prompting, test-time compute scaling, and how reasoning architectures transform problem-solving in software.',
                'content': """Artificial intelligence has transitioned from predictive statistical models to active reasoning engines. Today's advanced models don't just output the next probable token; they form iterative chains of thought, self-correct hypotheses, and navigate complex algorithmic logic.

### Moving Beyond Token Prediction

Traditional generative transformers operated primarily as high-dimensional autocomplete systems. When tasked with multi-step math or complex system design, standard generation frequently drifted into hallucinations.

With the emergence of **test-time compute scaling**, models spend cognitive cycles deliberating, generating candidate hypotheses, and verifying constraints before returning an answer. This dramatically reduces error rates across programming benchmarks, scientific research, and legal analysis.

### What Engineers Must Keep in Mind

- **Prompt Engineering as Systems Design**: Structuring inputs with structured constraints and multi-turn verification yields orders-of-magnitude higher reliability.
- **Data Provenance and Privacy**: Enterprise adoption requires rigorous boundary isolation, zero-retention policies, and strict API access governance.
- **Human-in-the-Loop Collaboration**: AI remains a powerful pair-programming and thinking collaborator, yet senior engineering oversight is non-negotiable for mission-critical software.

The future belongs to builders who harness these tools to augment human curiosity and problem-solving capability."""
            },
            {
                'title': 'Crafting Delightful User Interfaces: The Psychology of Micro-Interactions',
                'category': 'Design & UI/UX',
                'author': elena,
                'is_featured': True,
                'views': 195,
                'created_at': now - timedelta(days=6),
                'tags': 'ui, ux, design, microinteractions, frontend',
                'summary': 'Discover how subtle hover states, responsive feedback loops, and thoughtful motion design turn ordinary websites into memorable experiences.',
                'content': """Great design is often invisible. When a user interacts with a button that provides immediate visual feedback, or submits a form with a smooth fade-in confirmation, they experience confidence in the system.

### The Power of the Feedback Loop

Every micro-interaction consists of four core elements:
1. **The Trigger**: The user action (a mouse hover, click, or tap).
2. **The Rule**: What happens behind the scenes.
3. **The Feedback**: The visual or auditory response informing the user that their intention was understood.
4. **The Loops & Modes**: The duration or recurring behavior of the interaction.

### Subtle Details That Elevate Web Applications

- **Instant Button Responses**: Avoid blank delays. When an action occurs, provide an immediate loading indicator or subtle scale change.
- **Sensible Elevation**: Use multi-layered box shadows to simulate natural physical light rather than heavy flat outlines.
- **Accessible Typography**: High contrast ratios, readable line heights (around 1.6-1.8), and generous whitespace prevent cognitive fatigue.

When engineering meets empathetic human-centered design, the result is software that users genuinely enjoy returning to day after day."""
            },
            {
                'title': 'From Junior to Senior: Navigating the Software Engineering Career Ladder',
                'category': 'Career & Growth',
                'author': admin,
                'is_featured': False,
                'views': 160,
                'created_at': now - timedelta(days=4),
                'tags': 'career, engineering, mentorship, growth, leadership',
                'summary': 'Practical insights on technical communication, system architecture ownership, and multiplying team productivity to advance your career.',
                'content': """Many junior developers believe advancing to senior levels simply requires writing more lines of code or memorizing complex syntax. In reality, the differentiator is impact, communication, and system-level thinking.

### 1. Shift from 'How' to 'Why'
Junior engineers focus on *how* to implement a requested feature. Senior engineers step back and ask *why* the feature is needed, what business value it unlocks, and whether a simpler alternative exists.

### 2. Clarity of Written Communication
Writing thorough pull request descriptions, architecture decision records (ADRs), and clear documentation prevents misunderstandings that could cost weeks of engineering hours.

### 3. Multiplying Others
A 10x engineer is not someone who writes 10x more code; it is someone who mentors five colleagues and makes each of them 2x more effective. Prioritize unblocking teammates and establishing clean coding conventions."""
            },
            {
                'title': 'Mastering Modern CSS: Grid, Flexbox, and Container Queries Explained',
                'category': 'Web Development',
                'author': alex,
                'is_featured': False,
                'views': 120,
                'created_at': now - timedelta(days=2),
                'tags': 'css, frontend, responsive, webdesign',
                'summary': 'A practical breakdown of modern CSS layout techniques that make responsive web design clean, reliable, and fluid.',
                'content': """Gone are the days of float clearfixes and brittle pixel-based calculations. Modern CSS has evolved into a robust layout engine capable of intricate two-dimensional layouts with minimal code.

### When to Use Flexbox vs. Grid
- **CSS Grid** excels at two-dimensional layouts where both rows and columns need alignment (card grids, dashboard panels, hero sections).
- **Flexbox** is the champion for one-dimensional layouts (navbars, button groups, icon-text pairings).

### Responsive Without Media Queries
With functions like `clamp()` and CSS Grid's `repeat(auto-fit, minmax(280px, 1fr))`, cards can adjust dynamically to any screen width without a single breakpoint! Combine this with modern container queries to build truly modular component systems."""
            },
            {
                'title': 'Database Indexing Demystified: B-Trees and Query Optimization',
                'category': 'Tutorials & Guides',
                'author': sarah,
                'is_featured': False,
                'views': 95,
                'created_at': now - timedelta(days=1),
                'tags': 'database, sql, indexing, performance, backend',
                'summary': 'Learn how database indexes work under the hood, how B-Trees accelerate lookups, and when indexing might actually hurt performance.',
                'content': """Database performance issues almost always stem from unindexed queries scanning millions of rows sequentially. Understanding how B-Trees function allows developers to craft fast, scalable queries.

### The Index as a Book Index
Think of an index like the index at the back of a textbook. Instead of reading every single page sequentially (Full Table Scan), you jump straight to the topic and follow the page reference (Index Seek).

### Best Practices for Relational Indexes
1. **Index Foreign Keys**: Always index foreign keys (`user_id`, `category_id`) to accelerate join queries.
2. **Index Unique Slugs**: Slugs used in URLs (`/blog/<slug>`) must have unique constraints and B-Tree indexes for instantaneous page loads.
3. **Beware of Over-Indexing**: Every insert, update, and delete requires updating the index. Only index columns frequently queried in `WHERE`, `ORDER BY`, or `JOIN` clauses."""
            }
        ]

        created_posts = []
        for p in posts_data:
            cat = categories_map[p['category']]
            post = BlogPost(
                title=p['title'],
                slug=slugify(p['title']),
                summary=p['summary'],
                content=p['content'],
                category_id=cat.id,
                user_id=p['author'].id,
                tags=p['tags'],
                is_featured=p['is_featured'],
                views=p['views'],
                created_at=p['created_at']
            )
            db.session.add(post)
            created_posts.append(post)

        db.session.commit()
        print(f"Created {len(created_posts)} realistic blog posts.")

        print("\n4. Adding Comments and Likes...")
        comments_data = [
            (created_posts[0], sarah, "Outstanding overview, Alex! The section on the Application Factory pattern is spot on. It makes unit testing so much simpler."),
            (created_posts[0], elena, "Clear, practical, and well-structured. Bookmarked for my team's onboarding guide!"),
            (created_posts[0], admin, "Excellent write-up on defensive database modeling. Looking forward to part two."),
            (created_posts[1], alex, "Test-time compute scaling is genuinely the most exciting development in recent months. Great breakdown Sarah!"),
            (created_posts[1], elena, "Fascinating perspective on human-in-the-loop collaboration. The ethics aspect is crucial."),
            (created_posts[2], alex, "As a backend guy, understanding the psychology behind micro-interactions really changes how I design API response latencies!"),
            (created_posts[2], sarah, "The point about accessible typography cannot be overstated. Beautifully articulated Elena."),
            (created_posts[3], alex, "Solid career advice. Shifting from 'how' to 'why' was the single biggest turning point in my career."),
            (created_posts[4], elena, "The clamp() function has replaced dozens of media queries in my stylesheets. Super clean examples!")
        ]

        for post, author, text in comments_data:
            c = Comment(
                content=text,
                post_id=post.id,
                user_id=author.id,
                created_at=post.created_at + timedelta(hours=3)
            )
            db.session.add(c)

        # Add Likes
        likes_data = [
            (created_posts[0], sarah),
            (created_posts[0], elena),
            (created_posts[0], admin),
            (created_posts[1], alex),
            (created_posts[1], elena),
            (created_posts[1], admin),
            (created_posts[2], alex),
            (created_posts[2], sarah),
            (created_posts[3], alex),
            (created_posts[3], elena),
            (created_posts[4], admin),
            (created_posts[4], sarah),
            (created_posts[5], alex),
            (created_posts[5], elena)
        ]

        for post, user in likes_data:
            l = Like(post_id=post.id, user_id=user.id)
            db.session.add(l)

        db.session.commit()
        print(f"Created {len(comments_data)} comments and {len(likes_data)} likes.")

        print("\n" + "=" * 60)
        print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Credentials for Testing:")
        print("  Administrator : admin@blogsphere.com  / Admin@123")
        print("  Author 1      : alex@example.com      / Alex@123 (username: alex_dev)")
        print("  Author 2      : sarah@example.com     / Sarah@123 (username: sarah_connor)")
        print("  Author 3      : elena@example.com     / Elena@123 (username: elena_ux)")
        print("=" * 60)


if __name__ == '__main__':
    seed_database()
