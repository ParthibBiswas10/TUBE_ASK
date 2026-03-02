from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEndpointEmbeddings
import os
import re
import time
from requests.exceptions import RequestException

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def extract_video_id(url):
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Already a video ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url  # Return as-is if no match

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

video_url = "https://youtu.be/8ekTeZD_lNY?si=-OgOL931zX-mBJeH"  # Paste full URL or video ID
video_id = extract_video_id(video_url)
try:
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)
    transcript = " ".join(snippet.text for snippet in fetched_transcript)

except TranscriptsDisabled:
    print("No captions available for this video.")

splitter=RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
chunks=splitter.split_text(transcript)

# Create vectorstore with retry logic
for attempt in range(3):
    try:
        print("Creating embeddings...")
        vectorstore=FAISS.from_texts(chunks,embeddings)
        retriever=vectorstore.as_retriever(search_kwargs={"k":3})
        print("Ready!")
        break
    except (RequestException, ConnectionError, TimeoutError) as e:
        if attempt < 2:
            wait_time = 2 ** attempt
            print(f"Network error during setup, retrying in {wait_time}s...")
            time.sleep(wait_time)
        else:
            print("Failed to create embeddings! Check your connection.")
            exit(1)

#print(retriever.invoke("What is the video about?"))
prompt=PromptTemplate(
    template=""""You are a helpful assistant.
      Answer ONLY from the provided transcript context.
      If the context is insufficient, just say the question is out of context so,you can't answer.

      {context}
      Question: {question}""",
    input_variables=["context","question"]
)

print("\n YouTube Q&A Chat - Type 'quit' or 'exit' to end the conversation\n")

def ask_with_retry(question, max_retries=3):
    """Ask a question with retry logic for network errors."""
    for attempt in range(max_retries):
        try:
            docs = retriever.invoke(question)
            context = "\n".join([doc.page_content for doc in docs])
            final_prompt = prompt.invoke({"context": context, "question": question})
            answer = llm.invoke(final_prompt)
            return answer.content
        except (RequestException, ConnectionError, TimeoutError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Network error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                return f"Error: Network issue after {max_retries} attempts. Please check your connection and try again."
        except Exception as e:
            return f"Error: {str(e)}"

while True:
    question = input("You: ").strip()
    
    if not question:
        continue
    
    if question.lower() in ['quit', 'exit', 'q']:
        print("Goodbye!")
        break
    
    response = ask_with_retry(question)
    print(f"\nAssistant: {response}\n")
