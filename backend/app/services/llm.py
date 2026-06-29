from openai import AsyncOpenAI

# from app.core.config import settings

# _client = AsyncOpenAI(api_key=settings.openai_api_key)


# async def generate(messages: list[dict]) -> str:
#     """
#     Send a prompt to the LLM and return the text response.
    
#     Keeping this as a thin wrapper means you can swap GPT for Claude
#     or a local model by changing just this file.
#     """
#     response = await _client.chat.completions.create(
#         model=settings.llm_model,
#         messages=messages,
#         temperature=0,        # deterministic — we want factual answers, not creativity
#         max_tokens=1024,
#     )
#     return response.choices[0].message.content
# from openai import AsyncOpenAI

# Groq uses OpenAI-compatible API
_client = AsyncOpenAI(
    api_key="",
    base_url="https://api.groq.com/openai/v1"
)

async def generate(messages: list[dict]) -> str:
    response = await _client.chat.completions.create(
        model="llama-3.1-8b-instant",   # free on Groq
        messages=messages,
        temperature=0,
        max_tokens=1024,
    )
    return response.choices[0].message.content