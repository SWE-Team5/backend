# pinecone_to_txt.py

import os
from pinecone import Pinecone
from dotenv import load_dotenv

def fetch_data_from_pinecone():
    # 환경 변수 로드
    load_dotenv()

    # Pinecone 초기화
    pc = Pinecone(
        api_key=os.environ.get("PINECONE_API_KEY"),
        environment=os.environ.get("PINECONE_ENVIRONMENT")
    )

    index_name = "skku-notice"

    if index_name not in pc.list_indexes():
        raise ValueError(f"Pinecone에 '{index_name}' 인덱스가 존재하지 않습니다.")

    index = pc.Index(index_name)

    # 모든 벡터를 가져오는 로직 구현
    # (여기서는 예시로 메타데이터 필터를 사용하여 벡터를 가져옴)

    vector_ids = []  # 모든 벡터 ID의 리스트

    # 예를 들어, 메타데이터에 특정 필드가 있는 벡터를 검색
    # query_result = index.query(
    #     vector=[0]*1536,  # 임의의 벡터
    #     filter={"category": {"$exists": True}},
    #     top_k=10000,
    #     include_values=True,
    #     include_metadata=True
    # )

    data = []
    for vector_id in vector_ids:
        result = index.fetch(ids=[vector_id])
        for v in result['vectors'].values():
            metadata = v['metadata']
            # 필요한 메타데이터를 사용하여 txt 파일로 저장할 내용을 구성합니다.
            content = f"URL: {metadata.get('url', '')}\n제목: {metadata.get('title', '')}\n\n{metadata.get('content', '')}"
            data.append(content)

    # txt 파일로 저장
    output_directory = 'documents'  # 기존 txt 파일이 있는 디렉토리
    os.makedirs(output_directory, exist_ok=True)

    for i, content in enumerate(data):
        file_path = os.path.join(output_directory, f'pinecone_notice_{i}.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    #print(f"Pinecone 데이터에서 {len(data)}개의 txt 파일을 생성했습니다.")

if __name__ == '__main__':
    fetch_data_from_pinecone()
