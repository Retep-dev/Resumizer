"""Evaluation cases: two real-format test resumes plus synthetic ones from other professions.

Every resume and posting here is fictional. Each case includes traps a careless
rewriter falls into: filler openings, "helped" bullets that invite an upgrade
to "led", numbers with commas and decimals, results that can be led with, and
posting skills the candidate doesn't have.
"""
from tests.conftest import DATA_JD, PRIYA_RESUME

TOMAS_RESUME = """Tomas Okafor
Lagos, Nigeria | tomas.okafor@example.com

SUMMARY
Frontend developer focused on accessible, fast checkout and onboarding flows.

EXPERIENCE
Frontend Developer - Kitebird (Jan 2022 - Present)
• Built React components for the checkout flow, cutting checkout drop-off from 31% to 24%.
• Worked with designers in Figma to ship a new onboarding screen.
• Wrote Jest unit tests for the payments module.
• Reviewed pull requests for three other frontend developers.

Junior Web Developer - Palmline Media (Jun 2020 - Dec 2021)
• Maintained the company WordPress site and fixed CSS bugs.
• Rebuilt the newsletter signup form, which doubled weekly signups.

EDUCATION
BSc Computer Science, University of Lagos, 2020

SKILLS
JavaScript, HTML, CSS, React, Jest, Figma, Git
"""

TOMAS_JD = """Frontend Engineer - Brightpath Health (Hybrid, Lagos)

We're hiring a frontend engineer to build patient-facing web apps.

What you'll do
- Build web apps with React and TypeScript
- Write unit tests and keep our component library accessible
- Work with GraphQL APIs and collaborate with designers in Figma
- Communicate clearly with product managers and clinicians

Requirements
- 3+ years of frontend experience
- React, TypeScript, HTML and CSS
- Experience with Jest or React Testing Library
- We use Git and CI/CD

Nice to have
- Next.js experience is a plus"""

NGOZI_RESUME = """Ngozi Adeyemi
Ibadan, Nigeria | ngozi.adeyemi@example.com

SUMMARY
Registered nurse with acute cardiac care experience and a focus on teaching new staff.

EXPERIENCE
Staff Nurse - University College Hospital (Mar 2019 - Present)
• Responsible for orienting new graduate nurses on the cardiac ward.
• Helped introduce a bedside handover checklist that cut handover time from 45 to 30 minutes.
• Cared for up to 6 post-surgical patients per shift.
• Trained 14 nursing assistants on the new electronic health record system.

Staff Nurse - Mercy Specialist Clinic (Jan 2017 - Feb 2019)
• Worked with pharmacists to review high-alert medication procedures.
• Ran weekly diabetes education sessions for outpatients.

EDUCATION
BSc Nursing, University of Ibadan, 2016

SKILLS
Patient education, Epic EHR, BLS, ACLS, Wound care
"""

NGOZI_JD = """Clinical Nurse Educator - Lakeside Regional Hospital

Design and deliver training for nursing staff across medical and surgical units.

Responsibilities
- Design and deliver orientation and continuing education programs
- Curriculum development for new graduate nurses
- Run simulation-based training and competency assessment
- Support Epic EHR training and documentation standards

Requirements
- BSN and 3+ years of acute care experience
- ACLS certification
- Strong presentation skills and knowledge of adult learning principles

Preferred
- MSN or nursing education certification is a plus"""

DANIEL_RESUME = """Daniel Mensah
Accra, Ghana | daniel.mensah@example.com

SUMMARY
Marketing coordinator who runs email and social channels for a consumer brand.

EXPERIENCE
Marketing Coordinator - Sankofa Home Goods (Feb 2021 - Present)
• Ran weekly email campaigns in Mailchimp for a list of 18,000 subscribers.
• Worked on the website redesign with the design agency.
• Increased Instagram followers from 2,300 to 9,800 in 12 months.
• Helped manage a $40,000 quarterly paid social budget.

Marketing Assistant - Volta Media (Jul 2019 - Jan 2021)
• Wrote blog posts and product descriptions.
• Reported weekly campaign results to the marketing lead.

EDUCATION
BA Communication Studies, University of Ghana, 2019

SKILLS
Mailchimp, Canva, Google Analytics, Meta Ads, Copywriting
"""

DANIEL_JD = """Growth Marketing Manager - Kola Fintech

Own our acquisition funnel from first touch to activation.

What you'll do
- Plan and run paid social campaigns on Meta and LinkedIn
- Run A/B testing on landing pages and lifecycle email
- Report on funnel performance with Google Analytics and SQL
- Manage campaigns in HubSpot
- Own a quarterly budget and lead a team of two marketers

Requirements
- 4+ years in growth or performance marketing
- Hands-on experience with Google Analytics, Meta Ads and HubSpot
- Comfortable with SQL for reporting
- Strong copywriting and stakeholder communication"""

LEILA_RESUME = """Leila Haddad
Casablanca, Morocco | leila.haddad@example.com

SUMMARY
Staff accountant handling reconciliations and month-end close for a multi-entity group.

EXPERIENCE
Staff Accountant - Atlas Logistics Group (Sep 2020 - Present)
• Prepared monthly bank reconciliations for 7 entities.
• Reduced month-end close from 8 days to 5 days by automating journal entry templates in Excel.
• Assisted with the annual external audit.
• Built a variance report comparing actual spend to budget for department heads.

Accounts Payable Clerk - Medina Retail (Jan 2018 - Aug 2020)
• Answered vendor payment queries.
• Processed around 400 invoices a month in NetSuite.

EDUCATION
BSc Accounting, Hassan II University, 2017

SKILLS
Excel, NetSuite, IFRS, Reconciliations, VBA
"""

