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
     "Mentored two junior engineers [on what, e.g. pipeline reviews or on-call]."),
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
    ("Built weekly claims dashboards in Tableau for the operations team.",
     "Built weekly claims dashboards in Tableau, saving the operations team hours of manual work.", "invented benefit"),
    ("Worked with designers in Figma to ship a new onboarding screen.",
     "Led cross-functional collaboration with designers in Figma to ship a new onboarding screen.", "invented leadership"),
    ("Maintained the company WordPress site and fixed CSS bugs.",
     "Maintained the company WordPress site and fixed CSS bugs, improving site performance and SEO.", "invented results"),
]
