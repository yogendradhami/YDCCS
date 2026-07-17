from django.core.management.base import BaseCommand
from blog.models import BlogPost
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Populate initial blog posts from static template data'

    def handle(self, *args, **options):
        blog_data = [
            {
                'title': 'Professional Cleaning Best Practices for Adelaide Homes and Offices',
                'slug': 'professional-cleaning-best-practices',
                'excerpt': 'Learn industry-leading cleaning techniques and best practices that keep your Adelaide property spotless and healthy year-round.',
                'content': 'Professional cleaning is about consistency, right tools and safe cleaning agents. In this post we walk through key practices our teams follow to deliver reliable results across residential and commercial properties in Adelaide.\n\nPlanning and preparation: Every job starts with a clear plan: access points, surfaces, time allocation and client priorities. We advise clients to declutter zones to speed up cleaning and protect fragile items.\n\nHigh-impact techniques: Focus on high-touch areas like door handles, light switches and shared surfaces. Use microfibre cloths and electrostatic dusters for efficient dust removal.\n\nSafety and eco-awareness: We balance strong cleaning action with safe, low-toxicity products and follow guidance for ventilation and safe dilution of concentrated cleaners.',
                'category': 'Featured',
                'published': True,
                'published_at': datetime.now() - timedelta(days=3),
            },
            {
                'title': 'Deep Cleaning vs. Regular Cleaning: When You Need Each',
                'slug': 'deep-cleaning-vs-regular-cleaning',
                'excerpt': 'Learn the differences between deep cleaning and regular maintenance, and understand how often you should schedule each service.',
                'content': 'Regular cleaning keeps your home tidy; deep cleaning targets hidden dirt and buildup. We outline common scenarios where deep cleaning is the right investment.\n\nSigns you need a deep clean: Persistent odours, heavy dust, carpets that haven\'t been professionally cleaned in over a year — these are classic triggers.',
                'category': 'Residential',
                'published': True,
                'published_at': datetime.now() - timedelta(days=16),
            },
            {
                'title': 'How Office Cleanliness Affects Employee Productivity',
                'slug': 'office-cleanliness-productivity',
                'excerpt': 'Discover the connection between workplace cleanliness and employee performance, morale, and long-term business success.',
                'content': 'A clean workspace reduces distractions and illness, improving focus and attendance. We share evidence-based tips to create cleaner workplaces.',
                'category': 'Commercial',
                'published': True,
                'published_at': datetime.now() - timedelta(days=30),
            },
            {
                'title': 'Spring Cleaning Checklist: Room-by-Room Guide',
                'slug': 'spring-cleaning-checklist',
                'excerpt': 'Complete spring cleaning checklist for every room in your home. Refresh your space for the season with this detailed guide.',
                'content': 'This room-by-room checklist will help you plan an efficient spring clean. Focus on decluttering, deep-cleaning fabrics, and refreshing ventilation.',
                'category': 'Tips & Guides',
                'published': True,
                'published_at': datetime.now() - timedelta(days=36),
            },
            {
                'title': 'Summer Cleaning Tips for Adelaide\'s Hot Climate',
                'slug': 'summer-cleaning-adelaide',
                'excerpt': 'Practical cleaning strategies for Adelaide\'s summer weather. Keep your home fresh and hygienic during the hot months.',
                'content': 'In Adelaide\'s heat, focus on humidity-sensitive areas, pest control prevention, and keeping fabrics fresh to reduce odours.',
                'category': 'Seasonal',
                'published': True,
                'published_at': datetime.now() - timedelta(days=46),
            },
            {
                'title': 'Eco-Friendly Cleaning Solutions Safe for Your Family',
                'slug': 'eco-friendly-cleaning-solutions',
                'excerpt': 'Discover professional-grade eco-friendly cleaning products and methods that are effective and safe for families and pets.',
                'content': 'Choose green cleaning products that are effective and safe — we list substitutions and professional-grade eco products we trust.',
                'category': 'Tips & Guides',
                'published': True,
                'published_at': datetime.now() - timedelta(days=95),
            },
        ]

        for post_data in blog_data:
            post, created = BlogPost.objects.get_or_create(
                slug=post_data['slug'],
                defaults=post_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {post.title}'))
            else:
                self.stdout.write(self.style.WARNING(f'→ Skipped (already exists): {post.title}'))

        total = BlogPost.objects.count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Done! Total blog posts: {total}'))
