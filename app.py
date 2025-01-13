from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import logging
import sys
import json
import numpy as np
import spacy
import groq
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for specific routes and origins
CORS(app, resources={
    r"/api/*": {"origins": "http://localhost"}
})

# Configure logging
def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Set up file handler with rotation
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=1024 * 1024,  # 1MB
        backupCount=10
    )
    
    # Define log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # Add handlers to app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    
    # Also log to console in development
    if app.debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

setup_logger()

# Initialize Groq client
groq_client = groq.Client(api_key=os.getenv('GROQ_API_KEY'))

# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_md")
    app.logger.info("Successfully loaded SpaCy model")
except Exception as e:
    app.logger.error(f"Failed to load SpaCy model: {str(e)}")
    sys.exit(1)

# Middleware for request logging
def log_request():
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Log request details
            app.logger.info(f"Request: {request.method} {request.path}")
            app.logger.info(f"Headers: {dict(request.headers)}")
            app.logger.info(f"Body: {request.get_json(silent=True)}")
            
            # Execute route handler
            response = f(*args, **kwargs)
            
            # Log response
            app.logger.info(f"Response: {response.get_json()}")
            return response
        return decorated_function
    return decorator

def compute_similarity(user_answer, correct_answer):
    try:
        # Generate spacy docs
        user_doc = nlp(user_answer)
        correct_doc = nlp(correct_answer)

        # Check if either text has no vector
        if user_doc.vector_norm == 0 or correct_doc.vector_norm == 0:
            return 0

        # Compute cosine similarity
        cosine_similarity = np.dot(user_doc.vector, correct_doc.vector) / (
            np.linalg.norm(user_doc.vector) * np.linalg.norm(correct_doc.vector)
        )

        # Convert to 0-100 scale
        rating = int((cosine_similarity + 1) * 50)
        return max(0, min(100, rating))
    except Exception as e:
        app.logger.error(f"Error in compute_similarity: {str(e)}")
        raise
        
@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Flask App!"}), 200
    
@app.route('/health', methods=['GET'])
@log_request()
def health_check():
    return jsonify({"status": "OK"})

@app.route('/api/groq-rate', methods=['POST'])
@log_request()
def groq_rate():
    try:
        data = request.get_json()
        user_answer = data.get('userAnswer')
        correct_answer = data.get('correctAnswer')

        if not user_answer or not correct_answer:
            return jsonify({
                "error": "Missing required fields",
                "details": {"userAnswer": bool(user_answer), "correctAnswer": bool(correct_answer)}
            }), 400

        # Call Groq API
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI who has a multi-dimensional vector representation of all the words and terms in the English language. Rate the answer from 0 to 100, where 0 means completely unrelated and 100 means exact match. Only provide the rating as an integer."
                },
                {
                    "role": "user",
                    "content": f"Rate the following answer from 0 to 100:\nCorrect Answer: {correct_answer}\nUser Answer: {user_answer}. Only respond with a number between 0 and 100."
                }
            ],
            model="llama3-8b-8192",
        )

        rating = int(response.choices[0].message.content)
        if not (0 <= rating <= 100):
            raise ValueError(f"Invalid rating: {rating}")

        return jsonify({"rating": rating})

    except Exception as e:
        app.logger.error(f"Error in groq_rate: {str(e)}")
        return jsonify({
            "error": "Failed to rate the answer",
            "details": str(e)
        }), 500

@app.route('/api/spacy-rate', methods=['POST'])
@log_request()
def spacy_rate():
    try:
        data = request.get_json()
        user_answer = data.get('userAnswer')
        correct_answer = data.get('correctAnswer')

        if not user_answer or not correct_answer:
            return jsonify({
                "error": "Missing required fields",
                "details": {"userAnswer": bool(user_answer), "correctAnswer": bool(correct_answer)}
            }), 400

        rating = compute_similarity(user_answer, correct_answer)
        return jsonify({"rating": rating})

    except Exception as e:
        app.logger.error(f"Error in spacy_rate: {str(e)}")
        return jsonify({
            "error": "Failed to rate the answer",
            "details": str(e),
            "traceback": str(e.__traceback__)
        }), 500

# Error handling
@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"Unhandled error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "details": str(error)
    }), 500

port = int(os.getenv('PORT', 10000))
