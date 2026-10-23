// Sample data for the design previews only.
// Shape mirrors the real backend response (backend/app/schemas/resume.py →
// AnalyzeResponse { session_id, analysis: AnalysisResult }) so a chosen design
// can be wired to the live API without changing its components.
// The candidate, employers and role are fictional.

export const SAMPLE_JD = `Senior Product Analyst — Fieldnote (Remote, EMEA)

Fieldnote helps 40,000 teachers plan lessons together. You'll own product analytics for our planning workspace: define success metrics, design and read experiments, and turn usage data into roadmap decisions.

You have
• 4+ years in product or growth analytics
• Expert SQL and Python; dbt and a modern warehouse (Snowflake preferred)
• Experience running A/B tests on an experimentation platform, and comfort with causal inference when you can't
• Product analytics tools such as Amplitude or Looker
• Retention modeling and cohort analysis
• The ability to tell a clear story to executives`;

export const SAMPLE_RESPONSE = {
  session_id: 'preview-0000-sample',
  analysis: {
    resume_data: {
      full_name: 'Noor Castellan',
      email: 'noor.castellan@example.com',
      phone: null,
      location: 'Lisbon, Portugal',
      linkedin: 'linkedin.com/in/example',
      github: null,
      summary:
        'Product analyst with five years of experience in SQL, Python and dashboarding for subscription products.',
      technical_skills: ['SQL', 'Python', 'dbt', 'A/B testing', 'Statistics'],
      soft_skills: ['Stakeholder communication', 'Mentoring'],
      tools_and_frameworks: ['Looker', 'BigQuery', 'Git', 'Airflow'],
      work_experience: [
        {
          company: 'Kettlebrook',
          job_title: 'Product Analyst',
          location: 'Lisbon',
          start_date: '2022',
          end_date: 'Present',
          bullet_points: [
            'Built dashboards for the onboarding team.',
            'Ran A/B tests on the pricing page.',
            'Worked with engineers to fix tracking issues.',
          ],
        },
        {
          company: 'Parcel & Pine',
          job_title: 'Data Analyst',
          location: 'Porto',
          start_date: '2020',
          end_date: '2022',
          bullet_points: [
            'Responsible for weekly reporting to leadership.',
            'Helped migrate reports to dbt.',
          ],
        },
      ],
      education: [
        {
          institution: 'University of Porto',
          degree: 'MSc',
          field_of_study: 'Applied Statistics',
          graduation_year: '2020',
        },
      ],
      certifications: [],
      projects: [],
    },
    ats_score: {
      overall_score: 72,
      keyword_match_score: 64,
      experience_match_score: 81,
      formatting_score: 88,
      breakdown_summary:
        'Strong analytics foundation and the right seniority. The resume undersells experimentation work and never names the warehouse or product-analytics tools this role screens for, so keyword match is the main drag on the score.',
      matched_keywords: ['SQL', 'Python', 'dbt', 'A/B testing', 'Looker', 'Product analytics', 'Stakeholder communication'],
      missing_keywords: ['Snowflake', 'Amplitude', 'Causal inference', 'Retention modeling', 'Experimentation platform', 'Executive storytelling'],
    },
    skill_gap: {
      matched_hard_skills: ['SQL', 'Python', 'dbt', 'Looker', 'A/B testing'],
      missing_hard_skills: ['Snowflake', 'Amplitude', 'Causal inference', 'Retention modeling'],
      matched_soft_skills: ['Stakeholder communication', 'Mentoring'],
      missing_soft_skills: ['Executive storytelling'],
      priority_skill_recommendations: [
        'Name the experimentation work explicitly: how many tests, what platform, what decision each one changed.',
        'Add a retention or cohort project — the Kettlebrook onboarding dashboards are the closest evidence you have.',
        'If you have used BigQuery, say so next to Snowflake-style warehouse experience; the skills transfer and screeners look for the category.',
      ],
    },
    rewrite_report: {
      tailored_summary:
        'Product analyst with five years turning usage data into roadmap decisions for subscription products. Designs and reads A/B tests end to end, models onboarding retention in SQL, Python and dbt, and presents findings to executive audiences.',
      rewritten_experiences: [
        {
          company: 'Kettlebrook',
          job_title: 'Product Analyst',
          rewritten_bullets: [
            {
              original_bullet: 'Built dashboards for the onboarding team.',
              rewritten_bullet:
                'Built Looker cohort dashboards for onboarding that exposed a day-3 retention drop, leading to a redesigned checklist that lifted week-4 retention by 9%.',
              star_action: 'Built Looker cohort dashboards for onboarding',
              star_result: 'Week-4 retention up 9%',
              added_keywords: ['Retention modeling', 'Product analytics'],
            },
            {
              original_bullet: 'Ran A/B tests on the pricing page.',
              rewritten_bullet:
                'Designed and analysed 14 pricing-page A/B tests on an in-house experimentation platform; the winning annual-plan layout raised paid conversion 6.2% at 95% confidence.',
              star_action: 'Designed and analysed 14 pricing-page A/B tests',
              star_result: 'Paid conversion up 6.2%',
              added_keywords: ['Experimentation platform', 'A/B testing'],
            },
            {
              original_bullet: 'Worked with engineers to fix tracking issues.',
              rewritten_bullet:
                'Led a tracking audit with engineering that removed 31 broken events and cut dashboard discrepancies from 12% to under 2%.',
              star_action: 'Led a tracking audit with engineering',
              star_result: 'Discrepancies down from 12% to <2%',
              added_keywords: ['Product analytics'],
            },
          ],
        },
        {
          company: 'Parcel & Pine',
          job_title: 'Data Analyst',
          rewritten_bullets: [
            {
              original_bullet: 'Responsible for weekly reporting to leadership.',
              rewritten_bullet:
                'Rebuilt the weekly leadership report as a one-page narrative with three decisions per week, cutting meeting time by 40 minutes.',
              star_action: 'Rebuilt the weekly leadership report as a narrative',
              star_result: '40 minutes saved weekly',
              added_keywords: ['Executive storytelling'],
            },
            {
              original_bullet: 'Helped migrate reports to dbt.',
              rewritten_bullet:
                'Migrated 60 legacy SQL reports into tested dbt models, reducing nightly pipeline failures from weekly to once a quarter.',
              star_action: 'Migrated 60 legacy SQL reports into dbt',
              star_result: 'Pipeline failures: weekly → quarterly',
              added_keywords: ['dbt', 'SQL'],
            },
          ],
        },
      ],
    },
    interview_prep: {
      questions: [
        {
          question_type: 'behavioral',
          question: 'Tell us about an analysis that changed what the product team built next.',
          context_or_reason: 'The role is framed around turning usage data into roadmap decisions.',
          star_guide:
            'Situation: onboarding retention was flat. Task: find where users dropped. Action: cohort dashboards by first-week behaviour. Result: checklist redesign, +9% week-4 retention.',
          sample_answer:
            'At Kettlebrook our week-4 retention had been flat for two quarters. I split new users into cohorts by what they did in their first three days and found that people who never finished setup on day 3 almost never came back. I brought the curve to the onboarding PM with one recommendation: shorten the checklist. They shipped it, and week-4 retention rose 9% over the next cohort.',
        },
        {
          question_type: 'behavioral',
          question: 'Describe a time you had to tell a senior stakeholder their idea was not supported by the data.',
          context_or_reason: 'Executive storytelling is listed but not evidenced in your resume.',
          star_guide:
            'Pick a concrete disagreement, show how you framed the evidence, and end with the decision that was made — even if it went against you.',
          sample_answer:
            'Our CEO wanted to remove the monthly plan. I ran the numbers on churn by plan type and showed that monthly users converted to annual at 18% within six months. I presented it as one chart and one question — "are we willing to lose this path?" — and we kept the plan with a stronger annual upsell instead.',
        },
        {
          question_type: 'technical',
          question: 'How would you decide whether a 2% lift in an A/B test is real?',
          context_or_reason: 'Experimentation is a core requirement and appears in your strongest bullet.',
          star_guide:
            'Walk through power and sample size before the test, the metric definition, significance and confidence intervals, and novelty or seasonality checks after.',
          sample_answer:
            'I start before launch: the minimum detectable effect and sample size tell me whether 2% was even detectable. After the test I look at the confidence interval rather than just the p-value, check sample-ratio mismatch, and segment by new versus returning users to rule out a novelty effect. If the interval crosses zero, I call it inconclusive rather than a win.',
        },
        {
          question_type: 'technical',
          question: 'Write the SQL to compute 30-day retention by signup week.',
          context_or_reason: 'Retention modeling is a listed requirement that is missing from your resume.',
          star_guide:
            'Talk through the cohort definition, the activity table join, and how you handle users who signed up less than 30 days ago.',
          sample_answer:
            'I would build a signup cohort CTE truncated to week, left-join activity events where the event date falls between day 30 and 37 after signup, and divide retained users by cohort size — excluding cohorts younger than 37 days so the last weeks are not artificially low.',
        },
        {
          question_type: 'gap_focused',
          question: 'You have used BigQuery. How quickly could you be productive in Snowflake?',
          context_or_reason: 'Snowflake is preferred and does not appear on your resume.',
          star_guide:
            'Acknowledge the gap, show what transfers (SQL dialect, dbt, warehouse cost thinking), and name a concrete ramp plan.',
          sample_answer:
            'Most of my work is in dbt, which abstracts most warehouse differences. The things I would learn in week one are Snowflake-specific: warehouses and credit usage, time travel, and semi-structured data functions. I have already worked through their free trial with our dbt project to check the dialect differences.',
        },
        {
          question_type: 'gap_focused',
          question: 'When an experiment is not possible, how do you estimate the impact of a feature?',
          context_or_reason: 'Causal inference is required and is the largest gap in your skill profile.',
          star_guide:
            'Name one method you would actually use (difference-in-differences, synthetic control, regression discontinuity) and its key assumption.',
          sample_answer:
            'For a feature released to one region first, I would use difference-in-differences against a comparable region, checking that the two trended in parallel before launch. If they did not, I would say so and treat the result as directional rather than causal.',
        },
      ],
    },
  },
};

