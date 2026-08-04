from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.schemas.resume import ResumeSchema


PARSER_SYSTEM_PROMPT = """You are an expert Resume Parser AI Agent.
Your job is to read raw text extracted from a resume and parse it into a clean, structured JSON object according to the provided schema.

Rules:
1. Extract candidate's full name, email, phone, location, LinkedIn, GitHub.
2. Group skills into technical_skills, soft_skills, and tools_and_frameworks.
3. Parse work experience accurately including company name, job title, location, dates, and bullet points.
4. Parse education degrees, institutions, and graduation years.
5. Parse notable projects and certifications.
6. Do not invent missing facts, but structure all present data cleanly.
"""


def get_resume_parser_agent():
    """Initializes and returns the Resume Parser Agent with structured output."""
    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.1,
        timeout=180
    )

    
    prompt = ChatPromptTemplate.from_messages([
        ("system", PARSER_SYSTEM_PROMPT),
        ("human", "Raw Resume Text:\n\n{raw_resume_text}")
    ])
    
    # LangChain LCEL chain with structured output
    structured_llm = llm.with_structured_output(ResumeSchema)
    chain = prompt | structured_llm
    return chain


async def parse_resume_text(raw_resume_text: str) -> ResumeSchema:
    """Invokes the Resume Parser Agent to parse raw resume text into ResumeSchema."""
    agent = get_resume_parser_agent()
    truncated_text = raw_resume_text[:12000]
    result = await agent.ainvoke({"raw_resume_text": truncated_text})
    return result
