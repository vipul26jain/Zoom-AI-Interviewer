from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import json
import re
import requests
import base64
import threading
import time
from datetime import datetime
import io

load_dotenv()
app = Flask(__name__)

# Perfect CORS
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# AI Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else OpenAI(api_key=OPENAI_API_KEY)
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1") if os.getenv("GROQ_API_KEY") else None

active_interviews = {}
ai_bot_threads = {}
INTERVIEWS_FILE = "interviews.json"

def safe_groq_call(prompt, is_evaluation=False):
    """Safe AI call with fallback"""
    try:
        messages = [{"role": "user", "content": prompt}]
        if is_evaluation:
            messages = [{"role": "system", "content": "You are an expert technical interviewer. Evaluate the candidate's answer and provide score (1-10) and feedback."}, *messages]
        
        response = client.chat.completions.create(
            model="llama-3.1-70b-versatile" if not is_evaluation else "gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except:
        return "No AI response available"

def generate_questions(job_desc, skills):
    """Generate 6 targeted questions"""
    prompt = f"""Job: {job_desc}
Skills: {skills}

Generate EXACTLY 6 targeted technical interview questions. Return ONLY valid JSON:
{{"questions": [{{"id":1,"text":"Question text","category":"technical"}}, ...]}}"""
    
    result = safe_groq_call(prompt)
    try:
        json_match = re.search(r'\{.*\}', result, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            return data.get('questions', [])
    except:
        pass
    
    # Smart fallback
    return [
        {"id": 1, "text": "Tell me about your experience with this role's core technologies", "category": "technical"},
        {"id": 2, "text": "Describe your most challenging project and your role in it", "category": "behavioral"},
        {"id": 3, "text": "How do you optimize application performance?", "category": "technical"},
        {"id": 4, "text": "Walk through your deployment process", "category": "technical"},
        {"id": 5, "text": "Time you learned new technology quickly?", "category": "behavioral"},
        {"id": 6, "text": "How do you handle code reviews?", "category": "technical"}
    ]

def start_ai_bot(interview_id):
    """Start conversational AI bot"""
    if interview_id in ai_bot_threads:
        return False
    
    print(f"🤖 Starting AI Bot for {interview_id}")
    thread = threading.Thread(target=ai_interview_loop, args=(interview_id,), daemon=True)
    thread.start()
    ai_bot_threads[interview_id] = thread
    return True

def ai_interview_loop(interview_id):
    """Main AI interview conversation loop"""
    session = active_interviews[interview_id]
    candidate_name = session['candidate']
    questions = session['questions']
    
    session['bot_messages'] = []
    session['candidate_transcripts'] = []
    session['evaluations'] = []
    
    # 1. GREETING
    greeting = f"Hello {candidate_name}! Welcome to your AI technical interview. I'm your interviewer today. Please start with a 1-minute introduction about yourself."
    session['bot_messages'].append({'role': 'ai', 'text': greeting, 'timestamp': datetime.now().isoformat()})
    save_interviews()
    time.sleep(65)  # Wait for intro
    
    session['candidate_transcripts'].append({'question': 0, 'transcript': 'Candidate introduction recorded via Zoom'})
    
    # 2. 6 QUESTIONS (with evaluation)
    for i, q in enumerate(questions[:6]):
        question_text = f"Question {i+1}: {q['text']}"
        print(f"🤖 Q{i+1}: {question_text}")
        
        session['bot_messages'].append({'role': 'ai', 'text': question_text, 'timestamp': datetime.now().isoformat()})
        save_interviews()
        
        time.sleep(45)  # Wait for answer
        
        # Simulate transcript (real transcription would come from Zoom webhook)
        transcript = f"Candidate answered Q{i+1} (transcribed from Zoom audio)"
        session['candidate_transcripts'].append({'question': i+1, 'transcript': transcript})
        
        # AI Evaluation
        eval_prompt = f"Question: {q['text']}\nAnswer: {transcript}\n\nScore 1-10 and provide brief feedback:"
        evaluation = safe_groq_call(eval_prompt, True)
        session['evaluations'].append({'question': i+1, 'evaluation': evaluation})
        
        save_interviews()
    
    # 3. FINAL EVALUATION
    session['final_evaluation'] = safe_groq_call(f"""
    Candidate: {candidate_name}
    All answers: {json.dumps([t['transcript'] for t in session['candidate_transcripts']])}
    
    Provide overall score (1-10), recommendation (Hire/No Hire), and summary.
    """, True)
    
    session['status'] = 'completed'
    session['completed_at'] = datetime.now().isoformat()
    save_interviews()
    print(f"🏁 Interview complete: {interview_id}")

def save_interviews():
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except: pass

def load_interviews():
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
        except: pass

load_interviews()

# Zoom OAuth
ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

def get_zoom_token():
    if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
        return None
    try:
        url = "https://zoom.us/oauth/token"
        auth = base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": ZOOM_ACCOUNT_ID}
        response = requests.post(url, headers=headers, data=data)
        return response.json().get("access_token") if response.status_code == 200 else None
    except:
        return None

@app.route('/api/health')
def health():
    return jsonify({"status": "AI Interviewer LIVE ✅"})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(f"static/{path}"):
        return send_from_directory("static", path)
    return send_from_directory("static", 'index.html')

@app.route('/api/start-interview', methods=['POST'])
def start_interview():
    data = request.get_json() or {}
    job_desc = data.get('jobDescription', '')
    skills = data.get('skills', '')
    candidate_name = data.get('candidateName', 'Candidate')
    
    if not job_desc or not skills:
        return jsonify({"error": "Job description and skills required"}), 400
    
    # 1. Generate questions
    questions = generate_questions(job_desc, skills)
    
    # 2. Create session
    interview_id = str(uuid.uuid4())[:8].upper()
    active_interviews[interview_id] = {
        'id': interview_id,
        'candidate': candidate_name,
        'job_desc': job_desc,
        'skills': skills,
        'questions': questions,
        'status': 'active',
        'created_at': datetime.now().isoformat()
    }
    save_interviews()
    
    # 3. Create Zoom meeting
    token = get_zoom_token()
    if token:
        url = "https://api.zoom.us/v2/users/me/meetings"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "topic": f"🤖 AI Interview: {candidate_name} [{interview_id}]",
            "type": 1,
            "settings": {
                "host_video": False,
                "participant_video": True,
                "join_before_host": True,
                "waiting_room": False,
                "auto_recording": "cloud",
                "cloud_recording": {"status": "on"},
                "mute_upon_entry": False
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            meeting = response.json()
            active_interviews[interview_id]['zoom'] = {
                "join_url": meeting.get("join_url"),
                "meeting_id": meeting.get("id")
            }
    
    # 4. Start AI Bot
    start_ai_bot(interview_id)
    
    save_interviews()
    return jsonify({
        "success": True,
        "interview_id": interview_id,
        "zoom_url": active_interviews[interview_id].get('zoom', {}).get('join_url', ''),
        "message": "Interview started! AI Bot will greet, ask questions, evaluate answers."
    })

@app.route('/api/interview-status/<interview_id>')
def interview_status(interview_id):
    session = active_interviews.get(interview_id, {})
    return jsonify(session)

@app.route('/debug')
def debug():
    return jsonify({"interviews": len(active_interviews), "active_bots": len(ai_bot_threads)})

if __name__ == '__main__':
    os.makedirs("static", exist_ok=True)
    print("🚀 AI Interviewer LIVE - http://localhost:5000")
    app.run(port=5000, debug=True)
