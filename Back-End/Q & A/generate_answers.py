import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import faiss
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# Load datasets
logging.info("Loading datasets...")
qa_df = pd.read_csv('cleaned_question_and_answer.csv', encoding='ISO-8859-1')
chunked_notes_df = pd.read_csv('cleaned_Notes.csv', encoding='ISO-8859-1')

# Load the embedding model and FAISS index
logging.info("Loading embedding model and FAISS index...")
embedder = SentenceTransformer('sentence-transformers/multi-qa-mpnet-base-dot-v1')
index = faiss.read_index('faiss_index.bin')

# Load the LLaMA model for text generation
logging.info("Loading text generation model...")
generator = pipeline("text-generation", model="D:/SLIIT/Research/Finetune - Structure and Essay/Merged_model")

def retrieve_similar_content(query, k=5):
    """
    Retrieve the top-k most similar content from the FAISS index.
    """
    logging.info(f"Retrieving top {k} similar content for query: '{query}'")
    try:
        query_embedding = embedder.encode([query]).astype('float32')
        distances, indices = index.search(query_embedding, k)
        results = []
        for idx in indices[0]:
            if idx < len(qa_df):
                results.append({
                    'type': 'Q&A',
                    'question': qa_df.iloc[idx]['Question'],
                    'answer': qa_df.iloc[idx]['Answer']
                })
            else:
                note_idx = idx - len(qa_df)
                results.append({
                    'type': 'Note',
                    'chunk': chunked_notes_df.iloc[note_idx]['Chunk']
                })
        logging.info(f"Retrieved {len(results)} items.")
        return results
    except Exception as e:
        logging.error(f"Error retrieving similar content: {e}", exc_info=True)
        raise

def construct_context_for_structured(query, k=3):
    """
    Construct context for structured questions. Only include concise Q&A pairs.
    """
    logging.info("Constructing context for structured question...")
    retrieved = retrieve_similar_content(query, k)
    context = [f"Q: {item['question']}\nA: {item['answer']}" for item in retrieved if item['type'] == 'Q&A']
    logging.debug(f"Structured context: {context}")
    return "\n".join(context[:3])

def construct_context_for_essay(query, k=5):
    """
    Construct context for essay questions. Include the most relevant Q&A pair first,
    followed by complementary Note chunks.
    """
    logging.info("Constructing context for essay question...")
    retrieved = retrieve_similar_content(query, k)
    context = []
    for item in retrieved:
        if item['type'] == 'Q&A' and query.lower() in item['question'].lower():
            context.append(f"Q: {item['question']}\nA: {item['answer']}")
            break
    context.extend([f"Note:\n{item['chunk']}" for item in retrieved if item['type'] == 'Note'])
    logging.debug(f"Essay context: {context}")
    return "\n".join(context[:5])

def generate_structured_answer(query, k=3, max_words=50):
    """
    Generate structured answers with concise and specific responses.
    """
    logging.info("Generating structured answer...")
    try:
        context = construct_context_for_structured(query, k)
        prompt = (
            f"Question: {query}\n\n"
            f"Context:\n{context}\n\n"
            f"Answer the question concisely and accurately in 1-2 sentences.\nAnswer:"
        )
        input_length = len(generator.tokenizer(prompt)['input_ids'])
        adjusted_max_length = input_length + max_words
        response = generator(prompt, max_length=adjusted_max_length, truncation=True, num_return_sequences=1)
        logging.info("Structured answer generated successfully.")
        return response[0]["generated_text"]
    except Exception as e:
        logging.error(f"Error generating structured answer: {e}", exc_info=True)
        raise

def generate_essay_answer(query, k=5, min_words=175, max_words=300):
    """
    Generate essay-style answers with a detailed explanation.
    """
    logging.info("Generating essay answer...")
    try:
        context = construct_context_for_essay(query, k)
        prompt = (
            f"Question: {query}\n\n"
            f"Context:\n{context}\n\n"
            f"Answer the question in detail, providing a well-reasoned and comprehensive explanation. "
            f"Ensure your response is at least {min_words} words long. Complete your answer and avoid repetition.\nAnswer:"
        )
        input_length = len(generator.tokenizer(prompt)['input_ids'])
        estimated_token_count = int(min_words * 0.75)
        adjusted_min_length = input_length + estimated_token_count
        adjusted_max_length = input_length + max_words
        response = generator(prompt, max_length=adjusted_max_length, min_length=adjusted_min_length,
                             temperature=0.7, top_p=0.85, top_k=40, repetition_penalty=1.8,
                             truncation=True, num_return_sequences=1)
        logging.info("Essay answer generated successfully.")
        return extract_answer_from_generated_text(response[0]["generated_text"])
    except Exception as e:
        logging.error(f"Error generating essay answer: {e}", exc_info=True)
        raise

def extract_answer_from_generated_text(generated_text):
    """
    Extract the answer part from the generated text.
    """
    if "Answer:" in generated_text:
        return generated_text.split("Answer:")[1].strip()
    return generated_text.strip()

if __name__ == "__main__":
    query = "What is the structure of DNA?"
    logging.info("Generating answers for example query...")
    try:
        structured_answer = generate_structured_answer(query, k=3, max_words=100)
        logging.info(f"Structured Answer: {structured_answer}")
    except Exception as e:
        logging.error("Failed to generate structured answer.", exc_info=True)
