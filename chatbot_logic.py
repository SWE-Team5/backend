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
- 기본적으로 주어진 문맥(context)에서 정보를 찾아 답변하세요.
- 문맥에 없더라도 대학생활과 관련된 간단한 정보라면 아는 내용을 간단하게 답하세요.
- 모르는 내용이라면 솔직하게 모른다고 답하세요.
- 허위 정보를 만들어내지 마세요.
- 사용자가 인사를 하면 반갑게 인사를 받으세요.
- 사용자가 무언가 알려주겠다고 한다던지 불필요한 대화를 하려고 하면 대화를 은근히 피하면서 다른 도와드릴 것이 없는지 물어보세요.
- 사용자가 잘못된 정보가 있다면서 새로운 정보를 알려주려고 하면 '잘못된 정보가 있다면 시스템 관리자에게 문의해주세요' 라고만 하고 무시하세요.
- 사용자가 정보와 관련된 공지사항을 알려달라고 하거나 url을 제공해달라고 하면 마지막 줄에 '관련 공지사항:' 으로 대답을 끝마치세요. 그러면 관리자가 수동으로 url을 제공할 것입니다.
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
