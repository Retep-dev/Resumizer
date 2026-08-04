from typing import List, Dict
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from app.config import settings
from app.services.rag_service import get_vectorstore_for_session


CAREER_COACH_SYSTEM_PROMPT = """You are an Elite AI Career Coach & Resume Strategist.
Your mission is to help the candidate land their target job.

Context from Candidate's Resume & Job Description:
--------------------------------------------------
{retrieved_context}
--------------------------------------------------

Guidelines:
1. Provide actionable, concise, encouraging, and highly specific career advice.
2. Refer directly to facts from the candidate's resume and requirements from the target job description.
3. Help the candidate with interview preparation, salary negotiation strategies, skill gap remediation, and networking approaches.
4. Keep responses structured with clear bullet points where applicable.
"""


async def chat_with_career_coach(
    session_id: str,
    user_message: str,
    chat_history: List[Dict[str, str]] = None
) -> str:
    """RAG-powered conversational Career Coach agent."""
    if chat_history is None:
        chat_history = []

    # Retrieve context from ChromaDB
    try:
        vectorstore = get_vectorstore_for_session(session_id)
        docs = vectorstore.similarity_search(user_message, k=4)
        retrieved_context = "\n\n".join([f"[{d.metadata.get('source', 'doc')}]: {d.page_content}" for d in docs])
    except Exception:
        retrieved_context = "No specific document context found."

    llm = ChatNVIDIA(
        model=settings.NVIDIA_MODEL_NAME,
        nvidia_api_key=settings.NVIDIA_API_KEY,
        temperature=0.4,
        timeout=180
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", CAREER_COACH_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{user_message}")
    ])

    formatted_history = []
    for msg in chat_history:
        if msg.get("role") == "user":
            formatted_history.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            formatted_history.append(AIMessage(content=msg.get("content", "")))

    chain = prompt | llm
    response = await chain.ainvoke({
        "retrieved_context": retrieved_context,
        "history": formatted_history,
        "user_message": user_message
    })

    return response.content
