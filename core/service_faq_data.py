"""
Service-specific FAQ content for YD Commercial Cleaning Services.

This file provides SEO-focused, service-specific FAQ content while keeping
the existing SERVICE_DEFINITIONS structure unchanged.

FAQ priority:
    1. FAQs stored on the Service model
    2. FAQs defined here
    3. Existing generic fallback in views.py

Answers may use:
    {location}
    {location_name}
    {service_title}
    {service_name}
"""

SERVICE_FAQS = {

    # ============================================================
    # COMMERCIAL CLEANING
    # ============================================================

    "commercial-cleaning": [
        {
            "q": "What does commercial cleaning include?",
            "a": (
                "Commercial cleaning can include office areas, reception spaces, "
                "workstations, kitchens, bathrooms, floors, shared areas and "
                "high-touch surfaces. The cleaning scope is tailored to the "
                "requirements of each business in {location}."
            ),
        },
        {
            "q": "Can commercial cleaning be scheduled outside business hours?",
            "a": (
                "Yes. Commercial cleaning can be arranged around your operating "
                "hours, including suitable early morning, evening or other "
                "agreed cleaning times to minimise disruption to staff and customers."
            ),
        },
        {
            "q": "Do you clean retail stores and warehouses?",
            "a": (
                "Yes. Our commercial cleaning services can support retail stores, "
                "warehouses, offices and other business premises, with the scope "
                "adjusted to the size, layout and daily use of the property."
            ),
        },
        {
            "q": "Can commercial cleaning be arranged on a regular schedule?",
            "a": (
                "Yes. Businesses can arrange recurring cleaning based on their "
                "requirements, such as weekly or other agreed schedules. We can "
                "review your premises and recommend an appropriate cleaning scope."
            ),
        },
        {
            "q": "How do I request a commercial cleaning quote?",
            "a": (
                "Contact YD Commercial Cleaning Services with your business "
                "location, property type, approximate size and preferred cleaning "
                "frequency. We can then review the requirements and prepare a "
                "tailored quote."
            ),
        },
    ],

    # ============================================================
    # OFFICE CLEANING
    # ============================================================

    "office-cleaning": [
        {
            "q": "What areas are covered by office cleaning?",
            "a": (
                "Office cleaning can cover workstations, desks, meeting rooms, "
                "reception areas, kitchens, bathrooms, floors and commonly touched "
                "surfaces. The scope can be adjusted to suit your workplace in "
                "{location}."
            ),
        },
        {
            "q": "Can office cleaners work after business hours?",
            "a": (
                "Yes. Office cleaning can be scheduled at suitable times outside "
                "normal business operations where practical, helping reduce "
                "disruption to employees, clients and visitors."
            ),
        },
        {
            "q": "Do you provide regular office cleaning?",
            "a": (
                "Yes. Regular office cleaning can be arranged according to the "
                "needs of your workplace, including recurring cleaning for offices "
                "that require consistent presentation and hygiene."
            ),
        },
        {
            "q": "Can you clean office kitchens and bathrooms?",
            "a": (
                "Yes. Office kitchens, break areas and bathrooms can be included "
                "within the cleaning scope, together with floors, shared surfaces "
                "and other commonly used workplace areas."
            ),
        },
        {
            "q": "Do you provide office cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides professional office "
                "cleaning in {location} and surrounding Adelaide areas, subject to "
                "availability and the required service scope."
            ),
        },
    ],

    # ============================================================
    # END OF LEASE CLEANING
    # ============================================================

    "end-of-lease-cleaning": [
        {
            "q": "What is included in end of lease cleaning?",
            "a": (
                "End of lease cleaning can include kitchens, bathrooms, floors, "
                "carpets, windows, surfaces, skirting boards and other areas "
                "requiring detailed attention before a rental property is handed "
                "back."
            ),
        },
        {
            "q": "Is end of lease cleaning the same as bond cleaning?",
            "a": (
                "The terms are often used for similar rental cleaning services, "
                "but the exact requirements depend on the tenancy and property. "
                "We can tailor the cleaning scope to the expected handover "
                "requirements."
            ),
        },
        {
            "q": "Do you clean ovens during an end of lease clean?",
            "a": (
                "Oven cleaning can be included as part of the kitchen cleaning "
                "scope. This is particularly useful when built-up grease or food "
                "residue needs detailed attention before a rental inspection."
            ),
        },
        {
            "q": "Can end of lease cleaning include carpets?",
            "a": (
                "Yes. Carpet cleaning can be added where carpets require more than "
                "standard vacuuming, including stain treatment or deeper carpet "
                "cleaning depending on the property's condition."
            ),
        },
        {
            "q": "Do you provide end of lease cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides end of lease "
                "cleaning in {location} and surrounding Adelaide suburbs, subject "
                "to availability."
            ),
        },
    ],

    # ============================================================
    # BOND CLEANING
    # ============================================================

    "bond-cleaning": [
        {
            "q": "What does bond cleaning cover?",
            "a": (
                "Bond cleaning focuses on detailed cleaning required when leaving "
                "a rental property. Depending on the agreed scope, this can include "
                "kitchens, ovens, bathrooms, floors, carpets, windows, surfaces "
                "and other inspection areas."
            ),
        },
        {
            "q": "Can bond cleaning help prepare a property for inspection?",
            "a": (
                "Yes. A detailed bond clean is designed to prepare the property "
                "for handover and inspection by addressing common areas where dirt, "
                "grease, dust and stains may be noticed."
            ),
        },
        {
            "q": "Do you clean the oven as part of bond cleaning?",
            "a": (
                "Oven cleaning can be included in the bond cleaning scope. We can "
                "focus on built-up grease, burnt food residue, racks, trays and "
                "other accessible oven surfaces."
            ),
        },
        {
            "q": "Can carpet cleaning be added to a bond clean?",
            "a": (
                "Yes. Carpet cleaning can be added where the rental property "
                "requires deeper carpet treatment beyond normal vacuuming."
            ),
        },
        {
            "q": "Do you provide bond cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides bond cleaning in "
                "{location} and surrounding Adelaide suburbs, depending on "
                "availability and property requirements."
            ),
        },
    ],

    # ============================================================
    # HOUSE CLEANING
    # ============================================================

    "house-cleaning": [
        {
            "q": "What is included in house cleaning?",
            "a": (
                "House cleaning can include dusting, vacuuming, floor care, "
                "kitchen cleaning, bathroom cleaning, bedroom areas and other "
                "regular household surfaces. The scope can be tailored to your "
                "home in {location}."
            ),
        },
        {
            "q": "Can I book a one-off house clean?",
            "a": (
                "Yes. One-off house cleaning is available for homes that need a "
                "general refresh, additional cleaning before an event or extra "
                "attention to areas that have built up dirt and grime."
            ),
        },
        {
            "q": "Do you provide regular house cleaning?",
            "a": (
                "Yes. Regular house cleaning can be arranged for households that "
                "prefer an ongoing cleaning routine, with the frequency adjusted "
                "to the property's needs."
            ),
        },
        {
            "q": "Can house cleaning include kitchens and bathrooms?",
            "a": (
                "Yes. Kitchens and bathrooms can be included in the cleaning "
                "scope, along with living areas, bedrooms, floors and other "
                "commonly used areas of the home."
            ),
        },
        {
            "q": "Do you provide house cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides professional house "
                "cleaning in {location} and surrounding Adelaide suburbs."
            ),
        },
    ],

    # ============================================================
    # REGULAR HOUSE CLEANING
    # ============================================================

    "regular-house-cleaning": [
        {
            "q": "How often should I book regular house cleaning?",
            "a": (
                "The ideal frequency depends on household size, occupancy, pets, "
                "lifestyle and how quickly the property becomes dirty. Weekly or "
                "fortnightly cleaning can work well for many households."
            ),
        },
        {
            "q": "What is normally included in regular house cleaning?",
            "a": (
                "Regular cleaning can include dusting, vacuuming, mopping, kitchen "
                "and bathroom maintenance, surface wiping and other agreed routine "
                "cleaning tasks."
            ),
        },
        {
            "q": "Can I change my cleaning frequency?",
            "a": (
                "Cleaning frequency can be discussed according to your household's "
                "needs. We can adjust the service arrangement when a different "
                "schedule is more suitable."
            ),
        },
        {
            "q": "Is regular cleaning suitable for busy families?",
            "a": (
                "Yes. Recurring cleaning is particularly useful for households "
                "that want consistent maintenance without having to organise a "
                "complete clean every time the property needs attention."
            ),
        },
        {
            "q": "Do you provide recurring house cleaning in {location}?",
            "a": (
                "Yes. Regular house cleaning can be arranged in {location} and "
                "surrounding Adelaide areas, subject to availability."
            ),
        },
    ],

    # ============================================================
    # WINDOW CLEANING
    # ============================================================

    "window-cleaning": [
        {
            "q": "What does professional window cleaning include?",
            "a": (
                "Window cleaning can include accessible interior and exterior "
                "glass, frames, sills and finishing work to remove common dirt, "
                "marks and water residue."
            ),
        },
        {
            "q": "Can you clean both the inside and outside of windows?",
            "a": (
                "Yes. Interior and exterior window cleaning can be included where "
                "the windows are safely accessible and suitable for the agreed "
                "cleaning method."
            ),
        },
        {
            "q": "Can window cleaning remove water marks and streaks?",
            "a": (
                "Professional glass cleaning can reduce common streaks, dirt and "
                "water residue. The final result can vary depending on the age and "
                "condition of the glass."
            ),
        },
        {
            "q": "Do you clean commercial windows?",
            "a": (
                "Yes. Window cleaning can be arranged for offices, retail premises "
                "and other suitable commercial properties as well as residential "
                "homes."
            ),
        },
        {
            "q": "Do you provide window cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides window cleaning in "
                "{location} and surrounding Adelaide areas, subject to access and "
                "service requirements."
            ),
        },
    ],

    # ============================================================
    # CARPET STEAM CLEANING
    # ============================================================

    "carpet-steam-cleaning": [
        {
            "q": "What is carpet steam cleaning?",
            "a": (
                "Carpet steam cleaning uses professional hot water extraction "
                "methods to clean carpet fibres more deeply than routine vacuuming, "
                "helping remove embedded dirt, stains and odours."
            ),
        },
        {
            "q": "Can carpet steam cleaning remove stains?",
            "a": (
                "Professional carpet cleaning can treat many common stains, but "
                "results depend on the type of stain, how long it has been present "
                "and the condition of the carpet fibres."
            ),
        },
        {
            "q": "How long does a professionally cleaned carpet take to dry?",
            "a": (
                "Drying time depends on carpet type, ventilation, humidity, the "
                "amount of water used and site conditions. Good airflow can help "
                "the carpet dry more efficiently."
            ),
        },
        {
            "q": "Can carpet steam cleaning be used in offices?",
            "a": (
                "Yes. Professional carpet steam cleaning can be suitable for "
                "offices, commercial premises and other carpeted workplaces when "
                "scheduled around the property's operating requirements."
            ),
        },
        {
            "q": "Do you provide carpet steam cleaning in {location}?",
            "a": (
                "Yes. Carpet steam cleaning is available in {location} and "
                "surrounding Adelaide areas, subject to availability."
            ),
        },
    ],

    # ============================================================
    # BUILDERS CLEANING
    # ============================================================

    "builders-cleaning": [
        {
            "q": "What is builders cleaning?",
            "a": (
                "Builders cleaning is detailed cleaning carried out after building "
                "or renovation work to remove construction dust, debris, residue "
                "and other materials before a property is occupied or handed over."
            ),
        },
        {
            "q": "What construction residue can builders cleaning address?",
            "a": (
                "Depending on the surface and condition, builders cleaning can "
                "address construction dust, grout residue, paint splashes, surface "
                "debris and other post-building residue."
            ),
        },
        {
            "q": "Is builders cleaning suitable for new homes?",
            "a": (
                "Yes. Builders cleaning can prepare newly constructed homes for "
                "final presentation, inspection, handover or occupation."
            ),
        },
        {
            "q": "Can builders cleaning be used after renovations?",
            "a": (
                "Yes. Renovation projects often leave fine dust and building "
                "residue throughout the property. A detailed builders clean can "
                "focus on affected rooms and surfaces."
            ),
        },
        {
            "q": "Do you provide builders cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides builders cleaning "
                "in {location} and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # POST CONSTRUCTION CLEANING
    # ============================================================

    "post-construction-cleaning": [
        {
            "q": "What is post construction cleaning?",
            "a": (
                "Post construction cleaning prepares a newly built or renovated "
                "property by removing construction dust, debris, residue and "
                "surface marks before occupation or handover."
            ),
        },
        {
            "q": "When should post construction cleaning be completed?",
            "a": (
                "Post construction cleaning is generally completed after major "
                "building work has finished and before the property is occupied, "
                "presented to clients or handed over."
            ),
        },
        {
            "q": "Does post construction cleaning include windows and floors?",
            "a": (
                "Yes. Windows, floors and other finished surfaces can be included "
                "where they require removal of construction dust, residue or "
                "general post-build debris."
            ),
        },
        {
            "q": "Can you clean a property after a renovation?",
            "a": (
                "Yes. Post-renovation cleaning can focus on rooms and surfaces "
                "affected by building work, helping prepare the property for its "
                "next stage of use."
            ),
        },
        {
            "q": "Do you provide post construction cleaning in {location}?",
            "a": (
                "Yes. Post construction cleaning is available in {location} and "
                "surrounding Adelaide areas, subject to the project scope."
            ),
        },
    ],

    # ============================================================
    # PRESSURE WASHING
    # ============================================================

    "pressure-washing": [
        {
            "q": "What surfaces can pressure washing clean?",
            "a": (
                "Pressure washing can be suitable for compatible hard exterior "
                "surfaces such as driveways, paths, patios and selected building "
                "exteriors, depending on the surface condition and cleaning "
                "requirements."
            ),
        },
        {
            "q": "Can pressure washing remove mould and outdoor grime?",
            "a": (
                "Pressure washing can help remove accumulated dirt, grime, algae "
                "and some surface growth from suitable hard surfaces. The method "
                "used depends on the material being cleaned."
            ),
        },
        {
            "q": "Can you pressure clean driveways?",
            "a": (
                "Yes. Driveway cleaning can be included where the surface is "
                "suitable for pressure cleaning. The cleaning approach is adjusted "
                "to the material and condition of the driveway."
            ),
        },
        {
            "q": "Is pressure washing safe for every outdoor surface?",
            "a": (
                "No. Pressure levels and cleaning methods should be selected based "
                "on the material and its condition. A suitable assessment helps "
                "reduce the risk of surface damage."
            ),
        },
        {
            "q": "Do you provide pressure washing in {location}?",
            "a": (
                "YD Commercial Cleaning Services provides pressure washing in "
                "{location} and surrounding Adelaide areas for suitable exterior "
                "surfaces."
            ),
        },
    ],

    # ============================================================
    # BATHROOM CLEANING
    # ============================================================

    "bathroom-cleaning": [
        {
            "q": "What is included in bathroom cleaning?",
            "a": (
                "Bathroom cleaning can include showers, baths, toilets, sinks, "
                "tiles, grout, mirrors, fixtures and floor cleaning, with "
                "sanitisation of appropriate surfaces."
            ),
        },
        {
            "q": "Can bathroom cleaning remove soap scum and limescale?",
            "a": (
                "Professional bathroom cleaning can target soap residue, mineral "
                "build-up and general grime using cleaning methods appropriate for "
                "the surface."
            ),
        },
        {
            "q": "Can you clean bathroom grout?",
            "a": (
                "Yes. Grout can receive detailed cleaning where dirt, soap residue "
                "or staining has accumulated. Results depend on the condition and "
                "age of the grout."
            ),
        },
        {
            "q": "Can bathroom cleaning address mould?",
            "a": (
                "Cleaning can target visible mould and build-up on suitable "
                "surfaces. Persistent moisture problems may also require attention "
                "to the underlying cause of the mould."
            ),
        },
        {
            "q": "Do you provide bathroom cleaning in {location}?",
            "a": (
                "Yes. Professional bathroom cleaning is available in {location} "
                "and surrounding Adelaide suburbs."
            ),
        },
    ],

    # ============================================================
    # KITCHEN CLEANING
    # ============================================================

    "kitchen-cleaning": [
        {
            "q": "What is included in kitchen cleaning?",
            "a": (
                "Kitchen cleaning can include benchtops, splashbacks, sinks, taps, "
                "cooktops, accessible appliance surfaces, cabinets, floors and "
                "other agreed kitchen areas."
            ),
        },
        {
            "q": "Can kitchen cleaning remove built-up grease?",
            "a": (
                "Yes. Kitchen cleaning can focus on grease and food residue on "
                "suitable surfaces using cleaning products and methods appropriate "
                "for the material."
            ),
        },
        {
            "q": "Can you clean ovens as part of kitchen cleaning?",
            "a": (
                "Yes. Oven cleaning can be included when required, particularly "
                "where baked-on grease and food residue need additional attention."
            ),
        },
        {
            "q": "Is kitchen cleaning suitable for rental properties?",
            "a": (
                "Yes. Kitchen cleaning can be arranged for homes, rental "
                "properties and other suitable premises, including properties "
                "being prepared for inspection or handover."
            ),
        },
        {
            "q": "Do you provide kitchen cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides kitchen cleaning "
                "in {location} and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # DEEP CLEANING
    # ============================================================

    "deep-cleaning": [
        {
            "q": "What is included in a deep cleaning service?",
            "a": (
                "Deep cleaning focuses on areas that may receive less attention "
                "during routine cleaning, including corners, edges, detailed "
                "surfaces, kitchens, bathrooms and other agreed areas."
            ),
        },
        {
            "q": "When should I book a deep clean instead of regular cleaning?",
            "a": (
                "A deep clean can be useful when a property has accumulated dirt "
                "and grime, before establishing a regular cleaning routine, after "
                "a busy period or when particular areas need extra attention."
            ),
        },
        {
            "q": "Can deep cleaning be customised for my property?",
            "a": (
                "Yes. Deep cleaning can be tailored to the condition, size and "
                "priority areas of the property, allowing the cleaning scope to "
                "focus on the areas that need the most attention."
            ),
        },
        {
            "q": "Can deep cleaning be arranged for offices?",
            "a": (
                "Yes. Deep cleaning can be arranged for suitable offices and "
                "workplaces where additional attention is needed beyond routine "
                "maintenance cleaning."
            ),
        },
        {
            "q": "Do you provide deep cleaning in {location}?",
            "a": (
                "Yes. Professional deep cleaning is available in {location} and "
                "surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # MOVE IN CLEANING
    # ============================================================

    "move-in-cleaning": [
        {
            "q": "What does move-in cleaning include?",
            "a": (
                "Move-in cleaning can include kitchens, bathrooms, floors, "
                "surfaces, windows and other areas that benefit from a detailed "
                "clean before a new household moves into the property."
            ),
        },
        {
            "q": "Should I book move-in cleaning before moving furniture in?",
            "a": (
                "Where practical, cleaning before furniture is moved in can make "
                "many areas easier to access and clean, particularly floors, "
                "corners and empty rooms."
            ),
        },
        {
            "q": "Can move-in cleaning remove leftover construction dust?",
            "a": (
                "Yes. Where a property has recently been built or renovated, the "
                "cleaning scope can focus on suitable surfaces affected by dust "
                "and post-construction residue."
            ),
        },
        {
            "q": "Can move-in cleaning include kitchen and bathroom sanitisation?",
            "a": (
                "Yes. Kitchen and bathroom cleaning can be included to prepare "
                "these frequently used areas before the property is occupied."
            ),
        },
        {
            "q": "Do you provide move-in cleaning in {location}?",
            "a": (
                "Yes. Move-in cleaning is available in {location} and surrounding "
                "Adelaide suburbs."
            ),
        },
    ],

    # ============================================================
    # MOVE OUT CLEANING
    # ============================================================

    "move-out-cleaning": [
        {
            "q": "What is move-out cleaning?",
            "a": (
                "Move-out cleaning is a detailed cleaning service designed to "
                "prepare a property after occupants leave, with attention to "
                "kitchens, bathrooms, floors, surfaces and other agreed areas."
            ),
        },
        {
            "q": "Is move-out cleaning suitable for rental properties?",
            "a": (
                "Yes. Move-out cleaning can help prepare rental properties for "
                "handover, inspection or the arrival of new occupants."
            ),
        },
        {
            "q": "Can move-out cleaning include carpet cleaning?",
            "a": (
                "Yes. Carpet cleaning can be added when carpets require deeper "
                "cleaning beyond standard vacuuming."
            ),
        },
        {
            "q": "Can move-out cleaning include oven and kitchen cleaning?",
            "a": (
                "Yes. Kitchen and oven cleaning can be included in the agreed "
                "move-out cleaning scope where additional detail is required."
            ),
        },
        {
            "q": "Do you provide move-out cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides move-out cleaning "
                "in {location} and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # SPRING CLEANING
    # ============================================================

    "spring-cleaning": [
        {
            "q": "What is included in spring cleaning?",
            "a": (
                "Spring cleaning can include detailed room-by-room cleaning, "
                "dusting, windows, floors, carpets, high-level areas and other "
                "tasks selected to give the property a thorough seasonal refresh."
            ),
        },
        {
            "q": "Is spring cleaning only for houses?",
            "a": (
                "No. Spring cleaning can also be suitable for offices and other "
                "appropriate properties that need a detailed seasonal refresh."
            ),
        },
        {
            "q": "Can spring cleaning target areas I normally miss?",
            "a": (
                "Yes. A spring clean can focus on less frequently cleaned areas "
                "such as corners, edges, high-level surfaces, detailed fixtures "
                "and other agreed areas."
            ),
        },
        {
            "q": "Can I combine spring cleaning with carpet or window cleaning?",
            "a": (
                "Yes. Carpet and window cleaning can be incorporated into the "
                "overall cleaning scope when the property requires additional "
                "seasonal attention."
            ),
        },
        {
            "q": "Do you provide spring cleaning in {location}?",
            "a": (
                "Yes. Professional spring cleaning is available in {location} "
                "and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # OVEN CLEANING
    # ============================================================

    "oven-cleaning": [
        {
            "q": "What does professional oven cleaning include?",
            "a": (
                "Oven cleaning can focus on the interior, racks, trays, cooktop "
                "and other accessible areas, depending on the appliance and agreed "
                "scope."
            ),
        },
        {
            "q": "Can oven cleaning remove baked-on grease?",
            "a": (
                "Professional oven cleaning is designed to target built-up grease "
                "and burnt food residue using appropriate cleaning methods. Results "
                "depend on the condition and age of the appliance."
            ),
        },
        {
            "q": "Do you clean oven racks and trays?",
            "a": (
                "Yes. Oven racks and trays can be included in the cleaning scope "
                "when they are suitable for the selected cleaning method."
            ),
        },
        {
            "q": "Can oven cleaning be booked with kitchen cleaning?",
            "a": (
                "Yes. Oven cleaning can be combined with broader kitchen cleaning "
                "when customers want the surrounding benches, appliances, "
                "splashbacks and other kitchen areas cleaned as well."
            ),
        },
        {
            "q": "Do you provide oven cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides professional oven "
                "cleaning in {location} and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # MEDICAL CLEANING
    # ============================================================

    "medical-cleaning": [
        {
            "q": "What does medical cleaning include?",
            "a": (
                "Medical cleaning can include consultation rooms, reception and "
                "waiting areas, bathrooms, floors, high-touch surfaces and other "
                "appropriate areas of a healthcare facility. The cleaning scope is "
                "tailored to the requirements of the site."
            ),
        },
        {
            "q": "Do you provide cleaning for medical centres in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides professional "
                "medical cleaning for suitable clinics, dental practices, allied "
                "health facilities and medical environments in {location}."
            ),
        },
        {
            "q": "Why is professional healthcare cleaning important?",
            "a": (
                "Consistent professional cleaning helps maintain hygienic and "
                "presentable healthcare environments, particularly around "
                "high-touch surfaces, patient areas and shared spaces."
            ),
        },
        {
            "q": "Can medical cleaning be scheduled regularly?",
            "a": (
                "Yes. Healthcare facilities can arrange recurring cleaning "
                "according to their operating requirements, patient traffic and "
                "agreed cleaning scope."
            ),
        },
        {
            "q": "Can waiting rooms and consultation rooms be cleaned?",
            "a": (
                "Yes. Waiting rooms, reception areas and suitable consultation "
                "rooms can be included in the cleaning plan, together with other "
                "agreed areas of the healthcare facility."
            ),
        },
    ],

    # ============================================================
    # INSPECTION CLEANING
    # ============================================================

    "inspection-cleaning": [
        {
            "q": "What is inspection cleaning?",
            "a": (
                "Inspection cleaning prepares a rental property for a landlord, "
                "property manager or routine rental inspection by focusing on "
                "areas commonly reviewed during the inspection."
            ),
        },
        {
            "q": "Is inspection cleaning the same as bond cleaning?",
            "a": (
                "No. Inspection cleaning is generally focused on preparing a "
                "property for a routine inspection, while bond cleaning is usually "
                "associated with the end of a tenancy and property handover."
            ),
        },
        {
            "q": "What areas are commonly addressed before a rental inspection?",
            "a": (
                "Common areas include kitchens, bathrooms, floors, carpets, "
                "windows, surfaces, skirting boards, corners and other visible "
                "areas identified in the property's cleaning requirements."
            ),
        },
        {
            "q": "Can tenants book inspection cleaning before an inspection?",
            "a": (
                "Yes. Tenants can arrange inspection cleaning before an upcoming "
                "rental inspection when they want additional professional help "
                "preparing the property."
            ),
        },
        {
            "q": "Do you provide inspection cleaning across {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides inspection cleaning "
                "in {location} and surrounding Adelaide suburbs."
            ),
        },
    ],

    # ============================================================
    # EXIT CLEANING
    # ============================================================

    "exit-cleaning": [
        {
            "q": "What is exit cleaning?",
            "a": (
                "Exit cleaning is a detailed cleaning service designed to prepare "
                "a property when occupants are leaving, including agreed areas "
                "such as kitchens, bathrooms, floors and other inspection points."
            ),
        },
        {
            "q": "Is exit cleaning suitable before selling a property?",
            "a": (
                "Yes. Exit cleaning can help improve the presentation of a property "
                "before photography, inspections, open homes or a final handover."
            ),
        },
        {
            "q": "Can exit cleaning be used for rental properties?",
            "a": (
                "Yes. Exit cleaning can be tailored for rental properties where "
                "detailed cleaning is required before the property is handed back "
                "or prepared for its next occupants."
            ),
        },
        {
            "q": "Can carpet and floor cleaning be included?",
            "a": (
                "Yes. Carpet and floor cleaning can be included depending on the "
                "condition of the property and the agreed exit cleaning scope."
            ),
        },
        {
            "q": "Do you provide exit cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides exit cleaning in "
                "{location} and surrounding Adelaide areas."
            ),
        },
    ],

    # ============================================================
    # CARPET CLEANING
    # ============================================================

    "carpet-cleaning": [
        {
            "q": "What does professional carpet cleaning involve?",
            "a": (
                "Professional carpet cleaning can include pre-vacuuming, stain "
                "treatment, deep extraction, carpet grooming and drying support "
                "depending on the carpet type and agreed service."
            ),
        },
        {
            "q": "Can professional carpet cleaning remove odours?",
            "a": (
                "Carpet cleaning can help reduce many common odours by removing "
                "embedded dirt and residues. Persistent odours may require further "
                "assessment depending on their source."
            ),
        },
        {
            "q": "Can carpet cleaning treat high-traffic areas?",
            "a": (
                "Yes. High-traffic carpet areas can receive targeted treatment "
                "before deeper cleaning, although results depend on carpet age, "
                "wear and existing staining."
            ),
        },
        {
            "q": "Do you clean carpets in offices and commercial properties?",
            "a": (
                "Yes. Carpet cleaning can be arranged for suitable offices, retail "
                "premises and other commercial properties as well as homes."
            ),
        },
        {
            "q": "Do you provide carpet cleaning in {location}?",
            "a": (
                "Yes. Professional carpet cleaning is available in {location} "
                "and surrounding Adelaide suburbs."
            ),
        },
    ],

    # ============================================================
    # KITCHEN DEEP CLEANING
    # ============================================================

    "kitchen-deep-cleaning": [
        {
            "q": "What is included in kitchen deep cleaning?",
            "a": (
                "Kitchen deep cleaning focuses on detailed areas such as ovens, "
                "cooktops, rangehoods, filters, splashbacks, benches, sinks, "
                "cabinet exteriors, appliance surfaces, floors and other agreed "
                "kitchen areas."
            ),
        },
        {
            "q": "Can kitchen deep cleaning remove heavy grease?",
            "a": (
                "Yes. Kitchen deep cleaning is designed for heavier grease, "
                "baked-on food residue and accumulated grime that may require more "
                "detailed degreasing than a routine kitchen clean."
            ),
        },
        {
            "q": "Do you clean rangehoods and filters?",
            "a": (
                "Yes. Rangehood surfaces and suitable removable filters can be "
                "included in the cleaning scope, subject to their condition and "
                "accessibility."
            ),
        },
        {
            "q": "Is kitchen deep cleaning suitable for restaurants and commercial kitchens?",
            "a": (
                "Yes. Kitchen deep cleaning can be tailored for suitable commercial "
                "kitchens, hospitality venues and other food-preparation areas, "
                "with the scope based on the site's requirements."
            ),
        },
        {
            "q": "Can oven cleaning be included with a kitchen deep clean?",
            "a": (
                "Yes. Oven degreasing and detailed oven cleaning can form part of "
                "a kitchen deep cleaning service where required."
            ),
        },
        {
            "q": "Do you provide kitchen deep cleaning in {location}?",
            "a": (
                "Yes. YD Commercial Cleaning Services provides kitchen deep "
                "cleaning in {location} and surrounding Adelaide areas."
            ),
        },
    ],
}


def get_service_faqs(service_slug):
    """
    Return the FAQ set for a service slug.

    A new list is returned so callers can safely modify the result
    without changing the source configuration.
    """
    return list(SERVICE_FAQS.get(service_slug, []))