"""Hand-written rewrites used to measure the validator itself.

GOOD: honest improvements a careful editor would make (same facts, better wording).
BAD: each adds exactly one kind of fabrication. The validator should accept every
GOOD case and reject every BAD case. Written by hand, not by a model.
"""

GOOD = [
    # (original, rewrite)
    ("Maintain Airflow pipelines that load shipment data into Snowflake.",
     "Maintain the Airflow pipelines that load shipment data into Snowflake."),
    ("Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.",
     "Cut nightly load failures from 9 to 2 per month by adding data quality checks."),
    ("Mentored two junior engineers.",
     "Mentored two junior engineers [over N months]."),
    ("Built weekly claims dashboards in Tableau for the operations team.",
     "Built the operations team's weekly claims dashboards in Tableau."),
    ("Wrote SQL models that the pricing team used for monthly reporting.",
     "Wrote the SQL models behind the pricing team's monthly reporting."),
    ("Built React components for the checkout flow, cutting checkout drop-off from 31% to 24%.",
     "Cut checkout drop-off from 31% to 24% by building React components for the checkout flow."),
    ("Worked with designers in Figma to ship a new onboarding screen.",
     "Partnered with designers in Figma to ship a new onboarding screen."),
    ("Wrote Jest unit tests for the payments module.",
     "Wrote Jest unit tests covering the payments module."),
    ("Maintained the company WordPress site and fixed CSS bugs.",
     "Maintained the company's WordPress site, fixing CSS bugs as they came up."),
    ("Rebuilt the newsletter signup form, which doubled weekly signups.",
     "Doubled weekly newsletter signups by rebuilding the signup form."),
    ("Responsible for scheduling shifts for the night team.",
     "Scheduled shifts for the night team."),
    ("Helped organise the annual sales conference.",
     "Helped organise the annual sales conference [for about N attendees]."),
    # Messy, real-world bullets: the improvements a rewriter should be able to make.
    ("Was in charge of handling customer complaints that came in through email and phone for the UK market.",
     "Handled UK customer complaints across email and phone."),
    ("Did weekly reporting on ticket volumes for management using Zendesk and Excel.",
     "Reported weekly ticket volumes to management using Zendesk and Excel."),
    ("Responsible for making sure SLAs were met, which went from 82% to 95% over the year.",
     "Owned SLAs, with attainment rising from 82% to 95% over the year."),
    ("Helped new agents get up to speed by answering their questions and sitting with them on calls.",
     "Helped new agents ramp up by answering their questions and joining them on calls."),
    ("Worked closely with the product team giving them feedback from customers about bugs.",
     "Partnered with the product team, passing on customer feedback about bugs."),
    ("Part of the team that moved the help centre to a new platform in 2020.",
     "Helped move the help centre to a new platform in 2020."),
    ("Handled around 60 chats a day with a customer satisfaction score of 4.7 out of 5.",
     "Handled around 60 chats a day while keeping a 4.7 out of 5 customer satisfaction score."),
]

BAD = [
    # (original, rewrite, what it fabricates)
    ("Mentored two junior engineers.", "Mentored two junior engineers, boosting team velocity by 35%.", "invented percentage"),
    ("Maintain Airflow pipelines that load shipment data into Snowflake.", "Maintain Airflow and Kafka pipelines that stream shipment data into Snowflake.", "missing skill claimed"),
    ("Maintain Airflow pipelines that load shipment data into Snowflake.", "Maintain Airflow pipelines in Python that load shipment data into Snowflake.", "tool from elsewhere in resume"),
    ("Maintain Airflow pipelines that load shipment data into Snowflake.", "Built Airflow pipelines that load shipment data into Snowflake.", "maintain -> built"),
    ("Helped organise the annual sales conference.", "Led the annual sales conference.", "helped -> led"),
    ("Mentored two junior engineers.", "Managed two junior engineers.", "mentored -> managed"),
    ("Reduced nightly load failures from 9 per month to 2 per month by adding data quality checks.",
     "Reduced nightly load failures from 9 per effects to 2 per month by adding data quality checks.", "garbled metric"),
    ("Mentored two junior engineers.", "Mentored a team of 5 junior engineers.", "invented team size"),
    ("Wrote SQL models that the pricing team used for monthly reporting.",
     "Wrote SQL models that improved reporting accuracy for the pricing team.", "invented outcome"),
    ("Did weekly reporting on ticket volumes for management using Zendesk and Excel.",
     "Generated weekly ticket volume reports for management using Zendesk and Excel, highlighting key trends.", "invented detail"),
    ("Handled around 60 chats a day with a customer satisfaction score of 4.7 out of 5.",
     "Handled 60 chats daily with a customer satisfaction score of 4.7 out of 5.", "approximate made exact"),
    ("Built weekly claims dashboards in Tableau for the operations team.",
     "Built weekly claims dashboards in Tableau, saving the operations team hours of manual work.", "invented benefit"),
    ("Worked with designers in Figma to ship a new onboarding screen.",
     "Led cross-functional collaboration with designers in Figma to ship a new onboarding screen.", "invented leadership"),
    ("Maintained the company WordPress site and fixed CSS bugs.",
     "Maintained the company WordPress site and fixed CSS bugs, improving site performance and SEO.", "invented results"),
]
