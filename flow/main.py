from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os
import re
import time
from requests.exceptions import RequestException
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Prompt template
prompt = PromptTemplate(
    template="""You are a helpful assistant that answers questions based on a YouTube video transcript.

      CONTENT GUIDELINES:
      - Answer based on the provided transcript context
      - Look for related concepts, similar topics, or broader principles that connect to the question
      - If the transcript discusses the topic directly, explain it based on what's mentioned
      - If not directly discussed, try to relate it to concepts in the transcript
      - Always respond in English, even if the transcript is in another language - translate the relevant information
      - Be helpful, clear, and thorough in your explanations
      - Avoid saying "out of context" - instead, focus on connecting the question to what's available
      - Never start with filler phrases like "Sure!", "Great question!", "Certainly!" — go straight to the answer

      MARKDOWN FORMATTING RULES (follow strictly):

      1. HEADINGS — Use ## or ### only when:
         - Answer has 4+ distinct sections or points
         - Never use headings for short 1-3 sentence answers

      2. BOLD — Use **bold** only for:
         - Key terms being defined or introduced
         - The single most critical fact in a paragraph
         - Max 2-3 bolds per paragraph, never bold full sentences

      3. BULLET POINTS — Use only when:
         - Listing 3 or more distinct items
         - Items have no specific order or sequence
         - Never use bullets for a single point

      4. NUMBERED LIST — Use when:
         - Order or sequence matters
         - Explaining step-by-step processes

      5. PLAIN PARAGRAPH — Use for:
         - Simple factual or conversational answers
         - Answers under 3 sentences — no bullets, no headings, just clean prose

      6. CODE — Use backticks only for actual code, commands, or technical syntax

      7. LENGTH:
         - Simple question = 1-3 sentence plain paragraph
         - Detailed question = structured with headings + lists
         - Never pad or over-explain

      EXAMPLES:

      Q: "What is this video about?"
      A: This video covers **machine learning** fundamentals, explaining how models learn patterns from data and use them to make predictions.

      Q: "What are the main steps explained in the video?"
      A:
      ## Steps Covered in the Video
      1. **Data Collection** — Gathering raw data from various sources
      2. **Preprocessing** — Cleaning and normalizing the data
      3. **Model Training** — Feeding data through the algorithm
      4. **Evaluation** — Measuring accuracy on unseen data

      Q: "Who is the speaker?"
      A: The speaker is **Andrew Ng**, a well-known AI researcher and educator.

      Transcript Context:
      {context}

      Question: {question}

      Answer:""",
    input_variables=["context", "question"]
)

# Store video sessions (video_id -> retriever)
video_sessions = {}


def get_transcript_with_api(video_id: str) -> str:
    """Fetch transcript using youtube-transcript-api."""
    try:
        logger.info(f"Attempting to get transcript for {video_id}...")
        
        ytt_api = YouTubeTranscriptApi()
        try:
            fetched_transcript = ytt_api.fetch(video_id)
        except Exception as e:
            logger.warning(f"Default fetch failed: {e}. Trying first available transcript...")
            available_transcripts = list(ytt_api.list(video_id))
            if not available_transcripts:
                raise ValueError("No transcripts available for this video.")
            fetched_transcript = available_transcripts[0].fetch()
            
        transcript_text = " ".join(snippet.text for snippet in fetched_transcript)
        return transcript_text
        
    except TranscriptsDisabled:
        logger.error("Transcripts are disabled for this video")
        raise
    except Exception as e:
        logger.error(f"Error getting transcript: {str(e)}")
        raise


def extract_video_id(url: str) -> str:
    """Extract video ID from YouTube URL or return as-is if already an ID."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.info(f"🔍 Pattern matched, extracted ID: {video_id}")
            return video_id
    logger.warning(f"⚠️ No pattern matched for URL: {url}")
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
    logger.info(f"📥 Received URL: {request.video_url}")
    video_id = extract_video_id(request.video_url)
    logger.info(f"✂️ Extracted video_id: {video_id}")
    
    # Check if already loaded
    if video_id in video_sessions:
        logger.info(f"⚡ Video {video_id} already loaded")
        return LoadVideoResponse(
            success=True,
            message="Video already loaded!",
            video_id=video_id
        )
    
    try:
        # Fetch transcript using youtube-transcript-api
        logger.info(f"Loading video {video_id}...")
        transcript = get_transcript_with_api(video_id)
        logger.info(f"Got transcript of {len(transcript)} characters")
        
        if not transcript:
            raise HTTPException(status_code=400, detail="No transcripts available for this video.")
    except HTTPException:
        raise
    except TranscriptsDisabled:
        logger.error(f"Transcripts disabled for video {video_id}")
        raise HTTPException(status_code=400, detail="No captions available for this video.")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Transcript fetch error: {error_msg}")
        # Return the actual error so user can see what YouTube is saying
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Split text into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript)
    
    # Create vectorstore with retry logic
    for attempt in range(3):
        try:
            logger.info(f"Embedding attempt {attempt + 1} for video {video_id}")
            vectorstore = FAISS.from_texts(chunks, embeddings)
            retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            video_sessions[video_id] = retriever
            logger.info(f"✅ Successfully loaded video {video_id}")
            return LoadVideoResponse(
                success=True,
                message="Video loaded successfully!",
                video_id=video_id
            )
        except (RequestException, ConnectionError, TimeoutError) as e:
            error_msg = str(e)
            logger.warning(f"Embedding error (attempt {attempt + 1}): {error_msg}")
            
            if "429" in error_msg or "quota" in error_msg.lower():
                raise HTTPException(
                    status_code=429, 
                    detail="HuggingFace API quota exceeded. Upgrade your plan or try tomorrow."
                )
            
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise HTTPException(status_code=500, detail="Failed to create embeddings. Check your API tokens.")
    
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
            logger.info(f"Processing question (attempt {attempt + 1}): {request.question[:50]}...")
            docs = retriever.invoke(request.question)
            context = "\n".join([doc.page_content for doc in docs])
            final_prompt = prompt.invoke({"context": context, "question": request.question})
            answer = llm.invoke(final_prompt)
            logger.info(f"✅ Answer generated successfully")
            return AskResponse(answer=answer.content)
        except (RequestException, ConnectionError, TimeoutError) as e:
            error_msg = str(e)
            logger.warning(f"Network error (attempt {attempt + 1}): {error_msg}")
            
            if "429" in error_msg or "rate" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail="⚠️ API rate limit hit. You're sending too many requests. Wait a few minutes."
                )
            
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise HTTPException(status_code=500, detail="Network error. Please try again.")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error processing question: {error_msg}")
            
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                raise HTTPException(status_code=429, detail="⚠️ Groq API rate limit exceeded. Try again soon.")
            
            raise HTTPException(status_code=500, detail=f"Error: {error_msg[:200]}")
    
    raise HTTPException(status_code=500, detail="Unexpected error. Please try again.")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)