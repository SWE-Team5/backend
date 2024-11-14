# chatbot_logic.py

from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts.chat import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)

def create_chatbot(vectorstore):
    # 시스템 메시지 템플릿 정의
    system_message = """
당신은 학교 생활에 대한 정보를 제공하는 도움되는 어시스턴트입니다.
답변을 제공할 때는 아래의 지침을 따르세요:
- 주어진 문맥(context)에서만 정보를 찾아 답변하세요.
- 모르는 내용이라면 솔직하게 모른다고 답하세요.
- 허위 정보를 만들어내지 마세요.
- 필요하다면 관련 공지사항의 링크를 제공하세요.
"""

    # 프롬프트 템플릿 정의
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_message),
        HumanMessagePromptTemplate.from_template("""
{context}

질문: {question}

답변:
""")
    ])

    # 언어 모델 생성
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",  # 또는 사용 가능한 다른 모델
        temperature=0.0
    )

    # RetrievalQA 체인 생성
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        chain_type_kwargs={"prompt": prompt}
    )

    return qa_chain