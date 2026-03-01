from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

llm = ChatGroq(
    model="llama-3.1-8b-instant", 
    api_key=os.getenv("GROQ_API_KEY")
)

embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

'''rsult=llm.invoke("WHO IS MESSI?")
print(rsult.content)

result_embedding = embeddings.embed_query(rsult.content)
print(result_embedding)'''

video_id = "Gfr50f6ZBvo" # only the ID, not full URL
try:
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)
    transcript = " ".join(snippet.text for snippet in fetched_transcript)
    print(transcript)

except TranscriptsDisabled:
    print("No captions available for this video.")

splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
chunks=splitter.split_text(transcript)
vectorstore=FAISS.from_texts(chunks,embeddings)
retriever=vectorstore.as_retriever(search_kwargs={"k":3})
print(retriever.invoke("What is the video about?"))