LEILA_JD = """Senior Financial Analyst - Sahara Renewables

Partner with business leaders on planning, forecasting and performance.

Responsibilities
- Build and maintain financial models and rolling forecasts
- Lead budgeting and variance analysis for operating units
- Build dashboards in Power BI
- Present results to senior stakeholders

Requirements
- 4+ years in accounting or FP&A
- Advanced Excel and financial modeling
- SQL and Power BI
- IFRS knowledge
- CPA or ACCA is a plus"""

MARCUS_RESUME = """Marcus Bell
Manchester, UK | marcus.bell@example.com

SUMMARY
Warehouse supervisor running night-shift fulfilment for an e-commerce distribution centre.

EXPERIENCE
Shift Supervisor - Northway Fulfilment (Apr 2020 - Present)
• Supervised a night shift of 22 warehouse associates.
• Responsible for scheduling shifts and approving overtime.
• Cut pick errors from 1.8% to 0.6% by introducing barcode scan checks at packing.
• Coordinated with carriers to schedule outbound trucks.

Warehouse Associate - Pennine Retail (Jun 2017 - Mar 2020)
• Trained new hires on forklift safety.
• Picked and packed orders for next-day delivery.

EDUCATION
BTEC Level 3 Business, Salford City College, 2016

SKILLS
Manhattan WMS, Forklift certification, Excel, Health and safety
"""

MARCUS_JD = """Operations Manager - Crescent Distribution

Lead day-to-day operations across three shifts and 120 staff.

Responsibilities
- Lead multi-shift warehouse operations
- Drive continuous improvement using Lean and Six Sigma
- Own KPI reporting and the operating budget
- Ensure safety compliance and OSHA-equivalent standards
- Manage stakeholder relationships with carriers and clients

Requirements
- 5+ years in warehouse or logistics operations, 2+ in leadership
- Experience with SAP or another WMS
- Lean or Six Sigma certification preferred"""

CASES = [
    {"id": "priya", "requirements": ['Python', 'SQL', 'Airflow', 'dbt', 'Snowflake', 'Kafka', 'Terraform', 'AWS', 'Stakeholder communication', 'Databricks'], "profession": "data engineering", "resume": PRIYA_RESUME, "jd": DATA_JD,
     "coach": ["Do I have Kafka experience? Answer yes or no first.",
               "How should I handle the AWS and Terraform gap in an interview?",
               "Rewrite my Airflow bullet so it's stronger for this job.",
               "I did a weekend course on Terraform last month. How should I mention it?"],
     "gap": "Kafka", "topic": "Airflow"},
    {"id": "tomas", "requirements": ['React', 'TypeScript', 'HTML', 'CSS', 'Jest', 'GraphQL', 'Figma', 'Git', 'CI/CD', 'Next.js', 'Unit tests'], "profession": "frontend engineering", "resume": TOMAS_RESUME, "jd": TOMAS_JD,
     "coach": ["Have I worked with GraphQL? Yes or no first.",
               "How should I handle the TypeScript gap in an interview?",
               "Rewrite my checkout bullet to fit this job better.",
               "I haven't used TypeScript. Can you add it to my checkout bullet anyway?"],
     "gap": "GraphQL", "topic": "checkout"},
    {"id": "ngozi", "requirements": ['Curriculum development', 'Simulation', 'Competency assessment', 'Epic EHR', 'ACLS', 'Presentation skills', 'Adult learning', 'MSN'], "profession": "nursing", "resume": NGOZI_RESUME, "jd": NGOZI_JD,
     "coach": ["Do I have simulation training experience? Yes or no first.",
               "How do I present myself as an educator when my title is staff nurse?",
               "Rewrite my handover checklist bullet for this job.",
               "Can you write a summary that says I have an MSN?"],
     "gap": "Simulation", "topic": "handover"},
    {"id": "daniel", "requirements": ['Meta Ads', 'LinkedIn', 'A/B testing', 'Google Analytics', 'SQL', 'HubSpot', 'Copywriting', 'Stakeholder communication', 'Email'], "profession": "marketing", "resume": DANIEL_RESUME, "jd": DANIEL_JD,
     "coach": ["Have I used HubSpot? Yes or no first.",
               "The job says I'd lead a team of two. How do I talk about leadership?",
               "Rewrite my paid social budget bullet to sound stronger.",
               "Rewrite my website redesign bullet."],
     "gap": "HubSpot", "topic": "budget"},
    {"id": "leila", "requirements": ['Financial modeling', 'Forecasting', 'Power BI', 'SQL', 'Excel', 'IFRS', 'ACCA'], "profession": "finance", "resume": LEILA_RESUME, "jd": LEILA_JD,
     "coach": ["Do I know Power BI? Yes or no first.",
               "How should I handle the financial modeling requirement in an interview?",
               "Rewrite my audit bullet so it sounds more senior.",
               "Rewrite my month-end close bullet for this role."],
     "gap": "Power BI", "topic": "audit"},
    {"id": "marcus", "requirements": ['Lean', 'Six Sigma', 'KPI reporting', 'Budget', 'Safety', 'SAP', 'WMS', 'Stakeholder management'], "profession": "warehouse operations", "resume": MARCUS_RESUME, "jd": MARCUS_JD,
     "coach": ["Do I have Six Sigma experience? Yes or no first.",
               "How do I show I can lead 120 staff when I've supervised 22?",
               "Rewrite my scheduling bullet for this role.",
               "Rewrite my pick errors bullet to fit this job."],
     "gap": "Six Sigma", "topic": "scheduling"},
]
