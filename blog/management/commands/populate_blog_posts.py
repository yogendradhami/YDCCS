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
                'title': 'Construction Cleaning Services in Adelaide: Complete Guide for Builders and Property Owners',
                'slug': 'construction-cleaning-services-adelaide',
                'excerpt': 'Discover how professional construction cleaning services help builders, contractors, and property owners prepare newly built or renovated spaces for safe, clean, and ready-to-use environments.',
                'content': '<h2>What Is Construction Cleaning?</h2><p>Construction cleaning is a specialist service designed to remove dust, debris, building residue, and waste left behind after renovation or build work. Unlike regular cleaning, it focuses on the fine particles and material left by tradespeople, fittings, and finishing work.</p><p>For builders, contractors, offices, and property owners, this stage is essential because it transforms a recently completed project into a clean, safe, and presentable space that is ready for handover, occupation, or inspection.</p><h2>Why Professional Construction Cleaning Matters</h2><p>After construction or renovation work, a property can still contain:</p><ul><li>Fine dust on walls, ceilings, floors, and fixtures</li><li>Paint marks, adhesive residue, and grout stains</li><li>Packaging materials, rubbish, and leftover trim</li><li>Marks on glass, windows, and cabinetry</li><li>Dust in cupboards, drawers, and hard-to-reach areas</li></ul><p>Professional construction cleaning does more than improve appearance. It helps create a healthier environment and ensures the final finish reflects the quality of the workmanship behind it.</p><h2>Our Construction Cleaning Services</h2><p>We provide a careful, detail-focused process that covers the most common post-build requirements:</p><ul><li><strong>Post-construction dust removal</strong> for walls, ceilings, floors, and fixtures</li><li><strong>Detailed floor cleaning</strong> for tiles, timber, vinyl, concrete, and carpeted areas</li><li><strong>Window and glass cleaning</strong> to remove marks, dust, and residue</li><li><strong>Bathroom and kitchen cleaning</strong> for surfaces, fittings, fixtures, and final presentation</li><li><strong>Final builders clean</strong> for handover, inspections, property opening, or move-in ready preparation</li></ul><p>With a professional team, the end result is a property that feels truly finished and ready for use.</p><h2>Why Choose YD Commercial Cleaning Services?</h2><p>At YD Commercial Cleaning Services, we understand that construction cleaning requires more than routine wipe-downs. It demands consistency, care, and the right tools to remove residue without damaging new finishes.</p><p>Whether you are a builder, property owner, tenant, or business operator, our team delivers a polished, dependable result across Adelaide.</p>',
                'category': 'Residential',
                'published': True,
                'published_at': datetime.now() - timedelta(days=16),
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
