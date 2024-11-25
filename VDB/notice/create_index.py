from pinecone import Pinecone, ServerlessSpec
import os

# for sentence-transformers/xlm-r-100langs-bert-base-nli-stsb

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

def update_index(index_name, dimension, metric):
    pc = Pinecone(api_key=PINECONE_API_KEY)

    pc.delete_index(index_name)

    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

update_index("skku-notice", 768, "cosine")