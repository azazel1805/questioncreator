from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)
CORS(app)
@app.before_request
def restrict_origin():
    allowed_origins = [
        "https://sites.google.com",
        "https://sites.google.com/view/basicsinenglish",  # your actual site path
        "https://www.basicsinenglish.app"  # if you use a custom domain
    ]
    origin = request.headers.get('Origin')
    referer = request.headers.get('Referer')

    if origin and not any(origin.startswith(o) for o in allowed_origins):
        abort(403)
    if referer and not any(referer.startswith(r) for r in allowed_origins):
        abort(403)


def soru_uret(sinav_tipi, soru_tipi, zorluk_seviyesi, soru_sayisi, ceviri_yonu, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

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

    try:
        prompt = prompts.get(soru_tipi, "Invalid question type")
        if prompt == "Invalid question type":
            return {"questions": prompt, "answers": ""}
        
        if soru_tipi != "Çeviri Sorusu":
            ceviri_yonu = None
        
        response = model.generate_content(prompt)
        response_text = response.text

        # Soruları ve cevapları ayır
        questions = []
        answers = []
        lines = response_text.split('\n')
        current_question = []
        question_number = 0
        
        for line in lines:
            if re.match(r"^\d+\.", line):  # Yeni bir soru veya paragraf başlıyor
                if current_question:
                    questions.append('\n'.join(current_question))
                current_question = [line]
                question_number += 1
            elif line.strip().startswith("Correct answer:"):
                answer = line.split("Correct answer: ")[1].strip()
                answers.append(f"{question_number}. {answer}")
            elif line.strip() and not line.strip().startswith("Correct answer:"):
                current_question.append(line)

        if current_question:  # Son soruyu ekle
            questions.append('\n'.join(current_question))

        # Soru sayısını kullanıcı girişine göre sınırla
        if len(questions) > soru_sayisi:
            questions = questions[:soru_sayisi]
            answers = answers[:soru_sayisi]

        return {"questions": '\n\n'.join(questions), "answers": '\n'.join(answers)}
    except Exception as e:
        return {"questions": f"Error: {e}", "answers": ""}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/soru_uret', methods=['POST'])
def uret_soru():
    try:
        data = request.get_json()
        sinav_tipi = data['sinav_tipi']
        zorluk_seviyesi = data['zorluk_seviyesi']
        soru_tipi = data['soru_tipi']
        soru_sayisi = int(data['soru_sayisi'])
        ceviri_yonu = data.get('ceviri_yonu', 'tr_to_en')

        result = soru_uret(sinav_tipi, soru_tipi, zorluk_seviyesi, soru_sayisi, ceviri_yonu, api_key)

        return jsonify({'questions': result['questions'], 'answers': result['answers']})
    except Exception as e:
        return jsonify({'error': str(e)}, 500)

if __name__ == '__main__':
    app.run(debug=True, port=5000)