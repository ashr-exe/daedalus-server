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
from datetime import datetime, timedelta
from functools import wraps
from flask_cors import CORS
from cryptography.fernet import Fernet
import jwt

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Security configurations
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    print("ERROR: JWT_SECRET_KEY environment variable is not set!")
    sys.exit(1)

ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    print("ERROR: ENCRYPTION_KEY environment variable is not set!")
    sys.exit(1)

# Initialize encryption
fernet = Fernet(ENCRYPTION_KEY.encode())

# Enable CORS with secure settings
ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "https://daedalus-ai1.web.app"
]

CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

# Configure logging
def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    file_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=1024 * 1024,
        backupCount=10
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    
    if app.debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        app.logger.addHandler(console_handler)

setup_logger()

# Initialize Groq client
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY environment variable is not set!")
    sys.exit(1)

groq_client = groq.Client(api_key=GROQ_API_KEY)

# Load SpaCy model
try:
    nlp = spacy.load("en_core_web_md")
    app.logger.info("Successfully loaded SpaCy model")
except Exception as e:
    app.logger.error(f"Failed to load SpaCy model: {str(e)}")
    sys.exit(1)

# Security middleware
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Authentication decorator
def require_auth_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
            
        try:
            token = auth_header.split('Bearer ')[1]
            jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated

# Middleware for request logging
def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log request details
        app.logger.info(f"Request: {request.method} {request.path}")
        app.logger.info(f"Headers: {dict(request.headers)}")
        
        # Don't log full body to protect sensitive data
        app.logger.info("Request received with body")
        
        # Execute route handler
        response = f(*args, **kwargs)
        
        # Log response status
        app.logger.info(f"Response status: {response.status_code}")
        return response
    return decorated_function

def compute_similarity(user_answer, correct_answer):
    try:
        # Generate spacy docs
        user_doc = nlp(user_answer.lower().strip())
        correct_doc = nlp(correct_answer.lower().strip())

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

def decrypt_answer(encrypted_answer):
    try:
        return fernet.decrypt(encrypted_answer.encode()).decode()
    except Exception as e:
        app.logger.error(f"Decryption error: {str(e)}")
        return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Daedalus API!"}), 200

@app.route('/health', methods=['GET'])
@log_request
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/groq-rate', methods=['POST'])
@require_auth_token
@log_request
def groq_rate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data"}), 400

        user_answer = data.get('userAnswer', '').strip()
        encrypted_correct_answer = data.get('correctAnswer', '').strip()

        if not user_answer or not encrypted_correct_answer:
            return jsonify({"error": "Missing required fields"}), 400

        # Decrypt the correct answer
        correct_answer = decrypt_answer(encrypted_correct_answer)
        if not correct_answer:
            return jsonify({"error": "Invalid answer format"}), 400

        # Exact match check
        if user_answer.lower() == correct_answer.lower():
            return jsonify({"rating": 100})

        # Call Groq API
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Rate the semantic similarity between two answers from 0 to 100, where 0 means completely different and 100 means exactly the same meaning. Respond only with the number."
                },
                {
                    "role": "user",
                    "content": f"Rate how similar these answers are from 0-100:\nCorrect Answer: {correct_answer}\nUser Answer: {user_answer}"
                }
            ],
            model="llama3-8b-8192",
        )

        rating = int(response.choices[0].message.content.strip())
        if not (0 <= rating <= 100):
            raise ValueError(f"Invalid rating: {rating}")

        return jsonify({"rating": rating})

    except Exception as e:
        app.logger.error(f"Error in groq_rate: {str(e)}")
        return jsonify({"error": "Failed to rate answer"}), 500

@app.route('/api/spacy-rate', methods=['POST'])
@require_auth_token
@log_request
def spacy_rate():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid request data"}), 400

        user_answer = data.get('userAnswer', '').strip()
        encrypted_correct_answer = data.get('correctAnswer', '').strip()

        if not user_answer or not encrypted_correct_answer:
            return jsonify({"error": "Missing required fields"}), 400

        # Decrypt the correct answer
        correct_answer = decrypt_answer(encrypted_correct_answer)
        if not correct_answer:
            return jsonify({"error": "Invalid answer format"}), 400

        # Exact match check
        if user_answer.lower() == correct_answer.lower():
            return jsonify({"rating": 100})

        rating = compute_similarity(user_answer, correct_answer)
        return jsonify({"rating": rating})

    except Exception as e:
        app.logger.error(f"Error in spacy_rate: {str(e)}")
        return jsonify({"error": "Failed to rate answer"}), 500

# Error handling
@app.errorhandler(Exception)
def handle_error(error):
    app.logger.error(f"Unhandled error: {str(error)}")
    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
