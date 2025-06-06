import logging
import os
from datetime import datetime
from pymongo import MongoClient
from evaluate_answers import save_evaluation, evaluate_answer_hybrid
import pandas as pd
import random
from dotenv import load_dotenv
from fastapi import HTTPException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Load environment variables from .env file
load_dotenv()

# MongoDB connection
def get_db():
    """
    Connect to MongoDB and return the database object.
    """
    try:
        # MongoDB Connection
        MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        client = MongoClient(MONGO_URI)
        db = client["evaluation_db"]
        logging.info("Connected to MongoDB successfully.")
        return db
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# Global Database Connection
db = get_db()
collection = db["student_assigned_questions"]

# Load CSV **Globally**
FILE_PATH = "Notes/cleaned_question_and_answer.csv"
try:
    df = pd.read_csv(FILE_PATH)
    # Ensure required columns exist
    if not {"Question", "Answer", "Type"}.issubset(df.columns):
        raise ValueError("Dataset must contain 'Question', 'Answer', and 'Type' columns")

    logging.info("CSV file loaded successfully.")

except Exception as e:
    logging.error(f"Error loading CSV file: {e}", exc_info=True)
    raise HTTPException(status_code=400, detail=str(e))

# Select One Random Structured & Essay Question
def get_one_sample_question():
    """
    Selects one random structured and one random essay-type question with answers from a DataFrame.
    """
    try:
        if df is None:
            raise ValueError("Dataset is not loaded. Please check the CSV file.")

        # Select one random structured question
        structured_question = df[df["Type"] == "Structure"].sample(n=1, random_state=random.randint(1, 10000))

        # Select one random essay question
        essay_question = df[df["Type"] == "Essay"].sample(n=1, random_state=random.randint(1, 10000))

        # Create a dictionary with the selected questions and answers
        selected_questions = {
            "Structured_Question": {
                "Question": structured_question.iloc[0]["Question"],
                "Answer": structured_question.iloc[0]["Answer"]
            },
            "Essay_Question": {
                "Question": essay_question.iloc[0]["Question"],
                "Answer": essay_question.iloc[0]["Answer"]
            }
        }
        return selected_questions

    except Exception as e:
        logging.error(f"Error selecting sample questions: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

# Select Questions Per Student
def select_questions_per_student(student_id):
    """
    Select one structured and one essay question per student,
    store them in MongoDB, and return the assigned questions.
    """
    # Get one structured and one essay question
    selected_questions = get_one_sample_question()
    if not selected_questions:
        return None
    
    selected_questions["Student_ID"] = student_id
    selected_questions["Assigned_Date"] = datetime.utcnow()

    # Insert into MongoDB
    collection.insert_one(selected_questions)

    logging.info(f"Questions assigned to Student ID {student_id} and stored in MongoDB.")
    return selected_questions

def get_questions_by_student_id(student_id):
    """
    Fetches the assigned structured and essay questions for a given student ID from MongoDB.
    """
    try:
        # Query MongoDB to find the assigned questions for the student
        record = collection.find_one({"Student_ID": student_id}, {"_id": 0})

        if not record:
            select_questions_per_student(student_id)
            record = collection.find_one({"Student_ID": student_id}, {"_id": 0})
            # return {"error": f"No questions found for Student ID {student_id}"}

        # Check if the required fields exist
        if "Structured_Question" not in record or "Essay_Question" not in record:
            return {"error": f"No valid questions found for Student ID {student_id}"}

        return {
            "Structured_Question": record["Structured_Question"],
            "Essay_Question": record["Essay_Question"],
            "Assigned_Date": record.get("Assigned_Date")
        }

    except Exception as e:
        logging.error(f"Error fetching questions for Student ID {student_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def replace_question_for_student(student_id, question_type):
    """
    Replaces the previous structured or essay-type question for a specific student ID
    with a new randomly selected question from the dataset and updates it in MongoDB.
    """
    try:
        if df is None:
            raise ValueError("Dataset is not loaded. Please check the CSV file.")

        # Ensure the question type is valid
        if question_type.lower() not in ["structured", "essay"]:
            return {"error": "Invalid question type. Choose 'structured' or 'essay'."}

        # Fetch the existing student record from MongoDB
        record = collection.find_one({"Student_ID": student_id})

        if not record:
            raise HTTPException(status_code=404, detail=f"No questions found for Student ID {student_id}")

        # Select a new question and answer from the dataset
        if question_type.lower() == "structured":
            new_question_row = df[df["Type"] == "Structure"].sample(n=1, random_state=random.randint(1, 10000))
        else:
            new_question_row = df[df["Type"] == "Essay"].sample(n=1, random_state=random.randint(1, 10000))

        new_question = new_question_row.iloc[0]["Question"]
        new_answer = new_question_row.iloc[0]["Answer"]

        # Define the update key based on question type
        update_field = "Structured_Question" if question_type.lower() == "structured" else "Essay_Question"

        # Prepare update data
        update_data = {
            f"{update_field}.Question": new_question,
            f"{update_field}.Answer": new_answer,
            "Updated_At": datetime.utcnow()
        }

        # Update the question in MongoDB
        collection.update_one({"Student_ID": student_id}, {"$set": update_data})

        logging.info(f"{question_type.capitalize()} question replaced for Student ID {student_id}.")
        return {
            "message": f"{question_type.capitalize()} question successfully replaced for Student ID {student_id}.",
            "Student_ID": student_id,
            "Updated_Question": new_question,
            "Updated_Answer": new_answer
        }

    except Exception as e:
        logging.error(f"Error replacing {question_type} question for Student ID {student_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def compare_with_passpaper_answer (student_id, question, user_answer, question_type):
    """
    Evaluates the user's answer against the assigned pass paper answer based on the question type.
    """
    logging.info(f"Evaluating user's answer. Question: '{question}', Question Type: '{question_type}'")
    try:
        # Query MongoDB to find the assigned questions for the student
        record = collection.find_one({"Student_ID": student_id}, {"_id": 0})

        if not record:
            raise HTTPException(status_code=404, detail=f"No questions found for Student ID {student_id}")

        # Fetch the correct model answer based on the question type
        if question_type.lower() == "structured":
            pass_paper_answer = record.get("Structured_Question", {}).get("Answer", None)
        elif question_type.lower() == "essay":
            pass_paper_answer = record.get("Essay_Question", {}).get("Answer", None)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid question type: {question_type}")

        if not pass_paper_answer:
            raise HTTPException(status_code=404, detail=f"Pass paper answer not found for {question_type} question.")

        # Evaluate the user's answer against the saved answer
        logging.info("Evaluating user's answer against the pass paper answer...")
        result = evaluate_answer_hybrid(user_answer, pass_paper_answer, question_type.lower())
        logging.info("Evaluation completed successfully.")

        # Save evaluation result
        save_evaluation(student_id, question, question_type, user_answer, pass_paper_answer, result)

        replace_question_for_student(student_id, question_type)

        return {
            "student_id": student_id,
            "question": question,
            "question_type": question_type,
            "user_answer": user_answer,
            "model_answer": pass_paper_answer,
            "evaluation_result": result
        }
    except Exception as e:
        logging.error(f"Error occurred while evaluating user's answer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Run Tests
if __name__ == "__main__":
    STUDENT_ID = "1234"  # Example Student ID

    assigned_questions = compare_with_passpaper_answer(STUDENT_ID, "Indicate the type of fertilization in the Earthworm", "Mitochondria.", "structured")
    print(assigned_questions)
