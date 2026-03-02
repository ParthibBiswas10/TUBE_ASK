from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="YouTube Q&A API")

# CORS middleware for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "YouTube Q&A API is running. Use /load to load a video and /ask to ask questions."}


# Initialize LLM and embeddings
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

embeddings = HuggingFaceEndpointEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2",
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

# Prompt template
prompt = PromptTemplate(
    template="""You are a helpful assistant.
      Answer ONLY from the provided transcript context.
      If the context is insufficient, just say the question is out of context so, you can't answer.

      {context}
      Question: {question}""",
    input_variables=["context", "question"]
)

# Store video sessions (video_id -> retriever)
video_sessions = {}


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url


class LoadVideoRequest(BaseModel):
    video_url: str


class AskRequest(BaseModel):
    video_url: str
    question: str


class LoadVideoResponse(BaseModel):
    success: bool
    message: str
    video_id: str


class AskResponse(BaseModel):
    answer: str


@app.post("/load", response_model=LoadVideoResponse)
async def load_video(request: LoadVideoRequest):
    """Load a YouTube video and create embeddings from its transcript."""
    video_id = extract_video_id(request.video_url)
    
    # Check if already loaded
    if video_id in video_sessions:
        return LoadVideoResponse(
            success=True,
            message="Video already loaded!",
            video_id=video_id
        )
    
    try:
        # Fetch transcript with language fallback
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        
        fetched_transcript = None
        
        # Try to get English transcript first
        try:
            fetched_transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB']).fetch()
        except Exception:
            pass
        
        # If no English, try to get any transcript and translate to English
        if fetched_transcript is None:
            try:
                # Get any available transcript (prefer generated over manual for accuracy)
                available = list(transcript_list)
                if available:
                    transcript_obj = available[0]
                    # Try to translate to English if possible
                    try:
                        fetched_transcript = transcript_obj.translate('en').fetch()
                    except Exception:
                        # If translation fails, use original transcript
                        fetched_transcript = transcript_obj.fetch()
            except Exception:
                pass
        
        if fetched_transcript is None:
            raise HTTPException(status_code=400, detail="No transcripts available for this video.")
        
        transcript = " ".join(snippet.text for snippet in fetched_transcript)
    except HTTPException:
        raise
    except TranscriptsDisabled:
        raise HTTPException(status_code=400, detail="No captions available for this video.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch transcript: {str(e)}")
    
    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript)
    
    # Create vectorstore with retry logic
    for attempt in range(3):
        try:
            vectorstore = FAISS.from_texts(chunks, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            video_sessions[video_id] = retriever
            return LoadVideoResponse(
                success=True,
                message="Video loaded successfully!",
                video_id=video_id
            )
        except (RequestException, ConnectionError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise HTTPException(status_code=500, detail="Failed to create embeddings. Check your connection.")
    
    raise HTTPException(status_code=500, detail="Unexpected error during video loading.")


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """Ask a question about a loaded video."""
    video_id = extract_video_id(request.video_url)
    
    if video_id not in video_sessions:
        raise HTTPException(status_code=400, detail="Video not loaded. Please load the video first.")
    
    retriever = video_sessions[video_id]
    
    for attempt in range(3):
        try:
            docs = retriever.invoke(request.question)
            context = "\n".join([doc.page_content for doc in docs])
            final_prompt = prompt.invoke({"context": context, "question": request.question})
            answer = llm.invoke(final_prompt)
            return AskResponse(answer=answer.content)
        except (RequestException, ConnectionError, TimeoutError) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise HTTPException(status_code=500, detail="Network error. Please try again.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    raise HTTPException(status_code=500, detail="Unexpected error.")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
