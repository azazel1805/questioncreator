import os
import re
import logging
from flask import Flask, request, jsonify, render_template, abort
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# --- Basic Configuration ---
load_dotenv() # Load environment variables from .env file for local dev
api_key = os.getenv("GOOGLE_API_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO) # Log INFO level and above

app = Flask(__name__)

# --- Security Configuration ---
# Define allowed origins explicitly
# IMPORTANT: Use the exact origins your frontend runs on.
ALLOWED_ORIGINS = [
    "https://www.basicsinenglish.app",
    # Add local development URL if needed, e.g.: "http://localhost:3000"
]

# --- CORS Configuration ---
# Initialize CORS, restricting it ONLY to the allowed origins.
# This handles OPTIONS requests and adds Access-Control-Allow-Origin headers
# for requests matching ALLOWED_ORIGINS.
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

# --- Security Middleware (Origin/Referer Check) ---
@app.before_request
def restrict_origin_and_referer():
    """
    Checks Origin and Referer headers against allowed origins.
    Flask-CORS handles the primary Origin check for standard CORS requests.
    This adds an explicit Referer check and an additional Origin check layer.
    """
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')

    # Use app.logger provided by Flask
    app.logger.debug(f"Request Headers: Origin='{origin}', Referer='{referer}'")

    # Check Origin header (acts as secondary check to Flask-CORS)
    # Important if a request somehow bypasses CORS preflight/handling,
    # or if Origin is present but not technically a CORS request triggering Flask-CORS actions.
    if origin and not any(origin.startswith(o) for o in ALLOWED_ORIGINS):
        app.logger.warning(f"Blocking request: Origin '{origin}' not in allowed list {ALLOWED_ORIGINS}")
        # Use abort with a description for clarity in logs/response
        abort(403, description="Forbidden Origin")

    # Check Referer header
    # Note: Referer is less reliable than Origin and can be absent or spoofed.
    if referer and not any(referer.startswith(r) for r in ALLOWED_ORIGINS):
        app.logger.warning(f"Blocking request: Referer '{referer}' not in allowed list {ALLOWED_ORIGINS}")
        abort(403, description="Forbidden Referer")

    # If neither header is present OR if they both match (or one matches and the other is absent),
    # the request proceeds. You could add stricter checks here if needed (e.g., require at least one).


# --- API Logic (Your soru_uret function) ---
def soru_uret(sinav_tipi, soru_tipi, zorluk_seviyesi, soru_sayisi, ceviri_yonu, api_key):
    if not api_key:
        app.logger.error("Google API Key is not configured.")
        return {"questions": "Error: API Key not configured.", "answers": ""}
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') # Or your preferred model

        # (Your extensive prompts dictionary remains unchanged here)
        prompts = {
            "Kelime Sorusu": f"""
            IMPORTANT: Generate EXACTLY {soru_sayisi} completely new and unique English Vocabulary Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each question MUST be a distinct sentence with a blank for a word or phrasal verb, 
            covering diverse topics (e.g., daily life, nature, education, travel, emotions, technology) and using different sentence structures (e.g., questions, statements, negatives). 
            STRICTLY AVOID repeating the same sentence, similar sentence patterns, or previously used topics across questions. 
            The correct option must be chosen from the given choices, and options should be plausible but clearly distinguishable. 
            Format:
            (Sentence with a ___ blank)
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions (e.g., 1., 2., ...).
            """,
            "Dil Bilgisi Sorusu": f"""
            Generate {soru_sayisi} English Grammar Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each question should be a sentence with 1 or 2 blanks related to tense, 
            preposition, or conjunction, with the correct option chosen from the choices. Never repeat the same sentence. 
            Format:
            (Sentence with ___ blank(s))
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions.
            """,
            "Cloze Test Sorusu": f"""
Generate {soru_sayisi} English Cloze Test Questions for the {sinav_tipi} exam in Turkey, 
at {zorluk_seviyesi} difficulty level. Each should be a reading passage with 5 blanks (total {soru_sayisi * 5} questions), 
where blanks can be for missing words, verb tense, or prepositions. Ensure variety and do not repeat the same sentence.

Format:
1. (Reading passage with ___1___, ___2___, ___3___, ___4___, and ___5___ blanks)
   1) ___1___  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   2) ___2___  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   3) ___3___  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   4) ___4___  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   5) ___5___  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]

Generate multiple unique passages when more than one is requested.
""",

            "Cümle Tamamlama Sorusu": f"""
            Generate {soru_sayisi} English Sentence Completion Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each question should be an incomplete sentence, give the main clause and ask for the sub clause
        or give the sub clause and ask for the main clause using an appropriate conjunction from the options. The blank can be in the middle or at the beginning but do not use any other completing if the blank is in the ending. Never repeat the same sentence. 
            Format:
            (Incomplete sentence ___)
            A) Option 1

            B) Option 2

            C) Option 3

            D) Option 4

            E) Option 5
            Correct answer: [letter]
            Number the questions.
            """,
            "Çeviri Sorusu": f"""
            Generate {soru_sayisi} Translation Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each question should be a sentence translated from {'Turkish to English' if ceviri_yonu == 'tr_to_en' else 'English to Turkish'}. 
            Provide a sentence in {'Turkish' if ceviri_yonu == 'tr_to_en' else 'English'} and 5 options in {'English' if ceviri_yonu == 'tr_to_en' else 'Turkish'}, with one correct translation. 
            Ensure variety in sentence structures (e.g., affirmative, negative, questions, conditionals), topics (e.g., daily life, nature, technology, education), and avoid repetitive patterns. 
            Format:
            (Sentence in {'Turkish' if ceviri_yonu == 'tr_to_en' else 'English'})
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions.
            """,
            "Paragraf Sorusu": f"""
Generate {soru_sayisi} English Paragraph Questions for the {sinav_tipi} exam in Turkey, 
at {zorluk_seviyesi} difficulty level. Each paragraph should be followed by 3 related multiple-choice questions, 
each with 5 answer choices (A, B, C, D, E) and the correct answer explicitly stated.

Format:
1. (Paragraph text)
   1) (Question)  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   2) (Question)  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]
   3) (Question)  
      A) Option 1  
      B) Option 2  
      C) Option 3  
      D) Option 4  
      E) Option 5  
      Correct answer: [Letter]

Make sure that all questions have answers, even when generating multiple paragraphs.
""",
            "Diyalog Tamamlama Sorusu": f"""
            IMPORTANT: Generate EXACTLY {soru_sayisi} English Dialogue Completion Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each dialogue must have exactly 5 sentences between two people with randomly chosen names (different names for each dialogue), 
            following the order: Person1 → Person2 → Person1 → Person2 → Person1. 
            One line must be completely missing and represented as '(Speaker: ___)' on its own line, where the missing line can randomly be the 1st, 2nd, 3rd, 4th, or 5th line. 
            The speaker of the missing line must match its position (1st, 3rd, 5th is Person1; 2nd, 4th is Person2). 
            The missing line must be a natural and logical part of the conversation, and the correct option must be chosen from the given choices. 
            Ensure variety in topics (e.g., daily life, work, travel) and avoid repetition of dialogue patterns or names across questions. 
            Format each dialogue based on the position of the missing line:
            - If 1st line missing: '(Person1: ___)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)'
            - If 2nd line missing: '(Person1: Dialogue line)' then '(Person2: ___)' then '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)'
            - If 3rd line missing: '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: ___)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)'
            - If 4th line missing: '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)' then '(Person2: ___)' then '(Person1: Dialogue line)'
            - If 5th line missing: '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: Dialogue line)' then '(Person2: Dialogue line)' then '(Person1: ___)'
            Followed by:
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions (e.g., 1., 2., ...).
            """,
            "Restatement (Yeniden Yazma) Sorusu": f"""
            Generate {soru_sayisi} English Restatement Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each should be a sentence with 5 options rephrasing it, one correct. 
            Format:
            (Sentence)
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions.
            """,
            "Paragraf Tamamlama Sorusu": f"""
            Generate {soru_sayisi} English Paragraph Completion Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each should be a paragraph with a 1-sentence blank. The blank can be any sentence in the paragraph and make it different for each question. 
            Format:
            (Paragraph with a ___ blank)
            A) Option 1
            B) Option 2
            C) Option 3
            D) Option 4
            E) Option 5
            Correct answer: [letter]
            Number the questions.
            """,
            "Akışı Bozan Cümle Sorusu": f"""
            Generate {soru_sayisi} English Irrelevant Sentence Questions for the {sinav_tipi} exam in Turkey, 
            at {zorluk_seviyesi} difficulty level. Each question should be a paragraph consisting of several sentences 
            that follow a logical flow and coherence when read sequentially, but one sentence that is completely related to the topic 
            but disrupts the logical flow or coherence (e.g., by introducing an inconsistent detail, shifting focus slightly, or breaking the narrative). 
            The task is to identify the sentence that breaks the flow. 
            Format:
            (Paragraph text with numbered sentences, e.g., (1) Sentence 1. (2) Sentence 2. ...)
            A) Sentence 1
            B) Sentence 2
            C) Sentence 3
            D) Sentence 4
            E) Sentence 5
            Correct answer: [letter]
            Number the questions (e.g., 1., 2., ...).
            """
        }

        prompt = prompts.get(soru_tipi, "Invalid question type")
        if prompt == "Invalid question type":
            app.logger.warning(f"Invalid question type requested: {soru_tipi}")
            return {"questions": prompt, "answers": ""}

        if soru_tipi != "Çeviri Sorusu":
            ceviri_yonu = None # Ensure it's None if not translation

        app.logger.info(f"Generating {soru_sayisi} '{soru_tipi}' for '{sinav_tipi}' at '{zorluk_seviyesi}' difficulty.")
        response = model.generate_content(prompt)
        response_text = response.text
        app.logger.debug(f"Gemini Raw Response: {response_text[:200]}...") # Log start of response

        # --- Parsing Logic (Looks generally okay, added minor logging) ---
        questions = []
        answers = []
        lines = response_text.strip().split('\n') # Use strip() before split
        current_question_lines = []
        question_number_found = 0

        for line in lines:
            line_strip = line.strip()
            if not line_strip: # Skip empty lines
                continue

            # Match lines starting with digits and a dot (e.g., "1.", "12.")
            match = re.match(r"^(\d+)\.\s*(.*)", line_strip)
            if match:
                current_num = int(match.group(1))
                # If starting a new question number block AND we have content in current_question_lines
                if current_num > question_number_found and current_question_lines:
                    # Before starting the new question, finalize the previous one
                    q_text = '\n'.join(current_question_lines).strip()
                    if q_text: # Ensure we don't add empty questions
                        questions.append(q_text)
                    current_question_lines = [] # Reset for the new question
                
                question_number_found = current_num # Update the latest number found
                current_question_lines.append(line) # Add the line (could be the start of the question text)

            # Check for correct answer line
            elif line_strip.lower().startswith("correct answer:"):
                answer_part = line_strip.split(":", 1)[1].strip()
                # Use the most recently found question number
                answers.append(f"{question_number_found}. {answer_part}")
                # Add the current question block *before* the answer line was processed
                q_text = '\n'.join(current_question_lines).strip()
                if q_text:
                    questions.append(q_text)
                current_question_lines = [] # Reset because the question block is complete

            # Otherwise, it's part of the current question's text/options
            elif question_number_found > 0: # Only add if we've actually started processing a numbered question
                 current_question_lines.append(line)

        # Catch any remaining question content after the last answer
        if current_question_lines:
             q_text = '\n'.join(current_question_lines).strip()
             if q_text:
                 questions.append(q_text)

        app.logger.info(f"Successfully parsed {len(questions)} questions and {len(answers)} answers.")
        
        # Ensure we don't return more questions/answers than requested
        # Note: Your prompt asks for EXACTLY soru_sayisi, but parsing might split differently.
        # This slicing ensures the output count matches the request input `soru_sayisi`.
        # It assumes the API generally provides at least the requested number in order.
        final_questions = questions[:soru_sayisi]
        final_answers = answers[:soru_sayisi]

        return {"questions": '\n\n'.join(final_questions), "answers": '\n'.join(final_answers)}

    except Exception as e:
        app.logger.error(f"Error during question generation or processing: {e}", exc_info=True) # Log traceback
        return {"questions": f"Error: {e}", "answers": ""}


# --- Routes ---
@app.route('/')
def index():
    # This serves your frontend HTML. It's protected by the before_request check.
    # Note: If index.html itself makes API calls, those calls Origin/Referer will be checked.
    # Direct loading of the page might not have Origin, Referer check might apply.
    return render_template('index.html')

@app.route('/soru_uret', methods=['POST'])
def uret_soru():
    # This API endpoint is protected by CORS and the before_request check.
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        sinav_tipi = data.get('sinav_tipi')
        zorluk_seviyesi = data.get('zorluk_seviyesi')
        soru_tipi = data.get('soru_tipi')
        soru_sayisi_str = data.get('soru_sayisi')
        ceviri_yonu = data.get('ceviri_yonu', 'tr_to_en') # Default if not provided

        # --- Input Validation ---
        if not all([sinav_tipi, zorluk_seviyesi, soru_tipi, soru_sayisi_str]):
             return jsonify({'error': 'Missing required fields: sinav_tipi, zorluk_seviyesi, soru_tipi, soru_sayisi'}), 400
        try:
            soru_sayisi = int(soru_sayisi_str)
            if soru_sayisi <= 0 or soru_sayisi > 20: # Example limit
                 return jsonify({'error': 'Soru sayısı must be between 1 and 20'}), 400
        except ValueError:
            return jsonify({'error': 'Soru sayısı must be an integer'}), 400
        # Add more validation for enum-like fields if needed
        # --- End Input Validation ---

        result = soru_uret(sinav_tipi, soru_tipi, zorluk_seviyesi, soru_sayisi, ceviri_yonu, api_key)

        if "Error:" in result['questions']:
             # If soru_uret handled an error internally, return 500
             return jsonify({'error': result['questions']}), 500
        else:
             return jsonify({'questions': result['questions'], 'answers': result['answers']})

    except Exception as e:
        app.logger.error(f"Unhandled exception in /soru_uret route: {e}", exc_info=True)
        return jsonify({'error': 'An internal server error occurred.'}), 500

# --- Custom Error Handler for 403 Forbidden ---
@app.errorhandler(403)
def forbidden(e):
    # Log the detailed description from abort() if available
    description = e.description if hasattr(e, 'description') else "Forbidden"
    app.logger.warning(f"Forbidden (403) access attempt: {description}")
    response = jsonify(error=description)
    response.status_code = 403
    return response

# --- Development Server Execution ---
# This block is mainly for local testing (python app.py)
# Render will use Gunicorn specified in your Procfile or Start Command
if __name__ == '__main__':
    # Use 0.0.0.0 to be accessible on the network (and inside containers)
    # Use Render's PORT environment variable if available, otherwise default (e.g., 5000)
    port = int(os.environ.get('PORT', 5000))
    # debug=True is useful for development but should be False in production
    # Render typically sets NODE_ENV or similar; you might check that to disable debug mode
    app.run(host='0.0.0.0', port=port, debug=os.getenv("FLASK_ENV") == "development")