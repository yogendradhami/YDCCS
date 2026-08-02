SERVICE_DEFINITIONS = {
    "commercial-cleaning": {
        "service_name": "Commercial Cleaning",
        "title": "Commercial Cleaning",
        "heading": "Commercial Cleaning for Businesses",
        "description": "Reliable commercial cleaning for offices, retail stores, warehouses and business premises across {location}.",
        "overview": "Commercial cleaning solutions for businesses in {location}, tailored to keep workplaces clean, safe and professional.",
        "hero_image": "/static/images/services/commercial-cleaning.svg",
        "gallery": [],
        "problems": [
            "High-traffic dirt and grime",
            "Dust and allergen build-up",
            "Difficult-to-clean communal areas",
            "Inconsistent cleaning standards"
        ],
        "included": [
            "Daily or weekly office cleaning",
            "Dusting, vacuuming and sanitisation",
            "Kitchen and bathroom maintenance",
            "Flexible cleaning schedules for business hours"
        ],
        "process": [
            "Site assessment and quote",
            "Scheduled cleaning with quality checks",
            "Regular inspections and supervisor sign-off"
        ],
        "benefits": [
            "Healthier workplace",
            "Improved presentation for customers",
            "Consistent quality and reliability"
        ],
        "packages": [
            {"name": "Standard Commercial Clean", "price": "$220", "description": "Basic daily or weekly cleaning for small offices and retail spaces."},
            {"name": "Premium Commercial Clean", "price": "$360", "description": "Comprehensive cleaning for medium to large business premises."},
            {"name": "One-Off Commercial Clean", "price": "$280", "description": "Ideal for post-event or opening-day cleaning support."}
        ],
        "related_services": ["office-cleaning", "window-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "office-cleaning": {
        "service_name": "Office Cleaning",
        "title": "Office Cleaning",
        "heading": "Professional Office Cleaning",
        "description": "Professional office cleaning services in {location} for desks, meeting rooms, kitchens and shared spaces.",
        "overview": "Office cleaning that helps businesses maintain a hygienic workspace with minimal disruption.",
        "hero_image": "/static/images/services/office-cleaning.svg",
        "gallery": [],
        "problems": ["Dusty workstations", "Stains in carpets", "Untidy communal kitchens"],
        "included": [
            "Desk and workstation sanitisation",
            "Meeting room cleaning",
            "Kitchen and breakroom cleaning",
            "Floor vacuuming and mopping"
        ],
        "process": ["Weekly or daily scheduling", "Supervisor checks", "Quality feedback loop"],
        "benefits": ["Cleaner workspace", "Reduced sick-days", "Professional appearance"],
        "packages": [
            {"name": "Workspace Refresh", "price": "$180", "description": "Daily or weekly office cleaning for small teams."},
            {"name": "Executive Office Clean", "price": "$320", "description": "Deep cleaning for executive suites and client-facing spaces."},
            {"name": "After Hours Office Clean", "price": "$240", "description": "Flexible cleaning outside business hours for minimal disruption."}
        ],
        "related_services": ["commercial-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "end-of-lease-cleaning": {
        "service_name": "End of Lease Cleaning",
        "title": "End of Lease Cleaning",
        "heading": "End of Lease / Bond Cleaning",
        "description": "Detailed end of lease cleaning for tenants, landlords and property managers in {location}.",
        "overview": "Thorough bond cleaning to help tenants leave their rental clean and compliant with landlord expectations.",
        "hero_image": "/static/images/services/end-of-lease-cleaning.svg",
        "gallery": [],
        "problems": ["Stubborn oven and kitchen grease", "Carpet stains", "Grout and mould issues"],
        "included": [
            "Kitchen deep clean and appliance degreasing",
            "Bathroom sanitisation and grout cleaning",
            "Carpet vacuuming and stain treatment",
            "Wall wiping, skirting and window cleaning"
        ],
        "process": ["Pre-inspection", "Targeted deep cleaning", "Final inspection and report"],
        "benefits": ["Higher chance of full bond return", "Cleaner presentation for new tenants"],
        "packages": [
            {"name": "Basic Bond Clean", "price": "$320", "description": "Complete end of lease clean for standard properties."},
            {"name": "Premium Bond Clean", "price": "$450", "description": "Detailed cleaning for larger homes and rental properties."},
            {"name": "Express Bond Clean", "price": "$380", "description": "Fast scheduled cleaning to meet tight move-out dates."}
        ],
        "related_services": ["bond-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "bond-cleaning": {
        "service_name": "Bond Cleaning",
        "title": "Bond Cleaning",
        "heading": "Bond & End of Lease Cleaning",
        "description": "Bond cleaning and end of lease cleaning in {location} to help customers get their deposit back.",
        "overview": "Professional bond cleaning with same-day quotes and a satisfaction-focused approach.",
        "hero_image": "/static/images/services/bond-cleaning.svg",
        "gallery": [],
        "problems": ["Missed inspection items", "Stubborn stains", "Unclean appliances"],
        "included": [
            "Carpet and floor cleaning",
            "Bathroom, kitchen and oven cleaning",
            "Window cleaning and dusting",
            "Detailed property inspection report"
        ],
        "process": ["Detailed room-by-room clean", "Inspection checklist", "Manager sign-off"],
        "benefits": ["Increased likelihood of bond return", "Hassle-free handover"],
        "packages": [
            {"name": "Standard Bond Clean", "price": "$330", "description": "Bond cleaning for standard rental homes in {location}."},
            {"name": "Bond Clean + Carpet", "price": "$470", "description": "Includes carpet shampooing and a full move-out clean."},
            {"name": "Move-Out Bond Clean", "price": "$410", "description": "Designed for fast move-out preparation and inspection readiness."}
        ],
        "related_services": ["end-of-lease-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "house-cleaning": {
        "service_name": "House Cleaning",
        "title": "House Cleaning",
        "heading": "Reliable House Cleaning",
        "description": "House cleaning services in {location} for one-off, regular and deep cleans around your home.",
        "overview": "Home cleaning that keeps Adelaide houses welcoming, organised and healthy.",
        "hero_image": "/static/images/services/house-cleaning.svg",
        "gallery": [],
        "problems": ["Dusty living areas", "Kitchen grease", "Stains and odours"],
        "included": [
            "Living area dusting and vacuuming",
            "Kitchen and bathroom cleaning",
            "Bedroom and laundry room maintenance",
            "Interior window and mirror cleaning"
        ],
        "process": ["Tailored schedule", "Trained cleaners", "Satisfaction check"],
        "benefits": ["More free time", "Consistent cleanliness"],
        "packages": [
            {"name": "Standard Home Clean", "price": "$180", "description": "Regular house cleaning for busy Adelaide families."},
            {"name": "Deep Home Clean", "price": "$320", "description": "Thorough cleaning for homes requiring extra attention."},
            {"name": "Move-In Home Clean", "price": "$290", "description": "Fresh start cleaning for new Adelaide homes."}
        ],
        "related_services": ["regular-house-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "regular-house-cleaning": {
        "service_name": "Regular House Cleaning",
        "title": "Regular House Cleaning",
        "heading": "Regular House Cleaning Plans",
        "description": "Regular house cleaning in {location} for busy households and families.",
        "overview": "Routine house cleaning with dependable service and Adelaide-friendly scheduling.",
        "hero_image": "/static/images/services/regular-house-cleaning.svg",
        "gallery": [],
        "problems": ["Busy schedules", "Build-up between cleans"],
        "included": [
            "Weekly or fortnightly cleaning",
            "Kitchen and bathroom maintenance",
            "Dusting, vacuuming and floor care",
            "Wipes for high-touch surfaces"
        ],
        "process": ["Recurring bookings", "Consistent team allocation"],
        "benefits": ["Predictable cleanliness", "Time-savings"],
        "packages": [
            {"name": "Weekly Clean", "price": "$170", "description": "Ongoing house cleaning to keep your home tidy."},
            {"name": "Fortnightly Clean", "price": "$200", "description": "Flexible recurring cleaning for busy schedules."},
            {"name": "Monthly Clean", "price": "$240", "description": "Deep cleaning once per month for consistent results."}
        ],
        "related_services": ["house-cleaning"],
        "locations": ["Adelaide"]
    },
    "window-cleaning": {
        "service_name": "Window Cleaning",
        "title": "Window Cleaning",
        "heading": "Professional Window Cleaning",
        "description": "Window cleaning in {location} for homes, offices and commercial buildings.",
        "overview": "Streak-free window cleaning for Adelaide properties, inside and out.",
        "hero_image": "/static/images/services/window-cleaning.svg",
        "gallery": [],
        "problems": ["Streaks and watermarks", "Hard-to-reach panes"],
        "included": [
            "Interior glass cleaning",
            "Exterior glass cleaning",
            "Frame and sill wiping",
            "Spotless finishing touches"
        ],
        "process": ["Safety assessment", "Reach and clean", "Final polish"],
        "benefits": ["Clear views", "Improved curb appeal"],
        "packages": [
            {"name": "Residential Window Clean", "price": "$140", "description": "Window cleaning for homes and small offices."},
            {"name": "Commercial Window Clean", "price": "$260", "description": "Larger window cleaning jobs for business sites."},
            {"name": "High-Rise Window Clean", "price": "$420", "description": "Safe, professional cleaning for taller buildings."}
        ],
        "related_services": ["pressure-washing"],
        "locations": ["Adelaide"]
    },
    "carpet-steam-cleaning": {
        "service_name": "Carpet Steam Cleaning",
        "title": "Carpet Steam Cleaning",
        "heading": "Carpet Steam Cleaning",
        "description": "Carpet steam cleaning in {location} for homes and offices that need deep fibre care.",
        "overview": "Steam cleaning that restores carpets and removes stubborn dirt and odours.",
        "hero_image": "/static/images/services/carpet-steam-cleaning.svg",
        "gallery": [],
        "problems": ["Deep-seated dirt", "Odours and allergens", "Stubborn stains"],
        "included": [
            "Hot water extraction",
            "Stain treatment",
            "Carpet grooming",
            "Fast drying process"
        ],
        "process": ["Pre-treatment", "Hot water extraction", "Drying and grooming"],
        "benefits": ["Improved appearance", "Allergen reduction"],
        "packages": [
            {"name": "Small Carpet Steam Clean", "price": "$160", "description": "Effective steam cleaning for small rooms."},
            {"name": "Whole Home Steam Clean", "price": "$320", "description": "Deep cleaning for multiple rooms and high-traffic areas."},
            {"name": "Commercial Carpet Steam Clean", "price": "$390", "description": "Steam cleaning for carpets in offices and retail spaces."}
        ],
        "related_services": ["carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "builders-cleaning": {
        "service_name": "Builders Cleaning",
        "title": "Builders Cleaning",
        "heading": "Builders & Construction Cleaning",
        "description": "Builders cleaning in {location} for construction sites, renovations and new developments.",
        "overview": "Post-build cleaning that prepares new homes and commercial spaces for handover.",
        "hero_image": "/static/images/services/builders-cleaning.svg",
        "gallery": [],
        "problems": ["Construction dust and debris", "Paint splatters and grout residue"],
        "included": [
            "Debris removal",
            "Dust and grout cleaning",
            "Final surface wipe down",
            "Safety and clearance checks"
        ],
        "process": ["Site risk assessment", "Rough clear-out", "Detailed finish clean", "Final walkthrough"],
        "benefits": ["Inspection-ready properties", "Safe handover"],
        "packages": [
            {"name": "Standard Builders Clean", "price": "$420", "description": "Complete cleaning after renovations and building work."},
            {"name": "Final Builders Clean", "price": "$520", "description": "Thorough finish clean before property handover."},
            {"name": "Site Preparation Clean", "price": "$360", "description": "Pre-inspection cleaning for new builds."}
        ],
        "related_services": ["post-construction-cleaning"],
        "locations": ["Adelaide"]
    },
    "post-construction-cleaning": {
        "service_name": "Post Construction Cleaning",
        "title": "Post Construction Cleaning",
        "heading": "Post-Construction & Renovation Cleaning",
        "description": "Post construction cleaning in {location} to remove dust, debris and builders’ residue.",
        "overview": "Cleaning after building or renovation works, readying properties for occupation.",
        "hero_image": "/static/images/services/post-construction-cleaning.svg",
        "gallery": [],
        "problems": ["Fine dust in vents", "Adhesive and paint residue"],
        "included": [
            "Dust removal from surfaces",
            "Floor and window cleaning",
            "Debris collection",
            "Detailed room-by-room cleaning"
        ],
        "process": ["Rough clear-out", "Detail cleaning", "Final polish"],
        "benefits": ["Ready-for-occupation finish", "Faster handover"],
        "packages": [
            {"name": "Builder’s Clean", "price": "$430", "description": "Post-construction clean for new homes and renovations."},
            {"name": "Pre-Handover Clean", "price": "$540", "description": "Final clean before keys are handed over."},
            {"name": "Renovation Clean", "price": "$370", "description": "After-renovation cleaning for residential properties."}
        ],
        "related_services": ["builders-cleaning"],
        "locations": ["Adelaide"]
    },
    "pressure-washing": {
        "service_name": "Pressure Washing",
        "title": "Pressure Washing",
        "heading": "Pressure Washing & Exterior Cleaning",
        "description": "Pressure washing in {location} for driveways, patios, decks and building exteriors.",
        "overview": "Powerful pressure washing to remove grime, mould and weather stains from hard surfaces.",
        "hero_image": "/static/images/services/pressure-washing.svg",
        "gallery": [],
        "problems": ["Driveway oil stains", "Moss and mould on patios"],
        "included": [
            "Driveway and pathway cleaning",
            "Patio and deck washing",
            "Exterior wall cleaning",
            "High-pressure grime removal"
        ],
        "process": ["Assessment", "Safe pressure selection", "Surface washing and rinse"],
        "benefits": ["Improved curb appeal", "Moss and allergen reduction"],
        "packages": [
            {"name": "Driveway Wash", "price": "$180", "description": "High-pressure cleaning for driveways and paths."},
            {"name": "Exterior Wash", "price": "$260", "description": "Building exterior and facade cleaning."},
            {"name": "Complete Outdoor Wash", "price": "$340", "description": "Full property pressure washing service."}
        ],
        "related_services": ["window-cleaning"],
        "locations": ["Adelaide"]
    },
    "bathroom-cleaning": {
        "service_name": "Bathroom Cleaning",
        "title": "Bathroom Cleaning",
        "heading": "Bathroom Deep Cleaning & Sanitisation",
        "description": "Bathroom cleaning in {location} with thorough sanitation, grout and tile care.",
        "overview": "Deep bathroom cleaning that leaves Adelaide bathrooms fresh, sparkling and hygienic.",
        "hero_image": "/static/images/services/bathroom-cleaning.svg",
        "gallery": [],
        "problems": ["Grout staining", "Limescale and mould"],
        "included": [
            "Shower and bath cleaning",
            "Toilet and sink sanitisation",
            "Tile and grout scrubbing",
            "Mirror and fixture polish"
        ],
        "process": ["Descale and scrub", "Grout treatment", "Final sanitisation"],
        "benefits": ["Hygienic bathrooms", "Reduced mould risk"],
        "packages": [
            {"name": "Standard Bathroom Clean", "price": "$110", "description": "Complete bathroom cleaning for one bathroom."},
            {"name": "Deep Bathroom Clean", "price": "$170", "description": "Deep cleaning for bathrooms with heavy use."},
            {"name": "Luxury Bathroom Clean", "price": "$210", "description": "Premium bathroom detailing and sanitisation."}
        ],
        "related_services": ["deep-cleaning"],
        "locations": ["Adelaide"]
    },
    "kitchen-cleaning": {
        "service_name": "Kitchen Cleaning",
        "title": "Kitchen Cleaning",
        "heading": "Kitchen Cleaning & Degreasing",
        "description": "Kitchen cleaning in {location} for ovens, benchtops, splashbacks and appliances.",
        "overview": "Kitchen cleaning that removes grease, food residue and bacteria from every surface.",
        "hero_image": "/static/images/services/kitchen-cleaning.svg",
        "gallery": [],
        "problems": ["Greasy hobs", "Baked-on oven residues", "Sticky surfaces"],
        "included": [
            "Bench and appliance wipe down",
            "Oven and stove cleaning",
            "Sink and tap sanitisation",
            "Floor and cabinet cleaning"
        ],
        "process": ["Degrease surfaces", "Detail clean appliances", "Sanitise food-prep areas"],
        "benefits": ["Cleaner food prep surfaces", "Longer appliance life"],
        "packages": [
            {"name": "Standard Kitchen Clean", "price": "$140", "description": "Kitchen cleaning including surfaces and appliances."},
            {"name": "Deep Kitchen Clean", "price": "$210", "description": "Intensive degreasing and detail cleaning."},
            {"name": "Move-Out Kitchen Clean", "price": "$240", "description": "Kitchen cleaning for rental and sale-ready properties."}
        ],
        "related_services": ["oven-cleaning", "kitchen-deep-cleaning"],
        "locations": ["Adelaide"]
    },
    "deep-cleaning": {
        "service_name": "Deep Cleaning",
        "title": "Deep Cleaning",
        "heading": "Top-to-Bottom Deep Cleaning",
        "description": "Deep cleaning in {location} for kitchens, bathrooms, carpets and hard-to-reach areas.",
        "overview": "A detailed deep clean that refreshes homes and workplaces from top to bottom.",
        "hero_image": "/static/images/services/deep-cleaning.svg",
        "gallery": [],
        "problems": ["Dust in high areas", "Neglected corners and edges"],
        "included": [
            "High-level dusting and detail cleaning",
            "Deep kitchen and bathroom care",
            "Carpet and upholstery refresh",
            "Edge and corner sanitisation"
        ],
        "process": ["Room-by-room deep attention", "Targeted stain removal", "Final inspection"],
        "benefits": ["Comprehensive refresh", "Improved indoor hygiene"],
        "packages": [
            {"name": "Standard Deep Clean", "price": "$280", "description": "Deep cleaning for homes and offices."},
            {"name": "Premium Deep Clean", "price": "$390", "description": "Extended cleaning for large or high-use properties."},
            {"name": "Move-In Deep Clean", "price": "$340", "description": "Preparation cleaning for move-in homes."}
        ],
        "related_services": ["house-cleaning", "carpet-cleaning"],
        "locations": ["Adelaide"]
    },
    "move-in-cleaning": {
        "service_name": "Move In Cleaning",
        "title": "Move In Cleaning",
        "heading": "Move-In & New Home Cleaning",
        "description": "Move in cleaning in {location} that prepares new properties for a fresh start.",
        "overview": "Move in cleaning to make new houses and apartments ready for occupancy.",
        "hero_image": "/static/images/services/move-in-cleaning.svg",
        "gallery": [],
        "problems": ["Leftover dust from builders", "Packaging residue"],
        "included": [
            "Kitchen and bathroom sanitisation",
            "Floor and carpet care",
            "Window and surface cleaning",
            "Entry and hallway attention"
        ],
        "process": ["Pre-move check", "Full clean", "Final walkthrough"],
        "benefits": ["Move-in ready property", "Peace of mind"],
        "packages": [
            {"name": "Move-In Starter Clean", "price": "$260", "description": "Essential cleaning for new homes."},
            {"name": "Move-In Deep Clean", "price": "$330", "description": "Detailed cleaning for all living areas."},
            {"name": "Premium Move-In Clean", "price": "$390", "description": "Full property preparation and sanitisation."}
        ],
        "related_services": ["deep-cleaning", "post-construction-cleaning"],
        "locations": ["Adelaide"]
    },
    "move-out-cleaning": {
        "service_name": "Move Out Cleaning",
        "title": "Move Out Cleaning",
        "heading": "Move-Out & End of Lease Cleaning",
        "description": "Move out cleaning in {location} for end-of-lease and property handover requirements.",
        "overview": "Move out cleaning designed to leave rental properties in inspection-ready condition.",
        "hero_image": "/static/images/services/move-out-cleaning.svg",
        "gallery": [],
        "problems": ["Inspection failures", "Lingering odours and stains"],
        "included": [
            "Kitchen, bathroom and carpet cleaning",
            "Dusting and surface cleaning",
            "Window and door cleaning",
            "Skirting and corner detail cleaning"
        ],
        "process": ["Site assessment", "Targeted deep clean", "Final inspection report"],
        "benefits": ["Inspection-ready condition", "Higher bond return chances"],
        "packages": [
            {"name": "Move-Out Standard", "price": "$300", "description": "Reliable move out cleaning for rental homes."},
            {"name": "Move-Out Premium", "price": "$420", "description": "Deeper cleaning with extra attention to detail."},
            {"name": "Bond Ready Clean", "price": "$460", "description": "Move out cleaning for full bond return preparation."}
        ],
        "related_services": ["end-of-lease-cleaning", "bond-cleaning"],
        "locations": ["Adelaide"]
    },
    "spring-cleaning": {
        "service_name": "Spring Cleaning",
        "title": "Spring Cleaning",
        "heading": "Seasonal Spring Cleaning",
        "description": "Spring cleaning in {location} for seasonal deep cleaning and home refreshes.",
        "overview": "Seasonal spring cleaning that brings a fresh renewal to your home or workspace.",
        "hero_image": "/static/images/services/spring-cleaning.svg",
        "gallery": [],
        "problems": ["Built-up winter grime", "Dust and allergens"],
        "included": [
            "Complete room-by-room deep clean",
            "Window and glass cleaning",
            "Carpet and upholstery refresh",
            "High-level dusting and baseboards"
        ],
        "process": ["Deep room-by-room clean", "Window and carpet refresh"],
        "benefits": ["Seasonal fresh start", "Allergen reduction"],
        "packages": [
            {"name": "Spring Home Clean", "price": "$320", "description": "Complete spring refresh for homes."},
            {"name": "Spring Deep Clean", "price": "$420", "description": "Intensive seasonal clean for extensive results."},
            {"name": "Spring Office Clean", "price": "$380", "description": "Seasonal refresh for office and commercial spaces."}
        ],
        "related_services": ["deep-cleaning"],
        "locations": ["Adelaide"]
    },
    "oven-cleaning": {
        "service_name": "Oven Cleaning",
        "title": "Oven Cleaning",
        "heading": "Professional Oven Cleaning",
        "description": "Professional oven cleaning in {location} for residential and commercial kitchens.",
        "overview": "Specialist oven cleaning that removes built-up grease and burnt residue safely.",
        "hero_image": "/static/images/services/oven-cleaning.svg",
        "gallery": [],
        "problems": ["Baked-on grease", "Burnt-on residues"],
        "included": [
            "Interior oven deep clean",
            "Racks and trays cleaning",
            "Stovetop and hob cleaning",
            "Appliance polishing and finish"
        ],
        "process": ["Degrease", "Soak and scrub", "Rinse and polish"],
        "benefits": ["Improved oven performance", "Safer cooking environment"],
        "packages": [
            {"name": "Standard Oven Clean", "price": "$120", "description": "Professional cleaning for a single oven."},
            {"name": "Deep Oven Clean", "price": "$180", "description": "Intensive cleaning for heavily soiled ovens."},
            {"name": "Kitchen Appliance Package", "price": "$250", "description": "Oven, stovetop and other appliance cleaning."}
        ],
        "related_services": ["kitchen-cleaning"],
        "locations": ["Adelaide"]
    },
    "exit-cleaning": {
        "service_name": "Exit Cleaning",
        "title": "Exit Cleaning",
        "heading": "Exit & Pre-Sale Cleaning",
        "description": "Exit cleaning in {location} to prepare properties for tenant moving or sale.",
        "overview": "Professional exit cleaning designed to meet landlord and property standards.",
        "hero_image": "/static/images/services/exit-cleaning.svg",
        "gallery": [],
        "problems": ["Last-minute cleaning needs", "Inspection items"],
        "included": [
            "Full property deep clean",
            "Carpet and floor care",
            "Kitchen and bathroom sanitisation",
            "Move-out inspection-ready finish"
        ],
        "process": ["Targeted clean", "Inspection checklist", "Final polish"],
        "benefits": ["Faster property sale or bond return", "Hassle-free handover"],
        "packages": [
            {"name": "Standard Exit Clean", "price": "$350", "description": "Complete exit cleaning for rental properties."},
            {"name": "Premium Exit Clean", "price": "$480", "description": "Detailed exit cleaning with extra care."},
            {"name": "Express Exit Clean", "price": "$420", "description": "Fast turnaround exit cleaning service."}
        ],
        "related_services": ["move-out-cleaning"],
        "locations": ["Adelaide"]
    },
    "carpet-cleaning": {
        "service_name": "Carpet Cleaning",
        "title": "Carpet Cleaning",
        "heading": "Carpet Cleaning & Restoration",
        "description": "Carpet cleaning in {location} using hot water extraction and steam methods.",
        "overview": "Professional carpet cleaning that removes deep-seated dirt, stains and odours.",
        "hero_image": "/static/images/services/carpet-cleaning.svg",
        "gallery": [],
        "problems": ["Stubborn stains", "Odours and allergens"],
        "included": [
            "Pre-vacuum and stain treatment",
            "Hot water extraction cleaning",
            "Carpet grooming and fluffing",
            "Rapid drying with air circulation"
        ],
        "process": ["Assess fibres", "Pre-treat stains", "Hot water extraction"],
        "benefits": ["Restored carpets", "Allergen reduction"],
        "packages": [
            {"name": "Room Carpet Clean", "price": "$160", "description": "Professional cleaning for single rooms."},
            {"name": "Whole Home Carpet", "price": "$350", "description": "Carpet cleaning for entire residential property."},
            {"name": "Commercial Carpet Clean", "price": "$420", "description": "Large-scale carpet cleaning for commercial spaces."}
        ],
        "related_services": ["carpet-steam-cleaning"],
        "locations": ["Adelaide"]
    }
}

# Extended service definition example for richer landing pages.
# New keys supported: title, heading, description, overview, hero_image, gallery,
# problems, included, process, benefits, ideal_for, industries, packages, faqs,
# related_services, locations
SERVICE_DEFINITIONS.update({
    "kitchen-deep-cleaning": {
        "service_name": "Kitchen Deep Cleaning",
        "title": "Kitchen Deep Cleaning",
        "heading": "Professional Kitchen Deep Cleaning in Adelaide",
        "description": "Kitchen deep cleaning Adelaide businesses and homes rely on to remove grease, food residues and hidden contaminants while restoring hygiene and sparkle.",
        "meta_description": "Kitchen Deep Cleaning Adelaide with food-safe products, commercial-grade equipment, and trusted local cleaners for restaurants, homes and commercial kitchens.",
        "introduction": "When Adelaide kitchens need more than a surface clean, our Kitchen Deep Cleaning service delivers a full hygiene refresh for ovens, rangehoods, splashbacks, floors and food prep areas. This service is ideal for busy households, hospitality venues and property managers who need a professional team to remove stubborn grease, grime, odours and hidden bacteria. Our crew works with food-safe solutions, steam cleaning, HEPA vacuuming and commercial-grade degreasers to bring every kitchen area back to a sanitary and polished finish. With a focus on Adelaide-specific conditions, we handle sandy tiles, baked-on oven residue, sticky cupboard doors and tight corners around appliances. The result is a healthier kitchen, stronger visual appeal, and a cleaner working environment for cooking, serving and entertaining.",
        "overview": "Our kitchen deep cleaning service tackles heavy grease, baked-on food, and hard-to-reach contamination using food-safe, commercial-grade methods to make kitchens hygienic, safe and inspection-ready.",
        "hero_image": "/static/images/services/kitchen-hero.svg",
        "image_alt": "Kitchen deep cleaning team working in Adelaide kitchen",
        "gallery": [
            "kitchen-before.webp",
            "kitchen-after.webp",
            "kitchen-oven-clean.svg"
        ],
        "problems": [
            "Baked-on grease in ovens and rangehoods",
            "Stubborn food stains on benches and splashbacks",
            "Blocked or odorous drains",
            "Greasy exhaust filters and ducting",
            "Mould and bacteria in grout and seals",
            "Sticky residue on cabinet handles and appliance surfaces"
        ],
        "included": [
            "Full oven degrease and interior clean",
            "Rangehood and filter degreasing",
            "Sanitise benches, splashbacks and prep surfaces",
            "Clean and sanitise sinks, taps and drains",
            "Cabinet exterior wipe-down and handles",
            "Fridge exterior clean and hygienic wipe",
            "Microwave interior clean",
            "Steam-clean or mop floors and grout",
            "Polish stainless steel appliances",
            "Remove food residues from behind appliances",
            "Final inspection and photographic evidence",
            "Food-safe sanitisation of all prep areas"
        ],
        "process": [
            "Assessment - site & risk assessment to scope the job",
            "Preparation - move lightweight items, protect surfaces",
            "Degreasing & Steam Cleaning - ovens, hobs and floors",
            "Hand-detailing - cupboards, fittings and seals",
            "Quality Inspection - manager sign-off and customer walkthrough"
        ],
        "benefits": [
            "Improved hygiene and food-safety",
            "Reduced odours and pest risk",
            "Extended life of appliances and finishes",
            "A better-looking kitchen that builds customer confidence"
        ],
        "ideal_for": [
            "Restaurants, cafés and hospitality businesses",
            "Property managers and real estate agencies",
            "Busy families and households",
            "Commercial kitchens at retail and institutional sites"
        ],
        "industries": [
            "Hospitality",
            "Retail",
            "Property Management",
            "Healthcare (non-sterile areas)",
            "Education and childcare facilities"
        ],
        "packages": [
            {"name": "Basic Kitchen Deep Clean", "price": "$220", "description": "Surface degrease, benches, sinks, microwave and light polish."},
            {"name": "Standard Kitchen Deep Clean", "price": "$420", "description": "Includes oven degrease, rangehood filter clean and steam floor cleaning."},
            {"name": "Premium Kitchen Deep Clean", "price": "$680", "description": "Full-service deep clean with photographic report and manager sign-off."},
            {"name": "Custom Commercial Quote", "price": "Contact", "description": "Custom scope for hospitality and high-volume kitchens."}
        ],
        "faqs": [
            {"q": "How much does Kitchen Deep Cleaning cost in Adelaide?", "a": "Costs vary by size and condition; our Basic package starts from $220 and a site assessment provides an accurate quote."},
            {"q": "Do you use food-safe products?", "a": "Yes — all products used in kitchen areas are food-safe and suitable for food preparation zones."},
            {"q": "How long will the service take?", "a": "Typical domestic kitchens take 2–4 hours; commercial sites depend on size and equipment — we provide time estimates in the quote."}
        ],
        "related_services": [
            "commercial-cleaning",
            "carpet-steam-cleaning",
            "window-cleaning",
            "bond-cleaning"
        ],
        "locations": [
            "Adelaide CBD",
            "North Adelaide",
            "Norwood",
            "Burnside",
            "Glenelg",
            "Unley",
            "Prospect",
            "Mawson Lakes",
            "Salisbury",
            "Golden Grove",
            "Tea Tree Gully",
            "Mount Barker"
        ]
    }
})
SERVICE_SLUG_ALIASES = {
    "bathroom-deep-cleaning": "bathroom-cleaning",
    "commercial-office-cleaning": "office-cleaning",
    "inspection-cleaning": "bond-cleaning",
    "kitchen-deep-cleaning": "kitchen-cleaning",
    "medical-cleaning": "commercial-cleaning",
    "medical-cleaning-adelaide": "commercial-cleaning",
    "inspection-cleaning-adelaide": "bond-cleaning",
}

LOCATION_ALIASES = {
    "adelaide": "Adelaide",
    "prospect": "Prospect",
    "mawson-lakes": "Mawson Lakes",
    "salisbury": "Salisbury",
    "north-adelaide": "North Adelaide",
    "glenelg": "Glenelg",
    "norwood": "Norwood",
    "unley": "Unley",
    "burnside": "Burnside",
    "modbury": "Modbury"
}