// The real backend's 5-agent pipeline, in the order it actually runs.
// Stages 2 and 3 each run two agents in parallel (see backend/app/agents/pipeline.py).
export const PIPELINE = [
  { id: 'parse', stage: 1, label: 'Reading your resume', agent: 'Resume parser' },
  { id: 'ats', stage: 2, label: 'Scoring against the job', agent: 'ATS scoring' },
  { id: 'gap', stage: 2, label: 'Finding skill gaps', agent: 'Skill gap analysis' },
  { id: 'rewrite', stage: 3, label: 'Rewriting bullets', agent: 'STAR rewriter' },
  { id: 'interview', stage: 3, label: 'Writing interview questions', agent: 'Interview prep' },
];

// Canned coach replies so the chat prototype never calls the real API.
export const COACH_SUGGESTIONS = [
  'What should I fix first?',
  'How do I talk about Snowflake if I only used BigQuery?',
  'Draft a two-line cover note',
];

export function coachReply(message) {
  const m = message.toLowerCase();
  if (m.includes('snowflake') || m.includes('bigquery')) {
    return 'Put the category first and the tool second. In your skills line, write **Cloud warehouses: BigQuery (3 yrs), Snowflake (working knowledge)** — only if you have actually tried it. In the interview, say what transfers: dbt models, cost-aware SQL, partitioning.';
  }
  if (m.includes('cover') || m.includes('note')) {
    return 'Here is a start:\n\n"I turn product usage into roadmap decisions — most recently a cohort analysis at Kettlebrook that lifted week-4 retention by 9%. Fieldnote\'s focus on teacher collaboration is exactly the kind of retention problem I want to work on next."';
  }
  return 'Fix keyword coverage first — it is costing you the most points. In order:\n\n1. Replace your pricing-test bullet with the rewritten version; it adds **experimentation platform**.\n2. Add **retention** language to the onboarding dashboard bullet.\n3. Add Amplitude only if you have used it; otherwise leave the gap and prepare the interview answer.';
}
