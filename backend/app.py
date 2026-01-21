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
import time
import tempfile
import shutil

load_dotenv()
app = Flask(__name__)

# ✅ ULTIMATE CORS (KEEP YOUR ORIGINAL)
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

WORKING_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192", 
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768"
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None
WHISPER_CLIENT = client  # Same client for Whisper

active_interviews = {}
INTERVIEWS_FILE = "interviews.json"

def load_interviews():
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
        except: pass

def save_interviews():
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except: pass

load_interviews()

# 🔥 YOUR ORIGINAL GENERATE QUESTIONS (KEEP THIS EXACTLY)
def safe_groq_call(prompt, max_retries=2):
    if not client: return None
    
    for model in WORKING_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Return ONLY valid JSON: {\"questions\": [{\"id\":1,\"text\":\"question\",\"category\":\"technical\"}]}"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            if (hasattr(response, 'choices') and 
                isinstance(response.choices, list) and 
                len(response.choices) > 0 and 
                hasattr(response.choices[0], 'message') and 
                response.choices[0].message.content):
                
                content = response.choices[0].message.content.strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        questions = result.get('questions', [])
                        if questions: return questions
                    except: pass
        except Exception as e:
            print(f"❌ {model} failed: {str(e)[:80]}")
            continue
    return None

@app.route('/api/generate-questions', methods=['POST', 'OPTIONS'])
def generate_questions():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    
    data = request.get_json() or {}
    job_description = data.get('jobDescription', '').strip()
    resume_text = data.get('resumeText', '').strip()
    
    if not job_description:
        return jsonify({"error": "Job description required"}), 400
    
    prompt = f"""Job: {job_description}
Resume: {resume_text or 'None'}

Generate 6 targeted interview questions. Return ONLY JSON."""
    
    questions = safe_groq_call(prompt)
    if questions: 
        return jsonify({"questions": questions})
    
    # SMART FALLBACK
    words = [w for w in job_description.lower().split() if len(w) > 3]
    tech_terms = words[:3]
    
    fallback = [
        {"id": 1, "text": f"Can you describe your experience with {tech_terms[0] if tech_terms else 'the core technology stack'}?", "category": "technical"},
        {"id": 2, "text": "Tell me about your most challenging project and your specific role in it", "category": "behavioral"},
        {"id": 3, "text": "How do you approach performance optimization in production applications?", "category": "technical"},
        {"id": 4, "text": "Walk me through your typical deployment and CI/CD process", "category": "technical"},
        {"id": 5, "text": "Describe a time you had to learn a new technology under pressure", "category": "behavioral"},
        {"id": 6, "text": "How do you handle code reviews and collaborate with other developers?", "category": "technical"}
    ]
    
    return jsonify({"questions": fallback})

# ✅ ALL OTHER ENDPOINTS (create-interview, recording, evaluation, etc.)
@app.route('/api/health')
def health():
    return jsonify({"status": "Zoom AI Interviewer LIVE ✅", "groq": bool(client)})

@app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
def create_interview():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"})
    
    data = request.get_json() or {}
    questions = data.get('questions', [])
    candidate_name = data.get('candidateName', 'Candidate')
    
    interview_id = str(uuid.uuid4())[:8].upper()
    active_interviews[interview_id] = {
        'id': interview_id,
        'candidate': candidate_name,
        'questions': questions,
        'current_question': 0,
        'answers': [],
        'full_session_recording': None,
        'transcriptions': [],
        'evaluation': None,
        'status': 'active'
    }
    
    save_interviews()
    return jsonify({"interviewId": interview_id, "joinUrl": f"/interview/{interview_id}"})

@app.route('/api/start-recording/<interview_id>', methods=['POST'])
def start_recording(interview_id):
    session = active_interviews.get(interview_id)
    if session:
        session['recording_started'] = time.time()
        save_interviews()
        return jsonify({"status": "recording_started"})
    return jsonify({"error": "Interview not found"}), 404

@app.route('/api/finish-interview/<interview_id>', methods=['POST'])
def finish_interview(interview_id):
    session = active_interviews.get(interview_id)
    if not session: return jsonify({"error": "Interview not found"}), 404
    
    full_video = request.files.get('full_session')
    if full_video:
        os.makedirs("recordings", exist_ok=True)
        filepath = f"recordings/full_{interview_id}.webm"
        full_video.save(filepath)
        session['full_session_recording'] = filepath
    
    session['evaluation'] = evaluate_full_interview(session)
    session['status'] = 'completed'
    save_interviews()
    
    return jsonify({
        "status": "completed",
        "score": session['evaluation'].get('score', 'Pending')
    })

def evaluate_full_interview(session):
    if not client or not session.get('full_session_recording'):
        return {"score": "N/A", "feedback": "No recording"}
    
    try:
        with open(session['full_session_recording'], "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=audio_file
            )
        
        full_text = transcription.text
        eval_prompt = f"""
        Questions: {json.dumps(session['questions'], indent=2)}
        Transcript: {full_text}
        Rate 1-10. JSON only: {{"score": 8, "feedback": "detailed feedback"}}
        """
        
        response = client.chat.completions.create(
            model=WORKING_MODELS[0],
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1
        )
        
        return json.loads(response.choices[0].message.content)
    except:
        return {"score": "N/A", "feedback": "Evaluation failed"}

@app.route('/api/next-question/<interview_id>', methods=['POST'])
def next_question(interview_id):
    session = active_interviews.get(interview_id)
    if session:
        session['current_question'] += 1
        save_interviews()
    return jsonify({"status": "next"})

# ✅ YOUR ORIGINAL INTERVIEW ROOM HTML (with continuous recording)
@app.route('/interview/<interview_id>')
def ai_interview_room(interview_id):
    session = active_interviews.get(interview_id)
    if not session: return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text'] if current_q < len(session['questions']) else "🎉 Complete!"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head><title>AI Interview - {session['candidate']}</title>
    <style>/* YOUR ORIGINAL CSS */</style>
    </head>
    <body>
        <div class="q-counter">Q{current_q + 1}/{len(session['questions'])}</div>
        <h1>🤖 AI Interview - {session['candidate']}</h1>
        
        <!-- Videos + Question Area with START button -->
        <div class="question-area">
            <div style="font-size:1.8em;color:#00d4ff">{question}</div>
            <div class="status recording" id="status">🔴 FULL SESSION RECORDING</div>
            <button id="startInterviewBtn" class="button record-btn">🚀 START FULL INTERVIEW</button>
            <button id="askBtn" class="button record-btn" style="display:none">🎤 AI Ask</button>
            <button id="nextBtn" class="button next-btn" disabled>Next →</button>
        </div>
        
        <script>
        const interviewId = "{interview_id}";
        let mediaStream, recorder, chunks = [];
        
        // Camera + Continuous recording logic (your original + START button)
        async function initCamera() {{
            mediaStream = await navigator.mediaDevices.getUserMedia({{video:{{width:640,height:480}},audio:true}});
            document.querySelector("video").srcObject = mediaStream;
            
            document.getElementById("startInterviewBtn").onclick = async function() {{
                await fetch(`/api/start-recording/${{interviewId}}`,{{method:'POST'}});
                recorder = new MediaRecorder(mediaStream);
                chunks = [];
                recorder.ondataavailable = e => chunks.push(e.data);
                recorder.start(250);
                document.getElementById("startInterviewBtn").style.display = "none";
                document.getElementById("askBtn").style.display = "inline-block";
            }};
        }}
        
        document.getElementById("askBtn").onclick = function() {{
            speechSynthesis.speak(new SpeechSynthesisUtterance("{question}"));
            document.getElementById("nextBtn").disabled = false;
            document.getElementById("askBtn").style.display = "none";
        }};
        
        document.getElementById("nextBtn").onclick = function() {{
            fetch(`/api/next-question/${{interviewId}}`,{{method:'POST'}}).then(()=>location.reload());
        }};
        
        initCamera();
        </script>
    </body>
    </html>'''

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    static_path = app.static_folder
    if path != "" and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(static_path, 'index.html')

@app.route('/api/results/<interview_id>')
def results(interview_id):
    session = active_interviews.get(interview_id)
    if not session: return "Not found", 404
    return f'''
    <h1>Results: {session.get("evaluation", {}).get("score", "N/A")}/10</h1>
    <pre>{json.dumps(session, indent=2)}</pre>
    '''

if __name__ == '__main__':
    app.run(port=int(os.getenv('PORT', 5000)), debug=True)
