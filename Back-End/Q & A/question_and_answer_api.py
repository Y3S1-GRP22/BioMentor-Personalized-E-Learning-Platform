import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from generate_answers import generate_structured_answer, generate_essay_answer
from evaluate_answers import evaluate_user_answer
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL for better security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Define a generate answer request schema for the API
class QuestionRequest(BaseModel):
    question: str
    type: str 

@app.post("/generate-answer")
def generate_answer(request: QuestionRequest):
    """
    API endpoint to generate an answer based on the question type.
    """
    logging.info(f"Received request to generate answer: {request.dict()}")
    question_type = request.type.lower()  # Normalize type to lowercase
    
    try:
        if question_type == "structured":
            # Generate a structured answer
            answer = generate_structured_answer(
                query=request.question,
                k=3,  # Default k for structured
                max_words=50  # Default max words for structured
            )
            logging.info("Structured answer generated successfully.")
            return {"type": "structured", "answer": answer}
        else:
            # Invalid type provided
            logging.error("Invalid question type provided.")
            raise HTTPException(status_code=400, detail="Invalid question type. Use 'structured' or 'essay'.")
    except Exception as e:
        logging.error(f"Error while generating answer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while generating the answer.")

@app.post("/evaluate-answer")
def evaluate_answer(request: EvaluationRequest):
    """
    API endpoint to evaluate a user's answer based on the question type.
    """
    logging.info(f"Received request to evaluate answer: {request.dict()}")
    try:
        # Call the `evaluate_user_answer` function
        result = evaluate_user_answer(
            question=request.question,
            user_answer=request.user_answer,
            question_type=request.question_type
        )
        logging.info("User answer evaluated successfully.")
        return {
            "status": "success",
            "question": result["question"],
            "question_type": result["question_type"],
            "user_answer": result["user_answer"],
            "model_answer": result["model_answer"],
            "evaluation_result": result["evaluation_result"],
        }
    except ValueError as e:
        # Handle invalid question type or other validation errors
        logging.error(f"Validation error while evaluating answer: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Handle unexpected errors
        logging.error(f"Unexpected error while evaluating answer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred: " + str(e))


@app.get("/")
def root():
    """
    Health check endpoint to ensure the API is running.
    """
    logging.info("Health check endpoint accessed.")
    return {"message": "Question and Answer API is running!"}
