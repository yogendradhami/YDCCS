"""Versioned, role-ready learning content for the South Australian induction."""


MODULES = [
    {
        "code": "welcome-company",
        "title": "Welcome to YD Commercial Cleaning",
        "category": "welcome",
        "sort_order": 10,
        "summary": "Your first shift, service standards, site expectations and who to contact.",
        "acknowledgement_text": (
            "I understand how to prepare for my first shift, follow the site "
            "instructions provided to me, and ask my supervisor when a requirement is unclear."
        ),
        "content": {
            "illustration": "welcome",
            "introduction": (
                "Welcome to YD Commercial Cleaning. Commercial cleaning is a "
                "service relationship: customers trust us with their workplace, "
                "their property and access to areas that may be closed to the "
                "public. This induction explains how to start safely, work "
                "professionally and raise questions before a small issue becomes a bigger one."
            ),
            "objectives": [
                "Describe the purpose of the induction and the support available to you.",
                "Prepare for a first shift without guessing about access, duties or equipment.",
                "Recognise the difference between an agreed cleaning task and a new customer request.",
                "Explain how reliable service, respectful conduct and factual reporting build customer trust.",
            ],
            "why": (
                "A reliable start prevents missed shifts, unsafe improvisation and "
                "surprises for the customer. A cleaner should know the work area, "
                "the expected scope and the person to contact before beginning."
            ),
            "sections": [
                {
                    "title": "What commercial cleaning means",
                    "body": (
                        "A commercial site can include offices, shared amenities, "
                        "reception areas, kitchens, corridors and other agreed spaces. "
                        "The work order or site instructions define what is included, "
                        "how often it is done and any access limits. Do not assume "
                        "every room or surface is included simply because it is visible."
                    ),
                },
                {
                    "title": "The YD service standard",
                    "body": (
                        "Be dependable, courteous and careful with property. Follow "
                        "the agreed scope, use the approved work method, leave the "
                        "area orderly, and report a missed task or defect honestly. "
                        "A good result is safe, consistent and verifiable—not just fast."
                    ),
                },
                {
                    "title": "Who supports you",
                    "body": (
                        "Your assigned supervisor or manager is the first point of "
                        "contact for unclear work, access problems, customer requests, "
                        "equipment faults, incidents and roster changes. If you have "
                        "not been given a contact method or the site-specific details, "
                        "ask management to provide them before the shift."
                    ),
                },
                {
                    "title": "Your employment and site induction",
                    "body": (
                        "Complete the onboarding requirements assigned to you, "
                        "including any required training or documents. Before your "
                        "first site shift, management must brief you on the approved "
                        "scope, entry and exit arrangements, security controls, "
                        "amenities, emergency arrangements and any site hazards."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Before travelling to a new site",
                    "steps": [
                        "Check the roster for the date, start time, site and assigned supervisor.",
                        "Confirm the address, access method, uniform and required equipment.",
                        "Ask about any site-specific instructions or training not yet provided.",
                        "Tell the supervisor promptly if you cannot attend or expect to be late.",
                    ],
                },
                {
                    "title": "On arrival and at shift end",
                    "steps": [
                        "Use only the authorised entrance and access credentials provided to you.",
                        "Check in using the approved company process and follow the site induction.",
                        "Complete only the assigned work; raise an unclear or unsafe task before starting it.",
                        "Secure equipment, leave the work area orderly, follow exit instructions and record the shift accurately.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A room is not on the work list",
                    "body": (
                        "A customer asks you to clean a locked records room that is "
                        "not on your scope. Thank them, explain that you will check "
                        "the authorised scope, and contact your supervisor. Do not "
                        "enter or begin extra work without approval."
                    ),
                },
                {
                    "title": "You cannot access the site",
                    "body": (
                        "Do not tailgate another person, force a door or share a "
                        "code. Wait in a safe place and use the access escalation "
                        "contact supplied by management."
                    ),
                },
            ],
            "responsibilities": [
                "Attend the rostered shift ready to work and advise the supervisor about barriers early.",
                "Follow instructions and site induction details; ask when they are missing or unclear.",
                "Protect customer property and information and communicate respectfully.",
                "Record work and raise hazards, incidents, defects or scope changes honestly.",
            ],
            "mistakes": [
                "Entering a restricted room because a customer or colleague left the door open.",
                "Accepting additional work without checking whether it is authorised, safe and scheduled.",
                "Using an access code, key or equipment belonging to another worker.",
                "Hiding a missed task or making an inaccurate shift report.",
            ],
            "when_things_go_wrong": (
                "Pause the affected task, keep people and property safe, and contact "
                "your supervisor using the approved channel. State what happened, "
                "where it happened, what you have already done, and what decision "
                "you need. For an immediate threat to life, call 000."
            ),
            "scenario": {
                "title": "Your first evening at a medical office",
                "prompt": (
                    "You arrive at the rostered time but have not received the "
                    "alarm instructions. The customer contact has left, and another "
                    "tenant offers to let you follow them through a secure door. "
                    "What is the safest next action?"
                ),
                "reflection": (
                    "Identify which access information is missing and which "
                    "management contact you would use before entering."
                ),
            },
            "assessment": [
                {
                    "question": "The roster lists a site, but you have not been given its access instructions. What should you do?",
                    "choices": [
                        "Follow another tenant through the secure door.",
                        "Ask the supervisor for the authorised access method before entering.",
                        "Try common access codes until one works.",
                        "Ask the customer to leave a key outside.",
                    ],
                    "correct": 1,
                    "explanation": "Only use access arrangements authorised by management. Do not tailgate, guess codes or arrange unsecured keys.",
                },
                {
                    "question": "A customer requests a task that is not listed in your work scope. What is the best response?",
                    "choices": [
                        "Do it immediately so the customer is satisfied.",
                        "Refuse rudely because it is not your job.",
                        "Acknowledge the request and check approval with your supervisor.",
                        "Ask another cleaner to do it without telling anyone.",
                    ],
                    "correct": 2,
                    "explanation": "New work can affect safety, time and the agreed service. Escalate it rather than promise or perform unauthorised work.",
                },
                {
                    "question": "Which information should be confirmed before a first shift?",
                    "choices": [
                        "Only the site address.",
                        "Roster, scope, access, supervisor contact and site-specific instructions.",
                        "Only the customer's name.",
                        "Whatever another employee remembers.",
                    ],
                    "correct": 1,
                    "explanation": "A safe start requires the schedule, authorised scope, access process and a clear support contact.",
                },
                {
                    "question": "You discover that a scheduled task was missed. What should you do?",
                    "choices": [
                        "Record it as complete to avoid a complaint.",
                        "Leave without mentioning it.",
                        "Report the facts to your supervisor and follow their direction.",
                        "Ask the customer to complete it.",
                    ],
                    "correct": 2,
                    "explanation": "Accurate reporting allows the supervisor to arrange a remedy and maintain an honest service record.",
                },
                {
                    "question": "A tenant offers to share an alarm code with you. What should you do?",
                    "choices": [
                        "Accept it and keep it for future shifts.",
                        "Use it once and delete the message later.",
                        "Decline and request the approved access process from your supervisor.",
                        "Post it in the team chat for convenience.",
                    ],
                    "correct": 2,
                    "explanation": "Access credentials must only be issued and handled through authorised company arrangements.",
                },
                {
                    "question": "You are unsure who your supervisor is. What is the appropriate next step?",
                    "choices": [
                        "Continue and hope the customer knows.",
                        "Ask management to confirm the contact before you need assistance.",
                        "Use a public social media page.",
                        "Ask a customer to decide who manages your work.",
                    ],
                    "correct": 1,
                    "explanation": "Employees need an identified contact for safe work, access issues and changes to the service.",
                },
            ],
            "references": [
                {"label": "YD-approved work scope and site induction", "url": ""},
                {"label": "YD roster and employee portal instructions", "url": ""},
            ],
            "management_configuration": [
                "Provide the current roster/app instructions and a named supervisor contact method.",
                "Complete a site-specific briefing for entry, exit, access, restricted areas and emergency arrangements.",
            ],
            "verification_tasks": [],
        },
    },
    {
        "code": "whs-safety",
        "title": "WHS & Workplace Safety",
        "category": "whs",
        "sort_order": 20,
        "summary": "Identify cleaning hazards, assess risk and apply effective controls at work.",
        "acknowledgement_text": (
            "I understand how to identify cleaning hazards, avoid creating risks "
            "for others, and report a hazard or unsafe condition promptly."
        ),
        "content": {
            "illustration": "whs",
            "introduction": (
                "Work health and safety (WHS) is part of every cleaning task. In "
                "South Australia, the Work Health and Safety Act 2012 and Work "
                "Health and Safety Regulations 2012 set the legal framework. "
                "Workers must take reasonable care, follow reasonable safety "
                "instructions and cooperate with the safe-work arrangements in place."
            ),
            "objectives": [
                "Spot hazards common to commercial cleaning before work exposes people to them.",
                "Use a simple risk process to choose a control, then check whether it works.",
                "Prevent slips, trips and falls while cleaning occupied workplaces.",
                "Recognise chemical, electrical and equipment hazards that require a task to stop.",
                "Explain how to report a hazard without putting yourself or others at further risk.",
            ],
            "why": (
                "Cleaners work around water, chemicals, electrical equipment, "
                "people moving through shared spaces and changing site conditions. "
                "A hazard left in place can injure a cleaner, customer or visitor."
            ),
            "sections": [
                {
                    "title": "Hazard, risk and control",
                    "body": (
                        "A hazard is something with the potential to cause harm, "
                        "such as a wet entrance or damaged lead. Risk is the chance "
                        "and possible consequence of that harm. First remove or "
                        "isolate the hazard where this is safe and authorised. If "
                        "it cannot be eliminated, use effective controls in the "
                        "order established by the site risk assessment and procedure. "
                        "PPE is not a substitute for fixing an unsafe work area."
                    ),
                },
                {
                    "title": "Slips, trips and falls",
                    "body": (
                        "Water, detergent residue, loose mats, trailing leads, "
                        "poor lighting and clutter can create a fall risk. Use the "
                        "approved wet-floor signs before wet work begins; position "
                        "them so approaching people can see them before reaching "
                        "the hazard. Keep a safe route open, manage cables and "
                        "remove signs only when the floor is dry and safe."
                    ),
                },
                {
                    "title": "Chemicals, electricity and equipment",
                    "body": (
                        "Use only identified, approved products and follow their "
                        "label, Safety Data Sheet (SDS), dilution and site instructions. "
                        "Never mix products or transfer them into an unlabelled "
                        "container. Keep liquids away from electrical equipment. "
                        "Do not use a damaged plug, cable, machine or guard; isolate "
                        "it if safe and report it."
                    ),
                },
                {
                    "title": "Consultation and worker duties",
                    "body": (
                        "Tell your supervisor about hazards, near misses and "
                        "controls that are not working. Follow reasonable WHS "
                        "instructions and use the controls provided. If the task "
                        "cannot be done safely with the training or equipment "
                        "available, do not improvise—pause and seek direction."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Assess a hazard before starting or changing a task",
                    "steps": [
                        "Stop at a safe distance and identify who could be harmed and how.",
                        "If there is immediate danger, warn people and isolate the area only if this can be done safely.",
                        "Remove the hazard where authorised; otherwise apply the site-approved control and keep people clear.",
                        "Tell the supervisor promptly and follow the incident or hazard reporting process.",
                        "Check that the control remains effective; do not resume if the risk is still uncontrolled.",
                    ],
                },
                {
                    "title": "Wet-clean an occupied corridor",
                    "steps": [
                        "Check foot traffic and choose an approved section-by-section method.",
                        "Place visible warning signs before introducing water or solution.",
                        "Keep a dry, accessible route where possible and keep leads out of walkways.",
                        "Use the correct product and method for the floor; remove excess solution as instructed.",
                        "Keep signs in place until the floor is dry, then inspect for residue and trip hazards.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A visitor steps towards a wet lobby",
                    "body": (
                        "Pause the wet work, clearly warn the visitor, direct them "
                        "to a safe dry route and make sure the sign is visible. If "
                        "the floor was unexpectedly wet, report the cause and any "
                        "control failure to the supervisor."
                    ),
                },
                {
                    "title": "A vacuum lead has exposed wiring",
                    "body": (
                        "Stop using the vacuum. Do not tape or repair the cable. "
                        "Disconnect it only if safe, label or isolate it under the "
                        "site process, and report it so it cannot be used by another worker."
                    ),
                },
            ],
            "responsibilities": [
                "Take reasonable care for your own health and safety and avoid adversely affecting others.",
                "Use the supplied controls and equipment as trained; do not bypass guards or safety devices.",
                "Report hazards, control failures, near misses and injuries promptly through the approved channel.",
                "Ask for task-specific instruction when the site conditions, product or equipment differ from training.",
            ],
            "mistakes": [
                "Starting wet work before warning people or managing the pedestrian route.",
                "Assuming a hazard is safe because it was present on a previous shift.",
                "Continuing with damaged electrical equipment or making an unapproved repair.",
                "Using a stronger chemical or mixing products to save time.",
                "Treating PPE as a reason to ignore a hazard that could be removed or isolated.",
            ],
            "when_things_go_wrong": (
                "Stop the affected task, warn people, and keep clear of the hazard. "
                "If safe, prevent access without creating another hazard. Contact "
                "the supervisor and follow site emergency instructions. Call 000 "
                "for an immediate threat to life or serious injury. Do not restart "
                "until a safe method has been agreed."
            ),
            "scenario": {
                "title": "A wet floor and an unexpected delivery",
                "prompt": (
                    "You are mopping a narrow hallway. A delivery worker turns "
                    "the corner carrying boxes, and the warning sign is behind "
                    "your trolley. What do you do first, and how should the "
                    "remaining work be controlled?"
                ),
                "reflection": (
                    "Describe how you would stop exposure, warn the person, make "
                    "a visible safe route and tell the supervisor if the planned "
                    "method cannot control the traffic."
                ),
            },
            "assessment": [
                {
                    "question": "A hazard is best described as:",
                    "choices": [
                        "The record made after a shift.",
                        "Something with the potential to cause harm.",
                        "Only an event that caused an injury.",
                        "A task that takes longer than expected.",
                    ],
                    "correct": 1,
                    "explanation": "A hazard can cause harm even when nobody has yet been injured.",
                },
                {
                    "question": "A warning sign is needed for wet-floor work. When should it be placed?",
                    "choices": [
                        "After the floor has been mopped.",
                        "Before wet work begins, where people can see it before the hazard.",
                        "Only if a customer complains.",
                        "At the end of the hallway behind the trolley.",
                    ],
                    "correct": 1,
                    "explanation": "A control must warn people before they reach the wet area and be positioned where it is visible.",
                },
                {
                    "question": "You find a vacuum cable with exposed wiring. What is the safest response?",
                    "choices": [
                        "Finish the room quickly while avoiding the damaged spot.",
                        "Wrap it in tape and continue.",
                        "Stop using and isolate/report it under the site process.",
                        "Ask a customer to plug it in.",
                    ],
                    "correct": 2,
                    "explanation": "Damaged electrical equipment must not remain in service. Do not attempt an unauthorised repair.",
                },
                {
                    "question": "A product label is missing and you cannot identify a bottle. What should you do?",
                    "choices": [
                        "Smell it to identify the product.",
                        "Use a small amount with extra water.",
                        "Do not use it; isolate it if safe and ask the supervisor to identify and manage it.",
                        "Pour it into a sink.",
                    ],
                    "correct": 2,
                    "explanation": "Unknown chemicals must not be used, mixed or disposed of by guesswork.",
                },
                {
                    "question": "A wet corridor is busy with visitors. The planned method cannot keep them clear. What should you do?",
                    "choices": [
                        "Work faster and leave the sign behind you.",
                        "Pause and ask the supervisor for a safe way to control the traffic or reschedule the task.",
                        "Remove all signs so visitors can see the floor.",
                        "Ask visitors to walk through quickly.",
                    ],
                    "correct": 1,
                    "explanation": "The task must not continue when the available controls do not adequately manage the risk.",
                },
                {
                    "question": "Who is responsible for taking reasonable care and following reasonable WHS instructions?",
                    "choices": [
                        "Only the site manager.",
                        "Only the customer.",
                        "Workers, as part of their duties under WHS law.",
                        "No one unless an injury occurs.",
                    ],
                    "correct": 2,
                    "explanation": "Workers have duties under the WHS Act, including reasonable care and compliance with reasonable instructions.",
                },
            ],
            "references": [
                {"label": "Work Health and Safety Act 2012 (SA)", "url": "https://www.legislation.sa.gov.au/lz?path=%2FC%2FA%2FWork%20Health%20and%20Safety%20Act%202012"},
                {"label": "Work Health and Safety Regulations 2012 (SA)", "url": "https://www.legislation.sa.gov.au/lz?path=%2FC%2FR%2FWork%20Health%20and%20Safety%20Regulations%202012"},
                {"label": "SafeWork SA", "url": "https://www.safework.sa.gov.au/"},
            ],
            "management_configuration": [
                "Set the site-specific hazard reporting channel and escalation contact.",
                "Provide the approved wet-floor controls, chemical register/SDS access and equipment defect process for each site.",
            ],
            "verification_tasks": [
                "Identify a site hazard and explain the risk and control.",
                "Set up a wet-floor work area and visible pedestrian warning.",
            ],
        },
    },
    {
        "code": "ppe",
        "title": "Personal Protective Equipment",
        "category": "whs",
        "sort_order": 30,
        "summary": "Select, check, wear and care for task-appropriate protective equipment.",
        "acknowledgement_text": (
            "I understand that PPE must suit the task and product instructions, "
            "be checked before use, and be replaced or reported when damaged or unsuitable."
        ),
        "content": {
            "illustration": "ppe",
            "introduction": (
                "Personal protective equipment (PPE) helps reduce exposure to "
                "specific hazards. It is selected for the task, chemical and site "
                "risk controls—not chosen by appearance or habit. PPE does not "
                "make an unauthorised task safe."
            ),
            "objectives": [
                "Match gloves, eye protection, footwear and clothing to the task and product instructions.",
                "Check PPE fit, condition and compatibility before entering the work area.",
                "Put on and remove PPE in a way that avoids transferring contamination.",
                "Know when a respirator or other specialised PPE needs formal selection and fit arrangements.",
                "Store, clean, replace and report PPE correctly.",
            ],
            "why": (
                "The wrong glove can allow a chemical through or fail during "
                "scrubbing. Poor eye protection can leave splashes unprotected. "
                "Damaged or badly fitting PPE may create a false sense of safety."
            ),
            "sections": [
                {
                    "title": "Choose PPE from the hazard information",
                    "body": (
                        "Read the product label and SDS and follow the site risk "
                        "assessment. Glove material and thickness must be compatible "
                        "with the chemical and contact time; 'gloves' are not all "
                        "the same. Use splash goggles or face protection where the "
                        "task assessment calls for it. Never rely on a mask unless "
                        "the task assessment specifies the correct respiratory "
                        "protection and required fit and training arrangements."
                    ),
                },
                {
                    "title": "Footwear and protective clothing",
                    "body": (
                        "Wear the company/site-required footwear: stable, secure, "
                        "in good repair and suitable for wet or slippery floors. "
                        "Clothing should cover the areas identified in the task "
                        "risk controls without loose cuffs, drawstrings or jewellery "
                        "that can catch in equipment. Uniform is not a substitute "
                        "for protective clothing."
                    ),
                },
                {
                    "title": "Fit, inspect and remove",
                    "body": (
                        "Check gloves for holes, degraded areas or a poor fit; "
                        "check eye protection for cracks, loose sides and clear "
                        "vision; check footwear for worn soles. Follow the site "
                        "method for donning and removal. Remove contaminated "
                        "disposables without touching the contaminated surface, "
                        "wash hands as directed and do not reuse single-use PPE."
                    ),
                },
                {
                    "title": "Cleaning, storage and replacement",
                    "body": (
                        "Clean reusable PPE only as its manufacturer and site "
                        "instructions allow. Store it dry, clean and separate from "
                        "chemicals and contaminated tools. Replace damaged, "
                        "contaminated or expired items and tell the supervisor if "
                        "the required PPE is unavailable."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Select and use PPE for a chemical task",
                    "steps": [
                        "Identify the exact product and task; check the label, SDS and site risk controls.",
                        "Select the specified glove and eye/face protection; confirm any respiratory requirement with the supervisor.",
                        "Inspect each item for damage, contamination, correct size and secure fit.",
                        "Put on PPE before handling the product and keep it on for the exposure period identified by the instructions.",
                        "Remove PPE without spreading contamination, clean/store reusable items as directed and wash hands.",
                    ],
                },
                {
                    "title": "Respond to a PPE failure",
                    "steps": [
                        "Stop the task and move away from the exposure if it is safe.",
                        "Use the product/SDS first-aid instructions for contact or exposure; call 000 for a serious reaction.",
                        "Do not continue with a substitute item unless it is confirmed suitable.",
                        "Report the failed or unavailable PPE and arrange a safe replacement before restarting.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Gloves tear during toilet cleaning",
                    "body": (
                        "Stop, avoid touching clean surfaces, remove the torn "
                        "glove safely, wash your hands and replace it with the "
                        "approved compatible glove. If skin was exposed, follow "
                        "the chemical or biological exposure instructions and report it."
                    ),
                },
                {
                    "title": "A strong spray irritates your eyes",
                    "body": (
                        "Move to fresh air or a safe area and follow the product "
                        "SDS first-aid advice. Do not choose an ordinary dust mask "
                        "as a substitute for assessed respiratory protection."
                    ),
                },
            ],
            "responsibilities": [
                "Wear PPE identified by the task risk assessment, product information and site instruction.",
                "Inspect PPE before use and report missing, damaged, contaminated or unsuitable items.",
                "Keep PPE clean and stored as instructed; do not share personal-fit items.",
                "Ask for instruction if the product, task or required PPE changes.",
            ],
            "mistakes": [
                "Assuming any glove protects against every cleaning chemical.",
                "Wearing cracked goggles or shoes with worn, smooth soles.",
                "Reusing disposable gloves or touching clean items with contaminated gloves.",
                "Using a respirator or face covering without the required selection, fit and training.",
                "Continuing a task because PPE is available even though the task itself is unsafe.",
            ],
            "when_things_go_wrong": (
                "Stop exposure, move to a safe place and follow the label/SDS "
                "first-aid steps. Ask another worker to call for help if needed. "
                "Call 000 for serious breathing difficulty, collapse or another "
                "life-threatening emergency. Report the exposure and equipment "
                "failure to the supervisor; do not resume until the control is restored."
            ),
            "scenario": {
                "title": "The only gloves at the site do not fit",
                "prompt": (
                    "The scheduled task uses a product whose instructions specify "
                    "chemical-resistant gloves. The site cupboard contains only "
                    "oversized disposable food-preparation gloves. How do you proceed?"
                ),
                "reflection": (
                    "Explain why the available gloves may not be suitable and how "
                    "you would obtain a safe alternative without delaying silently."
                ),
            },
            "assessment": [
                {
                    "question": "How should you choose gloves for a cleaning chemical?",
                    "choices": [
                        "Choose any disposable glove.",
                        "Use the product label/SDS and site risk control to check compatibility.",
                        "Use the thickest glove regardless of the product.",
                        "Ask another cleaner to guess.",
                    ],
                    "correct": 1,
                    "explanation": "Glove materials differ. Selection must follow the product and task hazard information.",
                },
                {
                    "question": "You find a crack in your eye protection before mixing an approved solution. What should you do?",
                    "choices": [
                        "Use it because the task is short.",
                        "Turn the cracked side away from the splash.",
                        "Do not start until suitable undamaged protection is available.",
                        "Wear sunglasses instead.",
                    ],
                    "correct": 2,
                    "explanation": "Damaged PPE may not protect. Replace it before beginning the exposure task.",
                },
                {
                    "question": "Which statement about a dust mask and chemical vapour is correct?",
                    "choices": [
                        "Any mask protects from any vapour.",
                        "A mask should only be used when the task assessment identifies suitable respiratory protection and required fit/training.",
                        "A mask replaces ventilation and product instructions.",
                        "Two disposable masks are equivalent to a respirator.",
                    ],
                    "correct": 1,
                    "explanation": "Respiratory PPE must be specified for the hazard and supported by the required selection, fit and training arrangements.",
                },
                {
                    "question": "A disposable glove is contaminated after a task. What is the correct approach?",
                    "choices": [
                        "Wash it and wear it again.",
                        "Remove it without spreading contamination and dispose of it as instructed.",
                        "Put a clean glove over it.",
                        "Wipe the outside on your uniform.",
                    ],
                    "correct": 1,
                    "explanation": "Single-use gloves are not cleaned for reuse; careful removal prevents transferring contamination.",
                },
                {
                    "question": "The required glove is unavailable and the task is due. What should you do?",
                    "choices": [
                        "Use a different glove without checking.",
                        "Proceed carefully with bare hands.",
                        "Pause and ask the supervisor to provide an approved safe control or reschedule.",
                        "Ask the customer to supply any glove.",
                    ],
                    "correct": 2,
                    "explanation": "Do not improvise a control that may not protect against the identified exposure.",
                },
                {
                    "question": "Why is suitable footwear important during wet-floor cleaning?",
                    "choices": [
                        "It replaces warning signs.",
                        "It reduces some slip risk but does not remove the need to control the wet area.",
                        "It permits faster running across wet floors.",
                        "It prevents every type of foot injury.",
                    ],
                    "correct": 1,
                    "explanation": "Footwear is one control only; the wet work area and pedestrian exposure must also be managed.",
                },
            ],
            "references": [
                {"label": "Safe Work Australia: Personal protective equipment", "url": "https://www.safeworkaustralia.gov.au/safety-topic/managing-health-and-safety/personal-protective-equipment"},
                {"label": "Safe Work Australia: Chemicals", "url": "https://www.safeworkaustralia.gov.au/safety-topic/hazards/chemicals"},
            ],
            "management_configuration": [
                "Maintain task-specific PPE requirements and compatible replacement stock for approved products.",
                "Confirm respiratory-protection assessment, fit-testing and training arrangements before assigning a respirator task.",
            ],
            "verification_tasks": [
                "Select task-specific PPE using the product label/SDS and site risk controls.",
                "Demonstrate an uncontaminated method of removing and storing/discarding PPE.",
            ],
        },
    },
    {
        "code": "manual-handling",
        "title": "Manual Handling & Ergonomics",
        "category": "whs",
        "sort_order": 50,
        "summary": "Move cleaning tools and materials while reducing force, repetition and awkward posture.",
        "acknowledgement_text": (
            "I understand that I must use available handling aids, avoid unsafe "
            "lifts and request assistance or a different method when a task exceeds my capability."
        ),
        "content": {
            "illustration": "manual",
            "introduction": (
                "Cleaning work can involve pushing, pulling, carrying, reaching, "
                "bending and repeating the same movement. A hazardous manual task "
                "can injure muscles, joints or the back even when an item does not "
                "look heavy. Plan the task and reduce force and awkward movement "
                "rather than relying on a single lifting technique."
            ),
            "objectives": [
                "Recognise force, repetition, sustained posture and vibration as manual-task risk factors.",
                "Set up and move a trolley, vacuum and floor machine using their safe operating method.",
                "Plan a carry route and use mechanical aids or a team lift where suitable.",
                "Recognise early discomfort and report it before it worsens.",
                "Decline or pause a lift that is too heavy, unstable or outside your training.",
            ],
            "why": (
                "A trolley that is overloaded or difficult to steer, repeated "
                "high reaching, and twisting while carrying can build up strain. "
                "Changing the task, route, load or equipment is usually more "
                "reliable than telling a worker simply to 'lift correctly'."
            ),
            "sections": [
                {
                    "title": "What makes a task hazardous",
                    "body": (
                        "Consider the weight and shape of the load, grip, distance "
                        "carried, height, twisting, repetition, pace, floor slope, "
                        "available space and your physical condition. An awkward "
                        "vacuum, full bucket or jammed trolley can require high "
                        "force even if it is not especially heavy."
                    ),
                },
                {
                    "title": "Trolleys, vacuums and floor machines",
                    "body": (
                        "Keep trolley loads stable and within its rated capacity; "
                        "do not block your view. Push rather than pull where the "
                        "layout and equipment allow, keep the trolley close and "
                        "use a clear route. Adjust a vacuum handle if it is designed "
                        "to adjust, keep the hose and lead managed, and alternate "
                        "hands or tasks where practical. Floor machines require "
                        "equipment-specific instruction; do not use one until "
                        "trained and authorised."
                    ),
                },
                {
                    "title": "Repetition, reach and fatigue",
                    "body": (
                        "Use a tool with a suitable handle and work within a "
                        "comfortable reach. Move your feet to face the work instead "
                        "of twisting under load. Break up repetitive tasks or "
                        "alternate tasks where the schedule permits. Fatigue, "
                        "pain, numbness or reduced grip are early warning signs; "
                        "report them and do not push through worsening symptoms."
                    ),
                },
                {
                    "title": "Moving furniture and heavy items",
                    "body": (
                        "Do not move customer furniture, heavy bins or equipment "
                        "unless the task is authorised and a safe method is "
                        "provided. Check the route and destination first. Use a "
                        "suitable trolley or team assistance if directed; agree "
                        "who leads the move. Never lift with a colleague who has "
                        "not agreed or where the load blocks vision."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Move a cleaning trolley between floors",
                    "steps": [
                        "Remove unnecessary items and keep the load stable and below the rated capacity.",
                        "Check wheels, handle, floor transitions, doors and the route for people or obstacles.",
                        "Keep the trolley close; push at a controlled pace where the layout permits and maintain a clear view.",
                        "Do not force a stuck or overloaded trolley; unload or request assistance.",
                        "Report damaged wheels, an unsafe ramp or recurring high-force movement.",
                    ],
                },
                {
                    "title": "Respond to discomfort during repetitive work",
                    "steps": [
                        "Pause the task safely and note what movement or equipment is causing discomfort.",
                        "Tell the supervisor promptly; do not diagnose the injury or wait for severe pain.",
                        "Follow the injury reporting and first-aid process if injured.",
                        "Resume only with an agreed adjustment, aid, task change or other safe direction.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A trolley will not turn in a narrow corridor",
                    "body": (
                        "Do not jerk it around while twisting your back. Stop, "
                        "remove or rearrange the load if safe, check the route and "
                        "ask for assistance or a different trolley if it remains "
                        "difficult to control."
                    ),
                },
                {
                    "title": "A bin is heavier than expected",
                    "body": (
                        "Do not lift it to find out whether you can manage. Check "
                        "for a trolley or approved disposal method and ask the "
                        "supervisor for help if the load is heavy, unstable or "
                        "contains unknown material."
                    ),
                },
            ],
            "responsibilities": [
                "Use handling aids and equipment as trained and keep loads within equipment limits.",
                "Report early discomfort, high-force tasks, damaged wheels or unsuitable work heights.",
                "Ask for help or a different method instead of attempting an unsafe lift.",
                "Do not move customer furniture or operate a floor machine without authorisation and training.",
            ],
            "mistakes": [
                "Overloading a trolley or carrying supplies that block your view.",
                "Pulling a trolley around a corner while twisting under load.",
                "Repeatedly reaching above shoulder height instead of repositioning the body or tool.",
                "Trying to move furniture without checking permission, route and assistance.",
                "Ignoring pain, tingling or fatigue to finish a target faster.",
            ],
            "when_things_go_wrong": (
                "Stop the movement, put the load down only if safe, and keep "
                "others clear. If injured, seek first aid or urgent help as needed "
                "and report the injury promptly. Tell the supervisor what task, "
                "load, equipment and conditions contributed so the work method "
                "can be reviewed."
            ),
            "scenario": {
                "title": "Restocking an upper shelf",
                "prompt": (
                    "A heavy carton of paper products is on the floor and the "
                    "storage shelf is above shoulder height. You are alone, and "
                    "the carton blocks your view when lifted. How should the task "
                    "be changed before you move it?"
                ),
                "reflection": (
                    "Consider load size, storage height, trolley use, assistance "
                    "and whether the task is actually part of your authorised duties."
                ),
            },
            "assessment": [
                {
                    "question": "Which combination can make a cleaning task hazardous?",
                    "choices": [
                        "Only a very heavy object.",
                        "Force, repetition, awkward posture, vibration or a difficult environment.",
                        "Only tasks performed outdoors.",
                        "Only a task that already caused injury.",
                    ],
                    "correct": 1,
                    "explanation": "Manual-task risk can arise from several factors and does not require a heavy load or previous injury.",
                },
                {
                    "question": "A loaded trolley is hard to turn and blocks your view. What should you do?",
                    "choices": [
                        "Pull harder and keep moving.",
                        "Stop, make the load stable and visible, check the route, and seek help if it remains difficult.",
                        "Ask a customer to steer it.",
                        "Run to reduce the time under load.",
                    ],
                    "correct": 1,
                    "explanation": "A stable load, clear view and controlled route reduce force and collision risk.",
                },
                {
                    "question": "Your shoulder becomes sore after repeated high dusting. What is the best response?",
                    "choices": [
                        "Ignore it until the shift ends.",
                        "Continue faster to finish sooner.",
                        "Pause safely, report the discomfort and ask for an adjusted method or task.",
                        "Take medication without telling anyone.",
                    ],
                    "correct": 2,
                    "explanation": "Early reporting lets the task be reviewed before discomfort develops into a more serious injury.",
                },
                {
                    "question": "A floor machine is available but you have not been trained to use it. What should you do?",
                    "choices": [
                        "Try it on the lowest setting.",
                        "Watch a video during the shift and start.",
                        "Do not operate it; request training or an authorised operator.",
                        "Ask a customer to show you.",
                    ],
                    "correct": 2,
                    "explanation": "Powered equipment requires appropriate instruction and authorisation.",
                },
                {
                    "question": "A carton is heavy, above shoulder height and blocks your view. What is the safest plan?",
                    "choices": [
                        "Lift it overhead in one movement.",
                        "Ask for an approved handling aid or assistance and change the storage method.",
                        "Carry it on one shoulder.",
                        "Stand on an unsecured chair.",
                    ],
                    "correct": 1,
                    "explanation": "Change the task and use suitable aids or assistance rather than lifting a heavy, obstructive load overhead.",
                },
                {
                    "question": "A customer asks you to move a heavy filing cabinet. What should you do?",
                    "choices": [
                        "Move it immediately to be helpful.",
                        "Drag it across the floor.",
                        "Check that the task is authorised and ask the supervisor to arrange a safe method.",
                        "Ask a colleague to lift the other end without planning.",
                    ],
                    "correct": 2,
                    "explanation": "Moving heavy customer property requires authorisation and a planned safe method.",
                },
            ],
            "references": [
                {"label": "Safe Work Australia: Hazardous manual tasks", "url": "https://www.safeworkaustralia.gov.au/safety-topic/hazards/manual-tasks"},
                {"label": "Work Health and Safety Regulations 2012 (SA)", "url": "https://www.legislation.sa.gov.au/lz?path=%2FC%2FR%2FWork%20Health%20and%20Safety%20Regulations%202012"},
            ],
            "management_configuration": [
                "Document the safe method, handling aids and rated limits for each trolley and floor machine.",
                "Review repetitive or high-force site tasks and arrange practical training before assigning them.",
            ],
            "verification_tasks": [
                "Set up and move the site's cleaning trolley on its normal route.",
                "Demonstrate the approved vacuum or floor-machine posture and controls for the assigned equipment.",
            ],
        },
    },
    {
        "code": "incident-reporting",
        "title": "Incident, Injury & Hazard Reporting",
        "category": "whs",
        "sort_order": 70,
        "summary": "Respond, protect people, report facts and preserve information after an event.",
        "acknowledgement_text": (
            "I understand I must seek help, make the area safe where possible, "
            "and report hazards, injuries, near misses and damage promptly and factually."
        ),
        "content": {
            "illustration": "incident",
            "introduction": (
                "An incident is an unplanned event; an injury is harm to a person; "
                "a hazard could cause harm; and a near miss is an event that could "
                "have caused harm but did not. Reporting all of them helps prevent "
                "a repeat. This module separates your duty to report internally "
                "from the company's legal duty to notify SafeWork SA when an event "
                "is notifiable."
            ),
            "objectives": [
                "Distinguish a hazard, near miss, incident, injury and property-damage event.",
                "Prioritise emergency help and protect people before paperwork.",
                "Give a prompt, factual report with time, location, people and immediate actions.",
                "Handle chemical exposure, spills and damaged property without making the event worse.",
                "Explain that the PCBU manages any legal notification to SafeWork SA; workers report internally immediately.",
            ],
            "why": (
                "A small spill, failed warning sign or near miss can reveal a "
                "control that needs repair. Prompt, factual reporting helps the "
                "company respond, support affected people and assess its legal obligations."
            ),
            "sections": [
                {
                    "title": "First actions: people, danger, help",
                    "body": (
                        "Do not delay urgent care to complete a form. Call 000 "
                        "for a life-threatening emergency. Do not move an injured "
                        "person unless there is immediate danger or it is required "
                        "to provide care. Use only first-aid skills you are trained "
                        "to provide. Keep others clear, isolate the area if safe "
                        "and follow the site emergency plan."
                    ),
                },
                {
                    "title": "Chemical exposure or spill",
                    "body": (
                        "For exposure, use the product label/SDS first-aid "
                        "instructions and get help. Avoid contact with an unknown "
                        "spill, fumes or a reaction. Do not mix, neutralise, wash "
                        "into a drain or clean up beyond your training and the "
                        "site spill procedure. Keep people away and tell the "
                        "supervisor what product is involved if it is safely known."
                    ),
                },
                {
                    "title": "Factual reporting and evidence",
                    "body": (
                        "Record what you observed, heard and did. Include the "
                        "date/time, site and exact area, people involved, hazard "
                        "or equipment, injury or damage, witnesses, immediate "
                        "controls and who was notified. Separate facts from "
                        "assumptions. Do not blame people, alter evidence, post "
                        "photos publicly or make promises about liability."
                    ),
                },
                {
                    "title": "SafeWork SA notification is the PCBU's responsibility",
                    "body": (
                        "Under the South Australian WHS Act, a PCBU must notify "
                        "the regulator as soon as it becomes aware of a notifiable "
                        "incident, and preserve the incident site so far as "
                        "required by law, subject to exceptions such as helping "
                        "an injured person or making the site safe. The company "
                        "must promptly escalate a potentially notifiable event "
                        "to its designated responsible manager. Employees must "
                        "report internally immediately; do not assume the employee "
                        "alone is responsible for the company's regulator notification."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Report an injury or near miss",
                    "steps": [
                        "Call 000 or arrange first aid when required; protect people from further exposure.",
                        "Make the area safe only if you can do so without creating another risk.",
                        "Notify the supervisor as soon as possible using the approved urgent reporting channel.",
                        "Provide a factual account: when, where, what happened, who was affected, witnesses and controls used.",
                        "Complete the company incident record and cooperate with follow-up; do not alter the scene unless necessary for safety or directed.",
                    ],
                },
                {
                    "title": "Report property or equipment damage",
                    "steps": [
                        "Stop the activity and prevent additional damage or use of unsafe equipment.",
                        "Tell the supervisor and site contact promptly; do not conceal damage or admit liability on the company's behalf.",
                        "Record the item, location, condition, time and people present factually.",
                        "Preserve relevant equipment or evidence and follow the supervisor's direction.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A visitor slips but says they are fine",
                    "body": (
                        "Offer assistance, secure the area and notify the "
                        "supervisor. Record the event and the visitor's own "
                        "words as accurately as possible. Do not decide that "
                        "no report is needed because no injury is visible."
                    ),
                },
                {
                    "title": "A bottle leaks and causes coughing",
                    "body": (
                        "Move people away without entering fumes, get fresh air "
                        "and emergency assistance if symptoms are serious. Use "
                        "the label/SDS only if safely accessible; isolate the "
                        "area and alert the supervisor. Do not attempt an "
                        "untrained clean-up."
                    ),
                },
            ],
            "responsibilities": [
                "Raise an alarm and seek emergency assistance before completing records.",
                "Report every injury, near miss, hazard, exposure and property/equipment damage promptly.",
                "Provide accurate observations and cooperate with the company's investigation.",
                "Keep information confidential and do not make public statements, take unauthorised images or assign blame.",
            ],
            "mistakes": [
                "Assuming a near miss or minor injury does not need reporting.",
                "Cleaning an unknown chemical spill or mixing products to neutralise it.",
                "Waiting until the end of the week to report an injury or unsafe control.",
                "Changing a scene or deleting messages/photos that may be relevant.",
                "Telling staff that they personally must notify SafeWork SA instead of promptly escalating to the company's responsible manager.",
            ],
            "when_things_go_wrong": (
                "Call 000 where urgent help is required, follow the site emergency "
                "plan and contact the supervisor through the urgent channel. "
                "Keep people away from the affected area. The supervisor/manager "
                "must escalate a potentially notifiable event immediately to "
                "the company person responsible for regulator liaison; workers "
                "should not delay internal reporting while deciding legal categories."
            ),
            "scenario": {
                "title": "A near miss beside an auto-scrubber",
                "prompt": (
                    "A staff member steps over the machine lead and avoids a "
                    "fall. The lead was stretched across a walkway and the "
                    "warning sign had been moved. No one is hurt. What should "
                    "you do and what facts should be recorded?"
                ),
                "reflection": (
                    "Identify immediate controls, who needs to be told, and "
                    "which facts would help prevent a repeat without blaming anyone."
                ),
            },
            "assessment": [
                {
                    "question": "A near miss has not caused an injury. What should you do?",
                    "choices": [
                        "Ignore it because nobody was hurt.",
                        "Report it promptly so the hazard and controls can be reviewed.",
                        "Wait to see if someone else reports it.",
                        "Post the details publicly.",
                    ],
                    "correct": 1,
                    "explanation": "Near misses can reveal a control failure before someone is injured.",
                },
                {
                    "question": "A person has collapsed and is not responding. What comes first?",
                    "choices": [
                        "Finish the incident form.",
                        "Call 000, get first aid help and follow emergency instructions.",
                        "Move them to a chair immediately in every case.",
                        "Take a photo for the report.",
                    ],
                    "correct": 1,
                    "explanation": "Emergency care and scene safety take priority. Do not move a person unless needed for safety or care.",
                },
                {
                    "question": "A chemical spill has unknown contents and fumes. What should a cleaner do?",
                    "choices": [
                        "Mix it with another product to neutralise it.",
                        "Mop it up quickly with bare hands.",
                        "Keep people away, avoid exposure and alert the supervisor under the spill procedure.",
                        "Wash it down the nearest drain.",
                    ],
                    "correct": 2,
                    "explanation": "Do not enter or clean an unknown spill beyond your training and site procedure.",
                },
                {
                    "question": "Which is the best incident report statement?",
                    "choices": [
                        "The careless visitor caused everything.",
                        "At about 7:10 pm near reception, I saw water beside the entrance; I placed a sign and notified the supervisor.",
                        "The floor was probably wet for hours.",
                        "No one needs to know because there was no injury.",
                    ],
                    "correct": 1,
                    "explanation": "A useful report separates observed facts, time, place and actions from blame or unsupported assumptions.",
                },
                {
                    "question": "Who has the legal responsibility to notify SafeWork SA of a notifiable incident?",
                    "choices": [
                        "Every worker individually, regardless of role.",
                        "The customer in all cases.",
                        "The PCBU; workers must promptly report internally so the company can assess and meet its duties.",
                        "No one unless a lawyer asks.",
                    ],
                    "correct": 2,
                    "explanation": "The WHS Act places regulator notification duties on the PCBU. Employees must promptly escalate incidents internally.",
                },
                {
                    "question": "When may an incident site need to be disturbed?",
                    "choices": [
                        "Whenever cleaning is behind schedule.",
                        "To help an injured person, make the site safe, or as otherwise permitted/directed under the law.",
                        "To make the area look tidy before the customer arrives.",
                        "Whenever a worker wants to move equipment.",
                    ],
                    "correct": 1,
                    "explanation": "A PCBU must preserve the site of a notifiable incident as required by law, subject to specific exceptions and directions.",
                },
            ],
            "references": [
                {"label": "SafeWork SA: Notifiable incidents", "url": "https://www.safework.sa.gov.au/workplaces/incidents-and-injuries/notifiable-incidents"},
                {"label": "Work Health and Safety Act 2012 (SA)", "url": "https://www.legislation.sa.gov.au/lz?path=%2FC%2FA%2FWork%20Health%20and%20Safety%20Act%202012"},
            ],
            "management_configuration": [
                "Name the company role that assesses notifiability and contacts SafeWork SA; publish the urgent escalation channel.",
                "Provide the current incident, injury, hazard, property-damage and chemical-exposure reporting forms/process.",
                "Confirm the site-specific first-aid contacts and spill response arrangements.",
            ],
            "verification_tasks": [],
        },
    },
    {
        "code": "customer-conduct",
        "title": "Customer Service & Professional Conduct",
        "category": "conduct",
        "sort_order": 80,
        "summary": "Work respectfully at customer premises, protect property and handle requests professionally.",
        "acknowledgement_text": (
            "I understand how to communicate professionally, protect customer "
            "property and refer complaints or extra work to my supervisor."
        ),
        "content": {
            "illustration": "customer",
            "introduction": (
                "A cleaner is often one of the few people working in a customer's "
                "premises after hours. Professional conduct means being respectful, "
                "careful, predictable and within the agreed service scope. It also "
                "means knowing when a request belongs with a supervisor."
            ),
            "objectives": [
                "Use courteous, clear communication with customers, visitors and colleagues.",
                "Enter, secure and leave customer premises only under authorised arrangements.",
                "Respond to a complaint by listening, clarifying and escalating without arguing or promising.",
                "Protect property and perform only authorised work.",
                "Recognise conduct that may be disrespectful, discriminatory or unsafe.",
            ],
            "why": (
                "Good service is more than a clean surface. A calm interaction, "
                "respect for boundaries and prompt escalation protects the "
                "customer relationship and prevents unauthorised work."
            ),
            "sections": [
                {
                    "title": "Communication on site",
                    "body": (
                        "Greet people politely, use plain language and keep "
                        "conversations work-related. Do not interrupt private "
                        "meetings or discuss a customer's business with others. "
                        "If language or hearing differences make instructions "
                        "unclear, ask the supervisor to clarify rather than guess."
                    ),
                },
                {
                    "title": "Complaints and service recovery",
                    "body": (
                        "Listen without interrupting. Acknowledge the concern "
                        "without arguing, blaming a colleague or promising a "
                        "refund or future service. Clarify the location and "
                        "specific issue, then contact the supervisor promptly. "
                        "Record the concern factually using the company process."
                    ),
                },
                {
                    "title": "Scope, access and property",
                    "body": (
                        "Work only in areas and on tasks approved for your shift. "
                        "Use the authorised access method, do not borrow customer "
                        "property and do not move personal or business items "
                        "unless your scope requires it and the method is approved. "
                        "Report damage immediately; do not conceal it or attempt "
                        "a repair without authority."
                    ),
                },
                {
                    "title": "Respectful workplace behaviour",
                    "body": (
                        "Treat everyone fairly and respectfully. Do not use "
                        "threatening, sexual, discriminatory or harassing language "
                        "or conduct. Maintain appropriate boundaries, avoid "
                        "unnecessary contact with customer belongings and raise "
                        "unacceptable behaviour through the manager or company "
                        "reporting process."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Respond to a customer complaint",
                    "steps": [
                        "Pause and listen; do not interrupt or become defensive.",
                        "Thank the person for raising the issue and clarify the exact area or service concern.",
                        "Do not admit liability, promise a remedy or blame another person.",
                        "Tell the supervisor promptly and record the facts through the approved channel.",
                        "Follow the authorised direction and confirm only what you have actually done.",
                    ],
                },
                {
                    "title": "Handle an extra-work request",
                    "steps": [
                        "Confirm what the customer is asking and whether there is an immediate safety concern.",
                        "Explain politely that you need supervisor approval before changing the scope.",
                        "Do not use unfamiliar chemicals, equipment or access areas to perform the extra task.",
                        "Pass the request to the supervisor and wait for an authorised plan.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A customer reports dust on a desk",
                    "body": (
                        "Thank them, check the specific desk without moving "
                        "confidential papers, and notify the supervisor. Clean "
                        "only if the surface is within scope and it is safe and "
                        "appropriate to do so."
                    ),
                },
                {
                    "title": "A customer asks you to clean a spill in an unfamiliar lab",
                    "body": (
                        "Do not touch it. Explain that you need to follow the "
                        "site's spill controls and contact your supervisor. "
                        "Unknown substances or specialist environments require "
                        "site-specific training and authorisation."
                    ),
                },
            ],
            "responsibilities": [
                "Communicate calmly, courteously and truthfully.",
                "Stay within the approved work scope and site access permissions.",
                "Protect property and report a complaint, damage or unsafe request promptly.",
                "Maintain respectful behaviour and appropriate professional boundaries.",
            ],
            "mistakes": [
                "Arguing with a customer or promising a service outcome beyond your authority.",
                "Agreeing to extra work without confirming scope, time, equipment and safety.",
                "Moving papers, personal items or equipment without a work reason and authority.",
                "Entering a room or handling a spill without site-specific permission.",
                "Discussing another employee or customer in a public area.",
            ],
            "when_things_go_wrong": (
                "End an interaction that is escalating if you can do so safely, "
                "move to a safe area and contact your supervisor. If someone "
                "is threatened or in immediate danger, call 000. Report the "
                "facts and any witnesses through the approved company process."
            ),
            "scenario": {
                "title": "A complaint becomes a request for extra work",
                "prompt": (
                    "A frustrated office manager says a meeting room was missed "
                    "and asks you to also polish a wooden table using a product "
                    "they found in a cupboard. How can you respond helpfully "
                    "without accepting an unsafe or unauthorised task?"
                ),
                "reflection": (
                    "Practise a short response that acknowledges the concern, "
                    "avoids a promise and explains that you will contact your supervisor."
                ),
            },
            "assessment": [
                {
                    "question": "A customer complains about a missed room. What is the best first response?",
                    "choices": [
                        "Argue that the room was not on your list.",
                        "Listen, acknowledge the concern and clarify the room before escalating.",
                        "Promise a free extra service.",
                        "Blame the previous cleaner.",
                    ],
                    "correct": 1,
                    "explanation": "A calm acknowledgement and clear facts let the supervisor arrange an authorised response.",
                },
                {
                    "question": "A customer asks you to use an unknown product from a cupboard. What should you do?",
                    "choices": [
                        "Use it on a hidden area first.",
                        "Mix it with your normal solution.",
                        "Do not use it; explain you will check with the supervisor.",
                        "Ask the customer to apply it.",
                    ],
                    "correct": 2,
                    "explanation": "An unknown product is not an approved safe method; check its identity and authorisation before use.",
                },
                {
                    "question": "Which response is within a cleaner's authority when a customer requests extra work?",
                    "choices": [
                        "Promise it will be done tonight.",
                        "Politely explain that the supervisor must approve scope changes.",
                        "Say the customer has no right to ask.",
                        "Do the task without recording it.",
                    ],
                    "correct": 1,
                    "explanation": "The supervisor confirms scope, time, equipment and safety before extra work is accepted.",
                },
                {
                    "question": "You accidentally damage a small item while cleaning. What should you do?",
                    "choices": [
                        "Put it back and say nothing.",
                        "Try to repair it with a product from the cupboard.",
                        "Stop, protect the area and promptly report what happened factually.",
                        "Tell the customer a colleague did it.",
                    ],
                    "correct": 2,
                    "explanation": "Prompt factual reporting allows the company to respond and prevents further damage.",
                },
                {
                    "question": "A person enters a restricted room and invites you to clean it. What is the right action?",
                    "choices": [
                        "Enter because the person invited you.",
                        "Check the access and work scope with your supervisor before entering.",
                        "Use the room's equipment.",
                        "Ask for their access code.",
                    ],
                    "correct": 1,
                    "explanation": "An invitation does not replace the authorised site access and task scope.",
                },
                {
                    "question": "A customer uses threatening language during a complaint. What should you do?",
                    "choices": [
                        "Threaten them back.",
                        "Stay in the room and continue arguing.",
                        "Move to safety, contact the supervisor and call 000 if there is immediate danger.",
                        "Post the customer's name online.",
                    ],
                    "correct": 2,
                    "explanation": "Personal safety comes first; escalate threatening conduct through the proper channel.",
                },
            ],
            "references": [
                {"label": "YD-approved work scope and customer service process", "url": ""},
                {"label": "Work Health and Safety Act 2012 (SA)", "url": "https://www.legislation.sa.gov.au/lz?path=%2FC%2FA%2FWork%20Health%20and%20Safety%20Act%202012"},
            ],
            "management_configuration": [
                "Publish the customer complaint escalation route and the limits of employee authority for extra work.",
                "Provide each site with authorised access, restricted-area and customer property instructions.",
            ],
            "verification_tasks": [],
        },
    },
    {
        "code": "privacy-confidentiality",
        "title": "Privacy & Confidentiality",
        "category": "conduct",
        "sort_order": 90,
        "summary": "Protect customer, employee and company information encountered at work.",
        "acknowledgement_text": (
            "I understand that information and access credentials seen at work "
            "must be used only for authorised work and reported if lost or disclosed."
        ),
        "content": {
            "illustration": "privacy",
            "introduction": (
                "Cleaning staff may see names, addresses, health information, "
                "business records, screens, keys and alarm codes. Treat these "
                "as confidential even if they are visible or unattended. This "
                "module describes YD's workplace confidentiality expectations; "
                "it does not assume which privacy laws apply to the company."
            ),
            "objectives": [
                "Recognise confidential information and access credentials encountered during cleaning.",
                "Protect documents, computers, personal belongings and employee information from unnecessary access.",
                "Follow rules for keys, codes, photos, devices and company systems.",
                "Respond promptly if information or a credential may have been lost or exposed.",
                "Describe the limits of legal claims where an organisation's coverage has not been confirmed.",
            ],
            "why": (
                "A photo of a whiteboard, an unlocked computer or a misplaced "
                "key can expose information or create a security risk. Respect "
                "for confidentiality is part of safe, trustworthy service."
            ),
            "sections": [
                {
                    "title": "Information you may see",
                    "body": (
                        "Customer names, addresses, contact details, staff lists, "
                        "medical or financial papers, contracts, visitor logs, "
                        "computer screens and whiteboards can all be sensitive. "
                        "Do not read, copy, discuss or use information that is "
                        "not needed for your authorised work."
                    ),
                },
                {
                    "title": "Keys, codes and devices",
                    "body": (
                        "Keep keys and access credentials secure and use them "
                        "only for the assigned site and shift. Do not label a "
                        "key with a site address, share a code in a group chat "
                        "or save a customer password on a personal device. Lock "
                        "company systems when unattended and use only your own "
                        "approved login."
                    ),
                },
                {
                    "title": "Photos, video and social media",
                    "body": (
                        "Do not photograph or record inside a customer site "
                        "unless the company and site have expressly authorised "
                        "it for a defined work purpose. Never post customer "
                        "premises, people, documents or work problems on social "
                        "media. A customer request alone may not give you "
                        "company authority to record or share."
                    ),
                },
                {
                    "title": "Australian privacy obligations",
                    "body": (
                        "The Privacy Act 1988 (Cth) and Australian Privacy "
                        "Principles apply to organisations within their legal "
                        "scope, subject to the Act's coverage rules and "
                        "exceptions. Do not tell customers or colleagues that "
                        "YD is covered or exempt unless management has confirmed "
                        "that advice. Regardless of statutory coverage, follow "
                        "company confidentiality and customer site rules."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "You encounter confidential material",
                    "steps": [
                        "Do not read further, copy, photograph, move or discuss it unless the assigned task requires it.",
                        "Clean around papers and devices; do not touch controls, files or personal belongings without authority.",
                        "If an item blocks the agreed task, pause and ask the supervisor or site contact for direction.",
                        "Keep any information you have already seen confidential and report accidental access if required by the process.",
                    ],
                },
                {
                    "title": "A key, code or device may be lost",
                    "steps": [
                        "Tell the supervisor immediately using the urgent contact method.",
                        "State what is missing or exposed, the site, last known time and who may have had access.",
                        "Do not attempt to change a customer alarm or account password yourself.",
                        "Follow the manager's containment instructions and do not discuss the event outside the authorised group.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "An unlocked screen displays client records",
                    "body": (
                        "Do not read, photograph or use the information. If "
                        "cleaning would risk touching the keyboard or documents, "
                        "pause and ask the authorised site contact or supervisor "
                        "how to proceed."
                    ),
                },
                {
                    "title": "A key is missing after a shift",
                    "body": (
                        "Contact the supervisor immediately. Give the facts "
                        "needed to secure the site. Do not wait until the next "
                        "shift or message the code to a broad group."
                    ),
                },
            ],
            "responsibilities": [
                "Use information only for the assigned work purpose and disclose it only to authorised people.",
                "Secure keys and credentials; do not copy, label, share or store them insecurely.",
                "Do not make unauthorised recordings or social media posts at customer sites.",
                "Report suspected disclosure, loss, misdirection or unauthorised access promptly.",
            ],
            "mistakes": [
                "Reading a document because it is left open on a desk.",
                "Moving papers or switching off a computer to clean beneath it without permission.",
                "Sending access codes or customer photographs through personal messaging or social media.",
                "Using another employee's login or sharing your own login.",
                "Making unsupported statements about which privacy laws apply to YD.",
            ],
            "when_things_go_wrong": (
                "Report a lost key, exposed code, misdirected message, accidental "
                "photo or unauthorised access promptly to the supervisor. State "
                "what information or access may be involved and what containment "
                "steps you have taken. Do not delete evidence, send a broad "
                "notification or contact affected people unless management directs you."
            ),
            "scenario": {
                "title": "A spreadsheet is open on a reception computer",
                "prompt": (
                    "The spreadsheet displays employee names and bank details. "
                    "You need to wipe the desk, and a colleague asks you to take "
                    "a photo to show the supervisor that the reception area is "
                    "messy. What should you do?"
                ),
                "reflection": (
                    "Explain how to avoid accessing or sharing the information "
                    "and how to report that the work area cannot be cleaned as planned."
                ),
            },
            "assessment": [
                {
                    "question": "You see customer records open on a computer. What should you do?",
                    "choices": [
                        "Read them to find out who owns the desk.",
                        "Photograph them for the supervisor.",
                        "Avoid accessing or recording them and ask for direction if cleaning is blocked.",
                        "Email them to your personal account.",
                    ],
                    "correct": 2,
                    "explanation": "Only access information needed for authorised work; ask for direction rather than interact with the records.",
                },
                {
                    "question": "How should a customer alarm code be handled?",
                    "choices": [
                        "Share it with the whole cleaning team by text.",
                        "Use it only as authorised and keep it secure under the approved process.",
                        "Write it on a key tag with the site address.",
                        "Save it in a personal notes app.",
                    ],
                    "correct": 1,
                    "explanation": "Credentials must be restricted to authorised use and protected from disclosure.",
                },
                {
                    "question": "A colleague asks for a photo of a customer's documents to prove a spill occurred. What should you do?",
                    "choices": [
                        "Take the photo and post it in the group chat.",
                        "Do not photograph confidential documents; report the event through the approved process.",
                        "Use your personal phone but delete it later.",
                        "Send it to social media privately.",
                    ],
                    "correct": 1,
                    "explanation": "Use approved reporting channels; do not create or distribute unauthorised images of customer information.",
                },
                {
                    "question": "You cannot find a site key after your shift. What is the best response?",
                    "choices": [
                        "Wait until the next shift in case it turns up.",
                        "Tell the supervisor immediately with the relevant facts.",
                        "Ask a customer to change the locks.",
                        "Post the key details online.",
                    ],
                    "correct": 1,
                    "explanation": "Prompt escalation lets the authorised manager assess and contain the access risk.",
                },
                {
                    "question": "Which statement about the Privacy Act 1988 is accurate?",
                    "choices": [
                        "It applies identically to every Australian business without exceptions.",
                        "It may apply depending on legal coverage rules; do not claim YD is covered or exempt unless confirmed.",
                        "It never applies to cleaning companies.",
                        "It removes the need to follow customer confidentiality rules.",
                    ],
                    "correct": 1,
                    "explanation": "Coverage depends on the Act's rules and exceptions. Company confidentiality duties still apply.",
                },
                {
                    "question": "A customer asks you to post a before-and-after photo on your own social media. What should you do?",
                    "choices": [
                        "Post it if the customer said yes.",
                        "Post it without naming the site.",
                        "Do not post it; seek company authorisation through the approved process.",
                        "Ask a colleague to post it instead.",
                    ],
                    "correct": 2,
                    "explanation": "Company and site approval are required before recording or sharing customer-site images.",
                },
            ],
            "references": [
                {"label": "Office of the Australian Information Commissioner: Privacy Act", "url": "https://www.oaic.gov.au/privacy/privacy-legislation/the-privacy-act"},
                {"label": "YD confidentiality and acceptable-use instructions", "url": ""},
            ],
            "management_configuration": [
                "Confirm the company's privacy-law coverage with qualified advice before making employee or customer claims.",
                "Publish approved key/code handling, lost-credential escalation, incident reporting and photography rules.",
                "Define the approved company systems and devices for storing work information.",
            ],
            "verification_tasks": [],
        },
    },
    {
        "code": "emergency-procedures",
        "title": "Emergency Procedures",
        "category": "whs",
        "sort_order": 100,
        "summary": "Recognise an emergency, raise the alarm, evacuate and follow site-specific instructions.",
        "acknowledgement_text": (
            "I understand that I must follow the site's emergency plan, call 000 "
            "when emergency services are needed, and never re-enter an unsafe area."
        ),
        "content": {
            "illustration": "emergency",
            "introduction": (
                "Commercial cleaning often happens early or late, when fewer "
                "people are nearby. Know how to raise an alarm, leave the site "
                "and contact help before starting work. Every customer site has "
                "its own exits, alarms, assembly point and wardens; these details "
                "must be provided by management or the site's authorised contact."
            ),
            "objectives": [
                "Identify the site's evacuation route, exit, alarm method and assembly point before work.",
                "Respond safely to fire, smoke, medical emergencies and chemical exposure.",
                "Call 000 and provide the location and type of emergency clearly.",
                "Avoid electrical hazards and respond safely to power failure.",
                "Explain why you must not re-enter or attempt a rescue beyond your training.",
            ],
            "why": (
                "An alarm or incident can leave little time to find an exit. "
                "Knowing the site's arrangements and keeping routes clear helps "
                "you and others reach safety quickly."
            ),
            "sections": [
                {
                    "title": "Fire, smoke and evacuation",
                    "body": (
                        "Raise the alarm using the site method and call 000 "
                        "when emergency services are needed. Leave by the nearest "
                        "safe exit, do not use a lift unless the site emergency "
                        "plan specifically instructs it, and go to the nominated "
                        "assembly point. Do not collect equipment or return "
                        "inside for belongings. Follow wardens and emergency "
                        "services; do not re-enter until authorised."
                    ),
                },
                {
                    "title": "Medical emergency",
                    "body": (
                        "Call 000 for a serious or life-threatening condition. "
                        "Give the exact site address, entry point and nature of "
                        "the emergency. Request a first aider and follow the "
                        "call-taker's instructions. Do not move the person unless "
                        "they face immediate danger or movement is needed for care."
                    ),
                },
                {
                    "title": "Chemical and electrical emergencies",
                    "body": (
                        "For chemical splash or inhalation, get away from the "
                        "source and follow the product SDS/label first-aid "
                        "instructions. Do not enter a contaminated area or "
                        "approach a person in contact with electricity until "
                        "the source is isolated by a competent person. Keep "
                        "others clear and call emergency services when required."
                    ),
                },
                {
                    "title": "Power failure and communication",
                    "body": (
                        "Stop powered equipment, avoid dark stairs and use the "
                        "site's emergency lighting and exit instructions. Do not "
                        "use a phone as a substitute for an alarm or emergency "
                        "contact if it is unsafe to remain. At a safe location, "
                        "contact the site contact or supervisor as directed and "
                        "report whether people are accounted for."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Evacuate from fire or smoke",
                    "steps": [
                        "Raise the alarm and call 000 if emergency services are required.",
                        "Warn others only if you can do so without delaying your own safe exit.",
                        "Use the nearest safe marked exit and do not use a lift unless the site plan says otherwise.",
                        "Go to the confirmed assembly point and tell the warden/supervisor if anyone may be missing.",
                        "Stay out until emergency services or the authorised site controller permits re-entry.",
                    ],
                },
                {
                    "title": "Report a chemical splash or inhalation",
                    "steps": [
                        "Move away from the release to fresh air or a safe area without walking through the spill.",
                        "Call 000 for serious symptoms and request first aid.",
                        "Follow the product label/SDS first-aid instructions; do not apply an unapproved neutraliser.",
                        "Keep others out and notify the supervisor from a safe location.",
                        "Provide the product name only if it can be identified safely.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "Smoke is coming from a bin room",
                    "body": (
                        "Do not open the door to investigate or retrieve a trolley. "
                        "Raise the alarm, evacuate by a safe route, call 000 if "
                        "needed and report to the assembly point."
                    ),
                },
                {
                    "title": "A co-worker is shocked by a machine",
                    "body": (
                        "Do not touch the person or equipment while it may remain "
                        "live. Call 000, raise the alarm and wait for a competent "
                        "person to isolate the supply. Follow emergency service "
                        "instructions."
                    ),
                },
            ],
            "responsibilities": [
                "Learn the site exit, alarm, assembly point, warden and after-hours communication arrangements.",
                "Keep exit routes, fire doors and access to emergency equipment unobstructed.",
                "Evacuate promptly and follow wardens and emergency services.",
                "Report emergency hazards and do not re-enter until authorised.",
            ],
            "mistakes": [
                "Searching for equipment or personal items after an evacuation alarm.",
                "Opening a smoke-filled room or entering a chemical spill area to investigate.",
                "Touching a person who may still be in contact with an electrical source.",
                "Assuming the assembly point or alarm method is the same at every customer site.",
                "Returning inside because the alarm becomes quiet.",
            ],
            "when_things_go_wrong": (
                "Call 000 where emergency services are required. Tell the call "
                "taker the site address, exact access point and emergency type. "
                "Follow the site plan, move to safety and notify the site warden "
                "or supervisor. If the emergency arrangement is unknown, do not "
                "start a task that depends on it—ask management to confirm it."
            ),
            "scenario": {
                "title": "Smoke and a blocked exit",
                "prompt": (
                    "You smell smoke near your normal exit. The corridor is "
                    "partly blocked by cleaning equipment, and you cannot see "
                    "the source. What should you do?"
                ),
                "reflection": (
                    "Explain how you would raise the alarm, select a safe route, "
                    "avoid delaying for equipment and report at the assembly point."
                ),
            },
            "assessment": [
                {
                    "question": "You see smoke near your usual exit. What should you do?",
                    "choices": [
                        "Open the nearby door to investigate.",
                        "Raise the alarm, use a safe alternate exit and follow the site plan.",
                        "Finish the room first.",
                        "Use the lift to leave faster.",
                    ],
                    "correct": 1,
                    "explanation": "Do not investigate smoke or delay evacuation. Use a safe route and follow the site emergency plan.",
                },
                {
                    "question": "When should you call 000?",
                    "choices": [
                        "For an immediate or serious emergency requiring emergency services.",
                        "Only after the next shift.",
                        "For every routine cleaning request.",
                        "Only if a supervisor is physically present.",
                    ],
                    "correct": 0,
                    "explanation": "Call 000 for serious emergencies and provide the location and nature of the event.",
                },
                {
                    "question": "A co-worker may still be in contact with an electrical source. What should you do?",
                    "choices": [
                        "Pull them away by their clothing.",
                        "Touch the machine to test whether it is live.",
                        "Do not touch them or the equipment; call 000 and wait for safe isolation.",
                        "Pour water on the equipment.",
                    ],
                    "correct": 2,
                    "explanation": "You could become a second casualty. Keep clear and get emergency help and competent isolation.",
                },
                {
                    "question": "After evacuating, the alarm stops. What should you do?",
                    "choices": [
                        "Return to collect your phone.",
                        "Wait at the assembly point until authorised to re-enter.",
                        "Leave without telling anyone.",
                        "Go back if you cannot see smoke.",
                    ],
                    "correct": 1,
                    "explanation": "A quiet alarm does not confirm the hazard is over; re-entry must be authorised.",
                },
                {
                    "question": "A chemical splash causes severe breathing difficulty. What is the priority?",
                    "choices": [
                        "Find a mop and clean the spill.",
                        "Move to safety, call 000, follow SDS first aid and keep others away.",
                        "Mix another product to reduce the smell.",
                        "Wait until the symptoms pass.",
                    ],
                    "correct": 1,
                    "explanation": "Serious symptoms require urgent medical assistance; avoid exposure and follow the product first-aid information.",
                },
                {
                    "question": "Before starting work at a new site, what emergency information should be confirmed?",
                    "choices": [
                        "Only the location of the cleaning cupboard.",
                        "Exits, alarm method, assembly point and site emergency contacts/instructions.",
                        "Nothing if the shift is short.",
                        "A route chosen by another cleaner at a different site.",
                    ],
                    "correct": 1,
                    "explanation": "Emergency arrangements are site-specific and should be known before work begins.",
                },
            ],
            "references": [
                {"label": "Emergency Call Service: Triple Zero (000)", "url": "https://www.triplezero.gov.au/"},
                {"label": "SafeWork SA: Emergency plans", "url": "https://www.safework.sa.gov.au/workplaces/health-and-wellbeing/emergency-plans"},
            ],
            "management_configuration": [
                "Record each site's emergency exit, alarm activation, assembly point, warden and after-hours contact.",
                "Provide site-specific response arrangements for chemicals, electrical incidents and power failures.",
            ],
            "verification_tasks": [
                "Point out the assigned site's exit route, alarm point and assembly location.",
                "Explain the response to an electrical shock or chemical exposure scenario.",
            ],
        },
    },
    {
        "code": "time-attendance",
        "title": "Attendance, Timesheets & Punctuality",
        "category": "operations",
        "sort_order": 110,
        "summary": "Follow rosters, record actual work time and communicate changes promptly.",
        "acknowledgement_text": (
            "I understand that I must follow my roster, record actual work time "
            "accurately and report absence, lateness or timesheet errors promptly."
        ),
        "content": {
            "illustration": "attendance",
            "introduction": (
                "Accurate attendance information helps the company plan coverage, "
                "confirm customer service and process pay correctly. A roster is "
                "the authorised schedule; a timesheet is a record of what actually "
                "happened. Never alter a record to make it match the plan."
            ),
            "objectives": [
                "Check the published roster and know where to find shift updates.",
                "Record actual start, finish and breaks using the approved system.",
                "Notify the supervisor promptly when absent, delayed or unable to finish a shift.",
                "Request approval before swapping or changing a shift.",
                "Correct an error transparently while preserving an accurate record.",
            ],
            "why": (
                "A wrong time record can leave a site uncovered and create "
                "payroll errors. Prompt communication lets a supervisor arrange "
                "cover and keep the customer informed through the right channel."
            ),
            "sections": [
                {
                    "title": "Roster and shift changes",
                    "body": (
                        "Check the current roster in the approved portal or "
                        "company channel before travel. Confirm the site, time "
                        "and role. Do not rely on an old screenshot or informal "
                        "message if the current schedule is available. Do not "
                        "swap shifts or leave early without approval."
                    ),
                },
                {
                    "title": "Record actual time",
                    "body": (
                        "Use the approved timekeeping method at the time the "
                        "event occurs. Record actual start and finish and take "
                        "breaks as instructed by the applicable workplace "
                        "arrangement. Do not clock in for another person, record "
                        "time not worked, or change a break to hide a delay."
                    ),
                },
                {
                    "title": "Mobile app and connectivity",
                    "body": (
                        "Use only your own account and follow the current app "
                        "instructions. If the app is unavailable, the device "
                        "fails or connectivity prevents recording, note the "
                        "actual times and contact the supervisor using the "
                        "approved fallback process. Do not repeatedly submit "
                        "guessed times."
                    ),
                },
                {
                    "title": "Absence, lateness and correction",
                    "body": (
                        "Notify the supervisor as soon as you know you will be "
                        "late or absent, using the designated channel. Include "
                        "the affected shift and expected arrival only if known. "
                        "For a timesheet error, contact the supervisor/payroll "
                        "process with the date, original entry, correct actual "
                        "time and reason. Keep the correction transparent."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Start and finish a rostered shift",
                    "steps": [
                        "Check the latest roster and site details before travelling.",
                        "Record your actual arrival/start using the approved company method.",
                        "Record breaks and work status as they happen, following the provided instructions.",
                        "At shift end, record actual finish and update the assigned job status if required.",
                        "Report any discrepancy, system failure or incomplete task before leaving when possible.",
                    ],
                },
                {
                    "title": "Report a late arrival or absence",
                    "steps": [
                        "Contact the designated supervisor as soon as you know there is a problem.",
                        "Identify the shift/site and give a realistic update without guessing.",
                        "Follow instructions about customer cover or a safe change to the work plan.",
                        "Submit any required leave or attendance information through the approved process.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "The timekeeping app is offline",
                    "body": (
                        "Record the actual start and finish using the approved "
                        "fallback method and tell the supervisor promptly. Do "
                        "not enter a standard shift time if yours differed."
                    ),
                },
                {
                    "title": "A colleague asks you to clock them in",
                    "body": (
                        "Decline. Each employee must use their own account and "
                        "record their own actual time. Tell the supervisor if "
                        "the colleague cannot access the system."
                    ),
                },
            ],
            "responsibilities": [
                "Check the current roster and attend on time, ready for the scheduled work.",
                "Enter only your own actual work times and breaks through the approved method.",
                "Report absence, lateness, shift changes and system problems promptly.",
                "Request correction through the official process; never falsify or conceal an entry.",
            ],
            "mistakes": [
                "Using an old roster or assuming a shift has not changed.",
                "Clocking in for another person or sharing portal credentials.",
                "Entering scheduled hours when actual start/finish differed.",
                "Taking an unrecorded break or changing a record without an audit trail.",
                "Waiting until payroll closes to report a known error.",
            ],
            "when_things_go_wrong": (
                "Tell the supervisor promptly and provide the actual facts. "
                "If you cannot access the portal, use the fallback instructions "
                "management has supplied. Do not create a second account, share "
                "credentials or submit repeated guessed entries."
            ),
            "scenario": {
                "title": "A delayed bus and a failed clock-in",
                "prompt": (
                    "You expect to arrive 20 minutes late. On arrival, the "
                    "mobile app will not load. What should you communicate, "
                    "and how can you keep the time record accurate?"
                ),
                "reflection": (
                    "Identify who to contact, what time facts to record and "
                    "why you must not enter the rostered start time."
                ),
            },
            "assessment": [
                {
                    "question": "What should a timesheet record?",
                    "choices": [
                        "The standard roster times regardless of what happened.",
                        "Your actual work times and breaks using the approved process.",
                        "A colleague's hours if they forgot.",
                        "An estimate that helps payroll finish sooner.",
                    ],
                    "correct": 1,
                    "explanation": "Attendance records must reflect what actually happened and be entered through the approved process.",
                },
                {
                    "question": "You know you will be late. When should you notify the supervisor?",
                    "choices": [
                        "As soon as you know there is a problem.",
                        "At the end of the week.",
                        "Only if the customer asks.",
                        "After changing the roster yourself.",
                    ],
                    "correct": 0,
                    "explanation": "Early notice gives the supervisor time to arrange coverage and manage customer communication.",
                },
                {
                    "question": "The app is offline at shift start. What should you do?",
                    "choices": [
                        "Enter a guessed time later.",
                        "Use the approved fallback, record actual times and tell the supervisor.",
                        "Use a colleague's login.",
                        "Do nothing and hope it syncs.",
                    ],
                    "correct": 1,
                    "explanation": "Use the authorised contingency method and preserve an accurate record.",
                },
                {
                    "question": "A colleague asks you to clock them in because they are running late. What is the right response?",
                    "choices": [
                        "Do it once as a favour.",
                        "Use their password and keep it private.",
                        "Decline and direct them to contact the supervisor.",
                        "Change your own timesheet to cover their time.",
                    ],
                    "correct": 2,
                    "explanation": "Employees must not record time for another person or share system access.",
                },
                {
                    "question": "You notice a submitted finish time is wrong. What should you do?",
                    "choices": [
                        "Delete the whole timesheet.",
                        "Report the date, actual time and error through the approved correction process.",
                        "Ask a colleague to edit it.",
                        "Leave it because the shift is already submitted.",
                    ],
                    "correct": 1,
                    "explanation": "An authorised, traceable correction keeps the record accurate without hiding the change.",
                },
                {
                    "question": "A supervisor has not approved your proposed shift swap. What should you do?",
                    "choices": [
                        "Swap anyway and update the roster later.",
                        "Assume silence means approval.",
                        "Follow the existing roster until the change is confirmed.",
                        "Ask the customer to approve it.",
                    ],
                    "correct": 2,
                    "explanation": "Continue with the authorised schedule unless a change is confirmed through the company process.",
                },
            ],
            "references": [
                {"label": "YD roster, employee portal and timekeeping instructions", "url": ""},
                {"label": "Applicable employment instrument and payroll process (management to confirm)", "url": ""},
            ],
            "management_configuration": [
                "Publish the current app/timekeeping instructions, accepted fallback process and correction contact.",
                "Confirm the applicable break, shift-change, absence and leave procedures for each employment arrangement.",
            ],
            "verification_tasks": [],
        },
    },
    {
        "code": "uniform-appearance",
        "title": "Uniform & Professional Appearance",
        "category": "conduct",
        "sort_order": 120,
        "summary": "Maintain a clean, practical presentation and distinguish uniform from task PPE.",
        "acknowledgement_text": (
            "I understand the presentation requirements provided for my role "
            "and will report missing, damaged or unsuitable uniform and footwear."
        ),
        "content": {
            "illustration": "uniform",
            "introduction": (
                "Your presentation helps customers identify the cleaning team "
                "and signals care and professionalism. Uniform is work clothing; "
                "PPE is selected to control a task hazard. The exact YD uniform "
                "items, identification and footwear rules must be confirmed by "
                "management rather than guessed."
            ),
            "objectives": [
                "Follow the confirmed uniform and identification requirements for your role and site.",
                "Keep work clothing clean, serviceable and suitable for the task.",
                "Choose footwear that meets the site requirement and is safe for the surfaces you clean.",
                "Separate personal presentation from task-specific PPE requirements.",
                "Report missing or damaged items before they create a safety or customer issue.",
            ],
            "why": (
                "Clean, consistent presentation supports trust and helps identify "
                "authorised staff. Damaged clothing, poor footwear or loose items "
                "can also create hygiene, slip or entanglement risks."
            ),
            "sections": [
                {
                    "title": "Uniform and site identification",
                    "body": (
                        "Wear the approved uniform and identification supplied "
                        "or specified for your role. Keep identification visible "
                        "where the site requires it, but do not expose access "
                        "credentials. If a uniform item is missing, ask the "
                        "supervisor what approved alternative is acceptable "
                        "before arriving at a customer site."
                    ),
                },
                {
                    "title": "Footwear and grooming",
                    "body": (
                        "Use footwear that is secure, supportive, in good repair "
                        "and meets the site/company requirements. Check soles "
                        "for wear and keep them clean enough to avoid tracking "
                        "soil between areas. Maintain personal hygiene and tie "
                        "back hair or secure loose items when required by the task."
                    ),
                },
                {
                    "title": "Uniform is not PPE",
                    "body": (
                        "A polo shirt does not protect against chemical splash, "
                        "and ordinary gloves or shoes may not meet the task "
                        "risk controls. Put on the specified PPE for the work, "
                        "even when it differs from normal uniform. Do not modify "
                        "PPE or uniform in a way that removes its protective function."
                    ),
                },
                {
                    "title": "Care and replacement",
                    "body": (
                        "Follow the care instructions for each garment. Keep "
                        "clean and contaminated work clothing separate; do not "
                        "take contaminated PPE home unless the approved process "
                        "allows it. Tell the supervisor about tears, missing "
                        "items, persistent contamination or footwear damage and "
                        "request a replacement."
                    ),
                },
            ],
            "procedure": [
                {
                    "title": "Prepare before a shift",
                    "steps": [
                        "Check the site and role instructions for required uniform, ID and PPE.",
                        "Wear clean, serviceable clothing and secure loose hair, jewellery or drawstrings as the task requires.",
                        "Inspect footwear for secure fit, damage and worn soles.",
                        "Pack the task-specific PPE separately so it remains clean and available.",
                        "Tell the supervisor before the shift if a required item is missing or damaged.",
                    ],
                },
                {
                    "title": "Manage contamination or damage",
                    "steps": [
                        "Stop work if clothing or footwear damage creates a hazard or exposes skin.",
                        "Avoid spreading contamination to vehicles, homes or clean storage areas.",
                        "Follow the site/company cleaning or disposal instruction; do not improvise laundry handling for hazardous contamination.",
                        "Report the issue and obtain an approved replacement before resuming the affected work.",
                    ],
                },
            ],
            "examples": [
                {
                    "title": "A sole is separating before a wet-floor shift",
                    "body": (
                        "Do not assume it is acceptable because the footwear is "
                        "otherwise comfortable. Tell the supervisor and obtain "
                        "an approved safe replacement before working on wet floors."
                    ),
                },
                {
                    "title": "Uniform is clean but chemical PPE is missing",
                    "body": (
                        "Do not start the chemical task in uniform alone. Ask "
                        "for the required compatible PPE and follow the task "
                        "assessment; the uniform does not control that exposure."
                    ),
                },
            ],
            "responsibilities": [
                "Follow the confirmed uniform, footwear and identification instructions for your site.",
                "Keep garments and footwear clean, serviceable and suitable for work.",
                "Wear task-specific PPE in addition to uniform when required.",
                "Report missing, damaged or contaminated items and ask about an approved alternative.",
            ],
            "mistakes": [
                "Assuming any dark clothing counts as company uniform.",
                "Wearing damaged or loose footwear on wet floors.",
                "Treating uniform as protection from chemical or biological hazards.",
                "Wearing loose jewellery or unsecured clothing near moving equipment.",
                "Taking contaminated items home without following the approved handling instruction.",
            ],
            "when_things_go_wrong": (
                "If an item is missing, damaged or contaminated, stop the task "
                "that depends on it and contact the supervisor. Describe the "
                "item and the hazard. Use only an approved alternative; do not "
                "borrow another worker's personal PPE or alter uniform to imitate PPE."
            ),
            "scenario": {
                "title": "A torn sleeve and a chemical task",
                "prompt": (
                    "You arrive with a torn sleeve and are assigned to a task "
                    "requiring protective clothing and chemical-resistant gloves. "
                    "A customer offers an old jacket from a cupboard. What should "
                    "you check before starting?"
                ),
                "reflection": (
                    "Explain why a customer-provided garment is not automatically "
                    "an approved control and who can confirm a safe replacement."
                ),
            },
            "assessment": [
                {
                    "question": "What is the difference between uniform and PPE?",
                    "choices": [
                        "They are always the same.",
                        "Uniform identifies/presents the worker; PPE is selected to control a specific task hazard.",
                        "Uniform always protects against chemicals.",
                        "PPE is optional if the uniform is clean.",
                    ],
                    "correct": 1,
                    "explanation": "Uniform and PPE serve different purposes; wear the task controls identified for the work.",
                },
                {
                    "question": "Your required footwear has a worn smooth sole before a wet-floor shift. What should you do?",
                    "choices": [
                        "Continue carefully and avoid telling anyone.",
                        "Ask the supervisor for an approved safe replacement before the affected work.",
                        "Cover the sole with tape.",
                        "Wear socks over the shoes.",
                    ],
                    "correct": 1,
                    "explanation": "Damaged or unsuitable footwear can create slip risk; obtain an approved replacement.",
                },
                {
                    "question": "A required uniform item is missing. What is the best action?",
                    "choices": [
                        "Wear a customer's spare clothing.",
                        "Ask the supervisor what approved alternative is acceptable.",
                        "Use another employee's ID.",
                        "Skip the shift without reporting.",
                    ],
                    "correct": 1,
                    "explanation": "Management must confirm an acceptable alternative for the role and site.",
                },
                {
                    "question": "A uniform is clean but task-specific chemical gloves are unavailable. Can you begin?",
                    "choices": [
                        "Yes, because clean clothes are enough.",
                        "Yes, if you work quickly.",
                        "No; pause the chemical task and obtain the specified PPE.",
                        "Use any glove from a customer cupboard.",
                    ],
                    "correct": 2,
                    "explanation": "Uniform does not replace hazard-specific PPE.",
                },
                {
                    "question": "Your work clothing becomes contaminated with an unknown substance. What should you do?",
                    "choices": [
                        "Take it home and wash it with family laundry.",
                        "Follow the site/company contamination instructions and report it.",
                        "Shake it out in the staff room.",
                        "Wear it for the rest of the shift.",
                    ],
                    "correct": 1,
                    "explanation": "Unknown contamination should not be spread or handled by an improvised laundry method.",
                },
                {
                    "question": "Why should loose jewellery and unsecured clothing be controlled around equipment?",
                    "choices": [
                        "They can catch in moving parts or interfere with the task.",
                        "They make the uniform look too new.",
                        "They always damage floors.",
                        "They replace the need for PPE.",
                    ],
                    "correct": 0,
                    "explanation": "Loose items may snag and create an entanglement or other task hazard.",
                },
            ],
            "references": [
                {"label": "YD uniform, identification and laundry requirements", "url": ""},
                {"label": "Task-specific risk assessment and PPE instructions", "url": ""},
            ],
            "management_configuration": [
                "Publish the approved uniform pieces, ID display rules, footwear standard and issue/replacement process.",
                "Define handling and laundering arrangements for contaminated garments and reusable PPE.",
            ],
            "verification_tasks": [],
        },
    },
]

