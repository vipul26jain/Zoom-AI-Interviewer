# # from flask import Flask, request, jsonify, send_file
# # from flask_cors import CORS
# # from openai import OpenAI
# # from dotenv import load_dotenv
# # import os
# # import json
# # import time
# # import io
# # from gtts import gTTS
# # import uuid
# # import re

# # load_dotenv()

# # app = Flask(__name__)
# # CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500"])

# # # ✅ WORKING MODELS (Jan 2026) - Multiple fallbacks
# # WORKING_MODELS = [
# #     "llama-3.3-70b-versatile",
# #     "llama3-70b-8192", 
# #     "llama-3.1-70b-versatile",
# #     "mixtral-8x7b-32768"
# # ]

# # GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# # client = None

# # if GROQ_API_KEY:
# #     client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
# #     print("✅ GROQ client initialized")

# # active_interviews = {}

# # @app.before_request
# # def handle_preflight():
# #     if request.method == 'OPTIONS':
# #         resp = jsonify({'status': 'ok'})
# #         resp.headers['Access-Control-Allow-Origin'] = '*'
# #         resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
# #         resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
# #         return resp

# # @app.route('/')
# # def home():
# #     return jsonify({
# #         "status": "🚀 AI Interviewer LIVE!",
# #         "models": WORKING_MODELS[:2],
# #         "endpoints": ["/api/generate-questions"]
# #     })

# # def safe_groq_call(prompt, max_retries=2):
# #     """✅ BULLETPROOF Groq API call with ALL error handling"""
# #     if not client:
# #         return None
    
# #     for model in WORKING_MODELS:
# #         try:
# #             print(f"🔄 Trying model: {model}")
# #             response = client.chat.completions.create(
# #                 model=model,
# #                 messages=[
# #                     {
# #                         "role": "system",
# #                         "content": "Return ONLY valid JSON: {\"questions\": [{\"id\":1,\"text\":\"question\",\"category\":\"technical\"}]} NO markdown, no explanations."
# #                     },
# #                     {"role": "user", "content": prompt}
# #                 ],
# #                 temperature=0.1,
# #                 max_tokens=800
# #             )
            
# #             # ✅ FIXED: SAFE response parsing
# #             if (hasattr(response, 'choices') and 
# #                 isinstance(response.choices, list) and 
# #                 len(response.choices) > 0 and 
# #                 hasattr(response.choices[0], 'message') and 
# #                 hasattr(response.choices[0].message, 'content')):
                
# #                 content = response.choices[0].message.content.strip()
# #                 print(f"✅ SUCCESS with {model}: {content[:60]}...")
                
# #                 # Extract JSON
# #                 json_match = re.search(r'\{.*\}', content, re.DOTALL)
# #                 if json_match:
# #                     try:
# #                         result = json.loads(json_match.group())
# #                         questions = result.get('questions', [])
# #                         if questions:
# #                             return questions
# #                     except json.JSONDecodeError:
# #                         pass
            
# #         except Exception as e:
# #             print(f"❌ {model} failed: {str(e)[:80]}")
# #             continue
    
# #     return None

# @app.route('/api/generate-questions', methods=['POST', 'OPTIONS'])
# def generate_questions():
#     if request.method == 'OPTIONS':
#         return jsonify({"status": "ok"})
    
#     data = request.get_json() or {}
#     job_description = data.get('jobDescription', '').strip()
#     resume_text = data.get('resumeText', '').strip()
    
#     print(f"📥 JD: {job_description[:60]}...")
    
#     if not job_description:
#         return jsonify({"error": "Job description required"}), 400
    
#     # Try Groq first
#     prompt = f"""Job: {job_description}
# Resume: {resume_text or 'None'}

# Generate 6 targeted interview questions. Return ONLY JSON."""
    
#     questions = safe_groq_call(prompt)
    
#     if questions:
#         print(f"✅ Generated {len(questions)} AI questions")
#         return jsonify({"questions": questions})
    
#     # ✅ SMART FALLBACK - No errors, always works
#     print("🔄 Using smart fallback")
#     words = [w for w in job_description.lower().split() if len(w) > 3]
#     tech_terms = words[:3]
    
#     fallback = [
#         {"id": 1, "text": f"Can you describe your experience with {tech_terms[0] if tech_terms else 'the core technology stack'}?", "category": "technical"},
#         {"id": 2, "text": "Tell me about your most challenging project and your specific role in it", "category": "behavioral"},
#         {"id": 3, "text": "How do you approach performance optimization in production applications?", "category": "technical"},
#         {"id": 4, "text": "Walk me through your typical deployment and CI/CD process", "category": "technical"},
#         {"id": 5, "text": "Describe a time you had to learn a new technology under pressure", "category": "behavioral"},
#         {"id": 6, "text": "How do you handle code reviews and collaborate with other developers?", "category": "technical"}
#     ]
    
#     return jsonify({"questions": fallback})

# # @app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
# # def create_interview():
# #     if request.method == 'OPTIONS':
# #         return jsonify({"status": "ok"})
    
# #     data = request.get_json() or {}
# #     questions = data.get('questions', [])
# #     candidate_name = data.get('candidateName', 'Candidate')
    
# #     interview_id = str(uuid.uuid4())[:8].upper()
# #     active_interviews[interview_id] = {
# #         'id': interview_id,
# #         'candidate': candidate_name,
# #         'questions': questions,
# #         'current_question': 0,
# #         'answers': [],
# #         'status': 'active'
# #     }
    
# #     print(f"🎤 Interview {interview_id} created ({len(questions)} questions)")
# #     return jsonify({
# #         "interviewId": interview_id,
# #         "joinUrl": f"http://localhost:5000/interview/{interview_id}"
# #     })

# # @app.route('/interview/<interview_id>')
# # def interview_room(interview_id):
# #     session = active_interviews.get(interview_id)
# #     if not session:
# #         return "❌ Interview not found", 404
    
# #     current_q_index = session['current_question']
# #     question = session['questions'][current_q_index]['text'] if current_q_index < len(session['questions']) else "Interview complete!"
    
# #     return f'''
# # <!DOCTYPE html>
# # <html>
# # <head>
# #     <title>AI Interview - {session['candidate']}</title>
# #     <style>
# #         *{{margin:0;padding:0;box-sizing:border-box}}
# #         body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh;padding:20px}}
# #         .container{{max-width:1200px;margin:0 auto}}
# #         h1{{text-align:center;font-size:2.5em;background:linear-gradient(45deg,#00d4ff,#ff6b6b);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
# #         .videos{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin:40px 0}}
# #         .video-container{{background:rgba(15,15,35,0.8);border-radius:20px;padding:20px;border:3px solid #00d4ff;box-shadow:0 20px 40px rgba(0,212,255,0.2)}}
# #         video{{width:100%;height:350px;border-radius:15px;background:#0f0f23}}
# #         .question-area{{background:linear-gradient(135deg,rgba(22,33,62,0.95),rgba(26,26,46,0.95));backdrop-filter:blur(20px);padding:50px;border-radius:25px;margin:40px 0;text-align:center;border:2px solid #00d4ff}}
# #         .question-text{{font-size:2em;color:#00d4ff;margin-bottom:30px;line-height:1.5;max-width:900px;margin:0 auto}}
# #         .status{{padding:20px 40px;border-radius:15px;margin:25px 0;font-size:1.2em;font-weight:600;background:rgba(255,255,255,0.1)}}
# #         .status.recording{{background:linear-gradient(45deg,#ff4444,#cc0000);animation:pulse 1s infinite;color:white}}
# #         button{{padding:20px 40px;font-size:1.3em;font-weight:600;border:none;border-radius:15px;cursor:pointer;margin:15px 10px;transition:all 0.3s;box-shadow:0 10px 30px rgba(0,0,0,0.3)}}
# #         .record-btn{{background:linear-gradient(45deg,#ff4444,#cc0000);color:white}}
# #         .record-btn.recording{{animation:pulse 1s infinite}}
# #         .next-btn{{background:linear-gradient(45deg,#00d4ff,#0099cc);color:white}}
# #         .next-btn:disabled{{opacity:0.5;background:#666;cursor:not-allowed}}
# #         @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:0.7;transform:scale(1.02)}}}}
# #     </style>
# # </head>
# # <body>
# #     <div class="container">
# #         <h1>🤖 AI Technical Interview - Q{current_q_index + 1}</h1>
# #         <div class="videos">
# #             <div class="video-container">
# #                 <h3 style="margin-bottom:15px;color:#00d4ff">🤖 AI Interviewer</h3>
# #                 <video id="aiVideo" autoplay muted playsinline></video>
# #             </div>
# #             <div class="video-container">
# #                 <h3 style="margin-bottom:15px;color:#ff6b6b">{session['candidate']}</h3>
# #                 <video id="candidateVideo" autoplay playsinline muted></video>
# #             </div>
# #         </div>
        
# #         <div class="question-area">
# #             <div class="question-text">{question}</div>
# #             <div class="status" id="status">🎤 Click Record → Answer for 2 minutes</div>
# #             <div>
# #                 <button id="recordBtn" class="record-btn">🎤 Record Answer (2:00)</button>
# #                 <button id="nextBtn" class="next-btn" disabled>Next Question →</button>
# #             </div>
# #             <audio id="questionAudio" style="display:none"></audio>
# #         </div>
# #     </div>
    
# #     <script>
# #         let stream, recorder, chunks=[], interviewId='{interview_id}', currentQ={current_q_index};
        
# #         navigator.mediaDevices.getUserMedia({{
# #             video:{{width:640,height:480,facingMode:'user'}},
# #             audio:{{echoCancellation:true,noiseSuppression:true}}
# #         }}).then(s => {{
# #             stream = s;
# #             document.getElementById('candidateVideo').srcObject = s;
# #             createAnimatedAI();
# #             speakQuestion();
# #         }}).catch(e => console.error('Media error:', e));
        
# #         function createAnimatedAI() {{
# #             const canvas = document.createElement('canvas');
# #             canvas.width=640; canvas.height=360;
# #             const ctx = canvas.getContext('2d');
# #             document.getElementById('aiVideo').srcObject = canvas.captureStream(30);
            
# #             let frame = 0;
# #             function animate() {{
# #                 ctx.fillStyle = '#1a1a2e'; ctx.fillRect(0, 0, 640, 360);
                
# #                 // AI avatar with glow
# #                 const radius = 85 + Math.sin(frame * 0.1) * 10;
# #                 const gradient = ctx.createRadialGradient(320, 180, 0, 320, 180, radius);
# #                 gradient.addColorStop(0, '#00d4ff');
# #                 gradient.addColorStop(0.6, '#0099cc');
# #                 gradient.addColorStop(1, 'rgba(26,26,46,0.9)');
# #                 ctx.fillStyle = gradient;
# #                 ctx.beginPath();
# #                 ctx.arc(320, 180, radius, 0, Math.PI * 2);
# #                 ctx.fill();
                
# #                 // Talking mouth animation
# #                 ctx.fillStyle = '#16213e';
# #                 const mouthHeight = 25 + Math.sin(frame * 0.4) * 12;
# #                 ctx.fillRect(300, 225, 40, mouthHeight);
                
# #                 frame++;
# #                 requestAnimationFrame(animate);
# #             }}
# #             animate();
# #         }}
        
# #         function speakQuestion() {{
# #             const audio = document.getElementById('questionAudio');
# #             const questionText = document.querySelector('.question-text').textContent;
# #             audio.src = `/api/tts-question/1?text=` + encodeURIComponent(questionText);
# #             audio.play().catch(e => console.log('Audio autoplay blocked'));
# #         }}
        
# #         document.getElementById('recordBtn').onclick = () => {{
# #             // Auto-detect best codec
# #             let mimeType = 'audio/webm';
# #             if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) mimeType = 'audio/webm;codecs=opus';
# #             else if (MediaRecorder.isTypeSupported('audio/mp4')) mimeType = 'audio/mp4';
            
# #             recorder = new MediaRecorder(stream, {{mimeType: mimeType}});
# #             chunks = [];
            
# #             recorder.ondataavailable = e => {{if(e.data.size > 0) chunks.push(e.data);}};
# #             recorder.onstop = uploadAnswer;
            
# #             recorder.start(1000);
            
# #             const recordBtn = document.getElementById('recordBtn');
# #             const status = document.getElementById('status');
# #             recordBtn.disabled = true;
# #             recordBtn.classList.add('recording');
# #             recordBtn.textContent = '🔴 Recording...';
            
# #             let timeLeft = 120;
# #             status.textContent = '🔴 Recording (2:00)';
# #             status.className = 'status recording';
            
# #             const timer = setInterval(() => {{
# #                 timeLeft--;
# #                 const minutes = Math.floor(timeLeft / 60);
# #                 const seconds = timeLeft % 60;
# #                 status.textContent = '🔴 Recording (${{minutes}}: ${{seconds.toString().padStart(2, '0')}})';
# #                 recordBtn.textContent = '🔴 Recording...';
                
# #                 if (timeLeft <= 0) {{
# #                     clearInterval(timer);
# #                     recorder.stop();
# #                 }}
# #             }}, 1000);
# #         }};
        
# #         function uploadAnswer() {{
# #             if (chunks.length === 0) {{
# #                 alert('No audio recorded');
# #                 return;
# #             }}
            
# #             const blob = new Blob(chunks, {{type: 'audio/webm'}});
# #             const formData = new FormData();
# #             formData.append('audio', blob, `answer_q${{currentQ + 1}}.webm`);
            
# #             fetch(`/api/submit-answer/${{interviewId}}`, {{
# #                 method: 'POST',
# #                 body: formData
# #             }})
# #             .then(r => r.json())
# #             .then(data => {{
# #                 document.getElementById('status').textContent = '✅ Answer saved! Ready for next question.';
# #                 document.getElementById('status').className = 'status';
# #                 document.getElementById('recordBtn').style.display = 'none';
# #                 document.getElementById('nextBtn').disabled = false;
# #             }})
# #             .catch(e => {{
# #                 console.error('Upload failed:', e);
# #                 document.getElementById('status').textContent = '❌ Upload failed - but audio recorded locally';
# #             }});
# #         }}
# #     </script>
# # </body>
# # </html>'''

# # @app.route('/api/submit-answer/<interview_id>', methods=['POST', 'OPTIONS'])
# # def submit_answer(interview_id):
# #     if request.method == 'OPTIONS':
# #         return jsonify({"status": "ok"})
    
# #     session = active_interviews.get(interview_id)
# #     if not session:
# #         return jsonify({"error": "Session not found"}), 404
    
# #     audio_file = request.files.get('audio')
# #     if audio_file:
# #         os.makedirs("recordings", exist_ok=True)
# #         filename = f"{interview_id}_q{session['current_question'] + 1}_{int(time.time())}.webm"
# #         filepath = f"recordings/{filename}"
# #         audio_file.save(filepath)
        
# #         session['answers'].append({
# #             'question_id': session['current_question'] + 1,
# #             'filename': filename,
# #             'size_bytes': os.path.getsize(filepath),
# #             'timestamp': time.time()
# #         })
        
# #         session['current_question'] += 1
# #         print(f"✅ Saved {filename} ({os.path.getsize(filepath)} bytes)")
    
# #     return jsonify({
# #         "status": "saved",
# #         "current_question": session['current_question'] + 1,
# #         "total_questions": len(session['questions'])
# #     })

# # @app.route('/api/tts-question/<int:qid>')
# # def tts_question(qid):
# #     text = request.args.get('text', 'Please answer this question clearly')
# #     try:
# #         tts = gTTS(text=text[:200], lang='en', slow=False)
# #         buffer = io.BytesIO()
# #         tts.write_to_fp(buffer)
# #         buffer.seek(0)
# #         return send_file(buffer, mimetype='audio/mpeg', as_attachment=True, download_name=f"q{qid}.mp3")
# #     except Exception as e:
# #         print(f"TTS error: {e}")
# #         return "TTS unavailable", 500

# # if __name__ == '__main__':
# #     os.makedirs("recordings", exist_ok=True)
# #     print("🚀 AI Interviewer Backend - BULLETPROOF!")
# #     print("✅ FIXED: 'list object has no attribute message'")
# #     print("✅ Multiple model fallbacks")
# #     print("✅ Smart JD-aware fallback questions")
# #     print("✅ http://localhost:5000")
# #     app.run(port=5000, debug=True)


# from flask import Flask, request, jsonify, redirect, send_file
# from flask_cors import CORS
# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# import time
# import io
# import requests
# from gtts import gTTS
# import uuid
# import base64
# import hashlib

# load_dotenv()

# app = Flask(__name__)
# CORS(app, resources={r"/*": {
#     "origins": "*",
#     "methods": ["GET", "POST", "OPTIONS"],
#     "allow_headers": ["Content-Type"]
# }})
# CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500"])

# app.before_request
# def handle_preflight():
#     """✅ FIXES OPTIONS 404 ERROR"""
#     if request.method == 'OPTIONS':
#         response = jsonify({'status': 'ok'})
#         response.headers['Access-Control-Allow-Origin'] = '*'
#         response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
#         response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
#         return response

# # Zoom Setup
# ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
# ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID") 
# ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None

# def get_zoom_access_token():
#     """Generate Zoom Server-to-Server OAuth token"""
#     if not all([ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET]):
#         return None
    
#     token_url = "https://api.zoom.us/oauth/token"
#     timestamp = str(int(time.time()))
    
#     message = f"{ZOOM_CLIENT_ID}{ZOOM_ACCOUNT_ID}{ZOOM_CLIENT_SECRET}{timestamp}"
#     signature = base64.b64encode(
#         hashlib.sha256(message.encode()).digest()
#     ).decode()
    
#     headers = {
#         'Authorization': f'Basic {base64.b64encode(f"{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}".encode()).decode()}',
#         'Content-Type': 'application/x-www-form-urlencoded'
#     }
    
#     data = {
#         'grant_type': 'account_credentials',
#         'account_id': ZOOM_ACCOUNT_ID
#     }
    
#     response = requests.post(token_url, headers=headers, data=data)
#     if response.status_code == 200:
#         return response.json().get('access_token')
#     return None

# def create_zoom_meeting(topic="AI Technical Interview", duration=60):
#     """Create real Zoom meeting and return join URL"""
#     token = get_zoom_access_token()
#     if not token:
#         # Fallback WebRTC room
#         meeting_id = str(uuid.uuid4())[:8]
#         return meeting_id, f"http://localhost:5000/interview/{meeting_id}"
    
#     url = "https://api.zoom.us/v2/users/me/meetings"
#     headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
#     payload = {
#         "topic": topic,
#         "type": 2,
#         "start_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
#         "duration": duration,
#         "settings": {
#             "host_video": True,
#             "participant_video": True,
#             "join_before_host": True,
#             "mute_upon_entry": False,
#             "watermark": False,
#             "waiting_room": False
#         }
#     }
    
#     response = requests.post(url, headers=headers, json=payload)
#     if response.status_code == 201:
#         data = response.json()
#         return data['id'], data['join_url']
    
#     # Fallback
#     return "fallback123", "http://localhost:5000/interview/fallback"

# def generate_questions(job_desc, resume=""):
#     """Generate AI questions (Groq or smart fallback)"""
#     if client:
#         try:
#             response = client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",
#                 messages=[{
#                     "role": "user", 
#                     "content": f"Generate 6 interview questions for: {job_desc}. JSON only: {{\"questions\":[{{\"id\":1,\"text\":\"Q?\",\"category\":\"tech\"}}]}}"
#                 }],
#                 temperature=0.3
#             )
#             content = response.choices[0].message.content if response.choices else ""
#             # Simple JSON extract
#             start = content.find('{')
#             end = content.rfind('}') + 1
#             if start > -1 and end > start:
#                 return json.loads(content[start:end]).get('questions', [])
#         except:
#             pass
    
#     # Smart fallback
#     words = job_desc.lower().split()[:3]
#     return [
#         {"id":1,"text":f"Experience with {words[0]} in production?","category":"technical"},
#         {"id":2,"text":"Most challenging project?","category":"behavioral"},
#         {"id":3,"text":"Performance optimization approach?","category":"technical"},
#         {"id":4,"text":"Deployment process?","category":"technical"},
#         {"id":5,"text":"Learning new tech under pressure?","category":"behavioral"},
#         {"id":6,"text":"Code review process?","category":"technical"}
#     ]

# @app.route('/')
# @app.route('/index.html')
# def home():
#     return '''
#     <!DOCTYPE html>
#     <html>
#     <head><title>🚀 AI Zoom Interviewer</title>
#     <style>
#         *{margin:0;padding:0;box-sizing:border-box}
#         body{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:white;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
#         .container{max-width:600px;width:100%;background:rgba(255,255,255,0.05);backdrop-filter:blur(20px);border-radius:25px;padding:40px;border:1px solid rgba(0,212,255,0.3);box-shadow:0 25px 50px rgba(0,0,0,0.5)}
#         h1{text-align:center;font-size:2.5em;background:linear-gradient(45deg,#00d4ff,#ff6b6b);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:30px}
#         .form-group{margin-bottom:25px}
#         label{display:block;margin-bottom:10px;color:#00d4ff;font-weight:600}
#         textarea{width:100%;height:120px;padding:20px;border:2px solid rgba(0,212,255,0.3);border-radius:15px;background:rgba(255,255,255,0.05);color:white;font-size:16px;font-family:inherit;resize:vertical;transition:all 0.3s}
#         textarea:focus{outline:none;border-color:#00d4ff;box-shadow:0 0 20px rgba(0,212,255,0.4)}
#         input[type="text"]{width:100%;padding:20px;border:2px solid rgba(0,212,255,0.3);border-radius:15px;background:rgba(255,255,255,0.05);color:white;font-size:16px}
#         .btn{display:block;width:100%;padding:20px;font-size:1.3em;font-weight:600;background:linear-gradient(45deg,#00d4ff,#0099cc);color:white;border:none;border-radius:15px;cursor:pointer;transition:all 0.3s;margin-top:20px;box-shadow:0 10px 30px rgba(0,212,255,0.4)}
#         .btn:hover{transform:translateY(-3px);box-shadow:0 15px 40px rgba(0,212,255,0.6)}
#         .status{padding:15px;border-radius:10px;margin:20px 0;font-weight:500;text-align:center}
#         .zoom-status{background:rgba(0,212,255,0.2);border:1px solid #00d4ff}
#     </style>
#     </head>
#     <body>
#         <div class="container">
#             <h1>🤖 AI Zoom Interviewer</h1>
#             <div class="status zoom-status">
#                 {'✅ Zoom API' if ZOOM_ACCOUNT_ID else '⚠️ Add Zoom credentials to .env'}
#             </div>
            
#             <form id="interviewForm">
#                 <div class="form-group">
#                     <label>📋 Job Description</label>
#                     <textarea name="jobDescription" placeholder="Senior React Developer - TypeScript, Next.js, 3+ years production..." required>Senior React Developer
# TypeScript + Next.js required
# 3+ years production experience
# Performance optimization essential</textarea>
#                 </div>
                
#                 <div class="form-group">
#                     <label>👤 Candidate Name</label>
#                     <input type="text" name="candidateName" placeholder="John Doe" value="John Doe">
#                 </div>
                
#                 <button type="submit" class="btn">🚀 Generate Questions → Join Zoom Meeting</button>
#             </form>
#         </div>
        
#         <script>
#             document.getElementById('interviewForm').onsubmit = async (e) => {{
#                 e.preventDefault();
#                 const formData = new FormData(e.target);
#                 const btn = e.target.querySelector('.btn');
                
#                 btn.textContent = '🎯 Creating AI Questions...';
#                 btn.disabled = true;
                
#                 try {{
#                     // 1. Generate AI questions
#                     const questionsRes = await fetch('/api/generate-questions', {{
#                         method: 'POST',
#                         headers: {{'Content-Type': 'application/json'}},
#                         body: JSON.stringify(Object.fromEntries(formData))
#                     }});
#                     const questionsData = await questionsRes.json();
                    
#                     // 2. Create interview → Get Zoom redirect
#                     const interviewRes = await fetch('/api/start-zoom-interview', {{
#                         method: 'POST',
#                         headers: {{'Content-Type': 'application/json'}},
#                         body: JSON.stringify({{
#                             questions: questionsData.questions,
#                             candidateName: formData.get('candidateName')
#                         }})
#                     }});
#                     const interviewData = await interviewRes.json();
                    
#                     // 3. REDIRECT TO ZOOM
#                     btn.textContent = '🚀 Redirecting to Zoom...';
#                     window.location.href = interviewData.zoom_join_url;
                    
#                 }} catch (error) {{
#                     btn.textContent = '❌ Error - Try Again';
#                     btn.disabled = false;
#                     console.error('Error:', error);
#                 }}
#             }};
#         </script>
#     </body>
#     </html>
#     '''

# @app.route('/api/generate-questions', methods=['POST', 'OPTIONS'])
# def generate_question():
#     if request.method == 'OPTIONS': return jsonify({"ok": True})
    
#     data = request.get_json() or {}
#     questions = generate_questions(data.get('jobDescription', ''), data.get('resumeText', ''))
#     return jsonify({"questions": questions})

# @app.route('/api/start-zoom-interview', methods=['POST', 'OPTIONS'])
# def start_zoom_interview():
#     """🎯 ONE CLICK: Generate questions → Create Zoom → REDIRECT"""
#     if request.method == 'OPTIONS': return jsonify({"ok": True})
    
#     data = request.get_json() or {}
#     job_desc = data.get('jobDescription', 'Technical Interview')
#     candidate_name = data.get('candidateName', 'Candidate')
#     questions = data.get('questions', [])
    
#     print(f"🎤 Starting Zoom interview for {candidate_name}")
    
#     # Create Zoom meeting
#     meeting_id, zoom_join_url = create_zoom_meeting(
#         f"AI Interview: {candidate_name} - {job_desc[:30]}", 
#         45  # 45 minutes
#     )
    
#     # Save session
#     interview_id = str(uuid.uuid4())[:8].upper()
#     active_interviews[interview_id] = {
#         'zoom_meeting_id': meeting_id,
#         'zoom_join_url': zoom_join_url,
#         'candidate': candidate_name,
#         'questions': questions,
#         'current_question': 0,
#         'start_time': time.time()
#     }
    
#     print(f"✅ Zoom created: {meeting_id}")
#     return jsonify({
#         "interviewId": interview_id,
#         "zoom_join_url": zoom_join_url,
#         "status": "ready"
#     })

# active_interviews = {}

# @app.route('/interview/<interview_id>')
# def ai_zoom_interview_room(interview_id):
#     """AI-controlled interview room with speech questions"""
#     session = active_interviews.get(interview_id)
#     if not session:
#         return "Interview not found", 404
    
#     current_q = session['questions'][0]['text'] if session['questions'] else "Ready to begin"
    
#     return f'''
#     <!DOCTYPE html>
#     <html>
#     <head>
#         <title>AI Zoom Interview - {session['candidate']}</title>
#         <style>
#             body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:Arial;padding:20px;margin:0}}
#             .container{{max-width:1200px;margin:0 auto}}
#             .videos{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin:30px 0}}
#             video{{width:100%;height:350px;background:#0f0f23;border-radius:20px;border:3px solid #00d4ff}}
#             .ai-area{{background:rgba(22,33,62,0.95);padding:50px;border-radius:25px;margin:30px 0;text-align:center}}
#             .question{{font-size:2.2em;color:#00d4ff;margin-bottom:30px;line-height:1.5}}
#             .status{{padding:25px;border-radius:15px;margin:20px 0;font-size:1.3em;font-weight:bold;background:rgba(255,255,255,0.1)}}
#             .status.recording{{background:linear-gradient(45deg,#ff4444,#cc0000);animation:pulse 1s infinite}}
#             button{{padding:22px 45px;font-size:1.4em;border:none;border-radius:15px;cursor:pointer;margin:15px;transition:all 0.3s;font-weight:600}}
#             .record-btn{{background:linear-gradient(45deg,#ff4444,#cc0000);color:white;box-shadow:0 10px 30px rgba(255,68,68,0.4)}}
#             .record-btn.recording{{animation:pulse 1s infinite}}
#             .next-btn{{background:linear-gradient(45deg,#00d4ff,#0099cc);color:white;box-shadow:0 10px 30px rgba(0,212,255,0.4)}}
#             @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.6}}}}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <h1 style="text-align:center">🤖 AI Technical Interview</h1>
#             <div class="videos">
#                 <div><h3 style="margin-bottom:15px">🤖 AI Interviewer</h3><video id="aiVideo" autoplay muted></video></div>
#                 <div><h3 style="margin-bottom:15px">{session['candidate']}</h3><video id="candidateVideo" autoplay playsinline muted></video></div>
#             </div>
            
#             <div class="ai-area">
#                 <div class="question">{current_q}</div>
#                 <div class="status" id="status">🎤 AI will speak question → Click Record (2 minutes)</div>
#                 <button id="recordBtn" class="record-btn">🎤 Record Answer</button>
#                 <audio id="questionAudio" autoplay></audio>
#             </div>
#         </div>
        
#         <script>
#             let stream, recorder, chunks=[], interviewId='{interview_id}';
            
#             navigator.mediaDevices.getUserMedia({{
#                 video:{{width:640,height:480,facingMode:'user'}},
#                 audio:{{echoCancellation:true,noiseSuppression:true}}
#             }}).then(s => {{
#                 stream = s;
#                 document.getElementById('candidateVideo').srcObject = s;
#                 createAI();
#                 speakQuestion();
#             }});
            
#             function createAI() {{
#                 const canvas=document.createElement('canvas');
#                 canvas.width=640;canvas.height=360;
#                 const ctx=canvas.getContext('2d');
#                 document.getElementById('aiVideo').srcObject=canvas.captureStream(30);
#                 let frame=0;
#                 function animate() {{
#                     ctx.fillStyle='#1a1a2e';ctx.fillRect(0,0,640,360);
#                     ctx.fillStyle='#00d4ff';
#                     ctx.beginPath();
#                     ctx.arc(320,180,90+Math.sin(frame*0.1)*15,0,Math.PI*2);
#                     ctx.fill();
#                     ctx.fillStyle='#16213e';
#                     ctx.fillRect(295,230,50,30+Math.sin(frame*0.3)*15);
#                     frame++;requestAnimationFrame(animate);
#                 }}
#                 animate();
#             }}
            
#             function speakQuestion() {{
#                 const audio=document.getElementById('questionAudio');
#                 const q=document.querySelector('.question').textContent;
#                 audio.src=`/api/tts-question/1?text=`+encodeURIComponent(q);
#             }}
            
#             document.getElementById('recordBtn').onclick=() => {{
#                 const mime=MediaRecorder.isTypeSupported('audio/webm')?'audio/webm':'audio/mp4';
#                 recorder=new MediaRecorder(stream,{{mimeType:mime}});
#                 chunks=[];
#                 recorder.ondataavailable=e=>chunks.push(e.data);
#                 recorder.onstop=upload;
#                 recorder.start(1000);
                
#                 document.getElementById('recordBtn').disabled=true;
#                 document.getElementById('recordBtn').classList.add('recording');
#                 document.getElementById('status').textContent='🔴 Recording (2:00)';
#                 document.getElementById('status').className='status recording';
                
#                 let time=120;
#                 const timer=setInterval(() => {{
#                     time--;
#                     const m=Math.floor(time/60),s=time%60;
#                     document.getElementById('status').textContent=`🔴 Recording (${m}:${s.toString().padStart(2,'0')})`;
#                     if(time<=0){{clearInterval(timer);recorder.stop();}}
#                 }},1000);
#             }};
            
#             function upload() {{
#                 const blob=new Blob(chunks,{{type:'audio/webm'}});
#                 const form=new FormData();
#                 form.append('audio',blob,'answer.webm');
#                 fetch(`/api/save-answer/${interviewId}`,{{method:'POST',body:form}})
#                 .then(r=>r.json()).then(data=>{{document.getElementById('status').textContent='✅ Saved! Interview complete.';}});
#             }}
#         </script>
#     </body>
#     </html>'''

# @app.route('/api/save-answer/<interview_id>', methods=['POST'])
# def save_answer(interview_id):
#     session = active_interviews.get(interview_id)
#     if session:
#         audio = request.files.get('audio')
#         if audio:
#             os.makedirs("recordings", exist_ok=True)
#             filename = f"{interview_id}_{int(time.time())}.webm"
#             audio.save(f"recordings/{filename}")
#             print(f"✅ Zoom answer saved: {filename}")
#     return jsonify({"status": "saved"})

# @app.route('/api/tts-question/<int:qid>')
# def tts_question(qid):
#     text = request.args.get('text', 'Please answer clearly')
#     tts = gTTS(text=text[:180], lang='en')
#     buffer = io.BytesIO()
#     tts.write_to_fp(buffer)
#     buffer.seek(0)
#     return send_file(buffer, mimetype='audio/mpeg', as_attachment=True)

# if __name__ == '__main__':
#     os.makedirs("recordings", exist_ok=True)
#     print("🚀 AI Zoom Interviewer")
#     print("✅ Zoom:", "LIVE" if ZOOM_ACCOUNT_ID else "FALLBACK")
#     print("✅ http://localhost:5000")
#     app.run(port=5000, debug=True)

# import uuid
# active_interviews = {}

# @app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
# def create_interview():
#     """✅ FULLY CORS-SAFE - No more 404 errors"""
#     if request.method == 'OPTIONS':
#         return jsonify({"status": "ok"})
    
#     try:
#         data = request.get_json() or {}
#         questions = data.get('questions', [])
#         candidate_name = data.get('candidateName', 'Candidate')
        
#         if not questions:
#             return jsonify({"error": "No questions provided"}), 400
        
#         # Create interview session
#         interview_id = str(uuid.uuid4())[:8].upper()
#         active_interviews[interview_id] = {
#             'id': interview_id,
#             'candidate': candidate_name,
#             'questions': questions,
#             'current_question': 0,
#             'answers': [],
#             'status': 'active'
#         }
        
#         print(f"🎤 Interview {interview_id} created ({len(questions)} questions)")
#         return jsonify({
#             "interviewId": interview_id,
#             "joinUrl": f"http://localhost:5000/interview/{interview_id}",
#             "status": "created"
#         })
        
#     except Exception as e:
#         print(f"❌ Create interview error: {e}")
#         return jsonify({"error": "Server error"}), 500


from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv
import uuid
import json
import re
import requests

load_dotenv()
app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5500", "https://zoom-ai-interviewer-production.up.railway.app/", "https://zoom-ai-interviewer-production.up.railway.app/"])

# 🔥 ULTIMATE CORS CONFIGURATION
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "Authorization"]
}})

# ✅ WORKING MODELS (Jan 2026) - Multiple fallbacks
WORKING_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192", 
    "llama-3.1-70b-versatile",
    "mixtral-8x7b-32768"
]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = None

if GROQ_API_KEY:
    client = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    print("✅ GROQ client initialized")

client = OpenAI(api_key=os.getenv("GROQ_API_KEY"), base_url="https://api.groq.com/openai/v1") if os.getenv("GROQ_API_KEY") else None
active_interviews = {}

def safe_groq_call(prompt, max_retries=2):
    print("""✅ BULLETPROOF Groq API call with ALL error handling""")
    print(f"Client : {client}")
    if not client:
        return None
    
    for model in WORKING_MODELS:
        try:
            print(f"🔄 Trying model: {model}")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Return ONLY valid JSON: {\"questions\": [{\"id\":1,\"text\":\"question\",\"category\":\"technical\"}]} NO markdown, no explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            # ✅ FIXED: SAFE response parsing
            if (hasattr(response, 'choices') and 
                isinstance(response.choices, list) and 
                len(response.choices) > 0 and 
                hasattr(response.choices[0], 'message') and 
                hasattr(response.choices[0].message, 'content')):
                
                content = response.choices[0].message.content.strip()
                print(f"✅ SUCCESS with {model}: {content[:60]}...")
                
                # Extract JSON
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        questions = result.get('questions', [])
                        if questions:
                            return questions
                    except json.JSONDecodeError:
                        pass
            
        except Exception as e:
            print(f"❌ {model} failed: {str(e)[:80]}")
            continue
    
    return None

# Safe imports with fallbacks
try:
    from openai import OpenAI
    HAS_OPENAI = True
except:
    HAS_OPENAI = False

@app.route('/api/health')
def health():
    return jsonify({
        "status": "Zoom AI Interviewer LIVE ✅",
        "openai": HAS_OPENAI,
        "port": os.getenv('PORT', 5000)
    })

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    """Serve React app - handles all frontend routes"""
    static_path = app.static_folder
    if path != "" and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(static_path, 'index.html')

@app.route('/api/generate-questions', methods=['POST', 'OPTIONS'])
def generate_questions():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    data = request.get_json() or {}
    job_description = data.get('jobDescription', '').strip()
    resume_text = data.get('resumeText', '').strip()
    
    print(f"📥 JD: {job_description[:60]}...")
    
    if not job_description:
        return jsonify({"error": "Job description required"}), 400
    
    # Try Groq first
    prompt = f"""Job: {job_description}
Resume: {resume_text or 'None'}

Generate 6 targeted interview questions. Return ONLY JSON."""
    
    questions = safe_groq_call(prompt)
    print(f"AI questions : {questions}")
    if questions: 
        print(f"✅ Generated {len(questions)} AI questions")
        return jsonify({"questions": questions})
    
    # ✅ SMART FALLBACK - No errors, always works
    print("🔄 Using smart fallback")
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

# ✅ PERSISTENT STORAGE
INTERVIEWS_FILE = "interviews.json"

def load_interviews():
    """Load interviews from file"""
    global active_interviews
    if os.path.exists(INTERVIEWS_FILE):
        try:
            with open(INTERVIEWS_FILE, 'r') as f:
                active_interviews.update(json.load(f))
            print(f"✅ Loaded {len(active_interviews)} interviews")
        except:
            print("⚠️ Corrupted interviews file, starting fresh")

def save_interviews():
    """Save interviews to file"""
    try:
        with open(INTERVIEWS_FILE, 'w') as f:
            json.dump(active_interviews, f, indent=2)
    except Exception as e:
        print(f"⚠️ Save failed: {e}")

# ✅ LOAD ON STARTUP
load_interviews()

@app.route('/api/create-interview', methods=['POST', 'OPTIONS'])
def create_interview():
    if request.method == 'OPTIONS':
        print("✅ OPTIONS request handled")
        return jsonify({"status": "ok"}), 200
    
    print("✅ POST /api/create-interview HIT!")
    data = request.get_json() or {}
    questions = data.get('questions', [])
    candidate_name = data.get('candidateName', 'Candidate')
    
    interview_id = str(uuid.uuid4())[:8].upper()
    active_interviews[interview_id] = {
        'id': interview_id,
        'candidate': candidate_name,
        'questions': questions,
        'current_question': 0
    }
    
    print(f"🎤 Interview {interview_id} created!")
    return jsonify({
        "interviewId": interview_id,
        "joinUrl": f"/interview/{interview_id}"
    })

# @app.route('/interview/<interview_id>')
# def interview_room(interview_id):
#     print("Enter Interview Room1")
#     session = active_interviews.get(interview_id)
#     print("Session1:", session)
#     return f"Interview room for {session['candidate'] if session else 'NOT FOUND'}"


@app.route('/interview/<interview_id>')
def ai_interview_room(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text'] if current_q < len(session['questions']) else "🎉 Interview Complete!"
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 AI Interview - {session['candidate']}</title>
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;font-family:Arial,sans-serif;min-height:100vh;padding:20px}}.container{{max-width:1200px;margin:0 auto}}.videos{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}}.video-container{{background:rgba(15,15,35,0.8);border-radius:15px;padding:15px;border:2px solid #00d4ff}}.question-area{{background:rgba(22,33,62,0.95);padding:30px;border-radius:20px;margin:20px 0;text-align:center;border:2px solid #00d4ff}}.status{{padding:15px;border-radius:10px;margin:15px 0;font-weight:600}}.recording{{background:#ff4444;color:white}}.button{{padding:15px 30px;font-size:1.1em;border:none;border-radius:10px;cursor:pointer;margin:10px}}.record-btn{{background:#ff4444;color:white}}.next-btn{{background:#00d4ff;color:white}}.q-counter{{position:absolute;top:20px;right:20px;background:rgba(0,212,255,0.2);padding:10px;border-radius:10px}}</style>
</head>
<body>
    <div class="container">
        <div class="q-counter">Q{current_q + 1}/{len(session['questions'])}</div>
        <h1 style="text-align:center;font-size:2.5em;margin-bottom:20px">🤖 AI Interview - {session['candidate']}</h1>
        
        <div class="videos">
            <div class="video-container">
                <h3 style="color:#00d4ff;margin-bottom:10px">🤖 AI Interviewer</h3>
                <video id="aiVideo" width="100%" height="300" style="border-radius:10px;background:#0f0f23" autoplay muted></video>
            </div>
            <div class="video-container">
                <h3 style="color:#ff6b6b;margin-bottom:10px">👤 You</h3>
                <video id="candidateVideo" width="100%" height="300" autoplay muted playsinline style="border-radius:10px;background:#0f0f23"></video>
            </div>
        </div>
        
        <div class="question-area">
            <div style="font-size:1.8em;color:#00d4ff;margin-bottom:20px">{question}</div>
            <div class="status" id="status">🔄 Initializing camera...</div>
            <div>
                <button id="askBtn" class="button record-btn" disabled>🎤 AI Ask Question</button>
                <button id="recordBtn" class="button record-btn" disabled>🔴 Record Answer (60s)</button>
                <button id="nextBtn" class="button next-btn" disabled>Next →</button>
            </div>
        </div>
    </div>
    
    <script>
        // ✅ GLOBAL VARIABLES - Accessible EVERYWHERE
        const interviewId = "{interview_id}";
        const currentQuestionIndex = {current_q};
        let mediaStream = null;
        let recorder = null;
        let chunks = [];
        
        // 1. Initialize Camera
        navigator.mediaDevices.getUserMedia({{
            video: {{width: 640, height: 480, facingMode: "user"}},
            audio: true
        }}).then(function(stream) {{
            mediaStream = stream;
            document.getElementById("candidateVideo").srcObject = stream;
            createAnimatedAI();
            document.getElementById("status").textContent = "✅ Ready! Click AI Ask Question";
            document.getElementById("askBtn").disabled = false;
        }}).catch(function(e) {{
            document.getElementById("status").innerHTML = "❌ Camera/mic required";
        }});
        
        // 2. AI Animation
        function createAnimatedAI() {{
            const video = document.getElementById("aiVideo");
            const canvas = document.createElement("canvas");
            canvas.width = 640; canvas.height = 360;
            const ctx = canvas.getContext("2d");
            video.srcObject = canvas.captureStream(30);
            
            let frame = 0;
            function animate() {{
                ctx.fillStyle = "#1a1a2e"; ctx.fillRect(0, 0, 640, 360);
                const radius = 80 + Math.sin(frame * 0.1) * 8;
                const gradient = ctx.createRadialGradient(320, 180, 0, 320, 180, radius);
                gradient.addColorStop(0, "#00d4ff"); gradient.addColorStop(1, "rgba(0,212,255,0.3)");
                ctx.fillStyle = gradient; ctx.beginPath(); ctx.arc(320, 180, radius, 0, Math.PI*2); ctx.fill();
                ctx.fillStyle = "#16213e"; ctx.fillRect(300, 220, 40, 20 + Math.sin(frame * 0.3) * 10);
                frame++; requestAnimationFrame(animate);
            }}
            animate();
        }}
        
        // 3. AI Ask Question (TTS)
        document.getElementById("askBtn").onclick = function() {{
            const utterance = new SpeechSynthesisUtterance("{question}");
            utterance.rate = 0.9; utterance.pitch = 1.1;
            speechSynthesis.speak(utterance);
            
            document.getElementById("status").textContent = "🎤 Question asked! Ready to record.";
            document.getElementById("recordBtn").disabled = false;
            document.getElementById("askBtn").style.display = "none";
        }};
        
        // 4. Record Answer
        document.getElementById("recordBtn").onclick = function() {{
            if (!mediaStream) return alert("No camera");
            
            recorder = new MediaRecorder(mediaStream);
            chunks = [];
            recorder.ondataavailable = function(e) {{ chunks.push(e.data); }};
            recorder.onstop = uploadAnswer;  // ✅ Calls GLOBAL uploadAnswer()
            
            recorder.start(250);
            
            let timeLeft = 60;
            const status = document.getElementById("status");
            status.textContent = "🔴 Recording (1:00)";
            status.className = "recording";
            
            const timer = setInterval(function() {{
                timeLeft--;
                const minutes = Math.floor(timeLeft / 60);
                const seconds = timeLeft % 60;
                status.textContent = "🔴 Recording (" + minutes + ":" + seconds.toString().padStart(2,"0") + ")";
                
                if (timeLeft <= 0) {{
                    clearInterval(timer);
                    recorder.stop();
                }}
            }}, 1000);
        }};
        
        // 5. ✅ FIXED UPLOAD - Uses GLOBAL VARIABLES
        function uploadAnswer() {{
            const questionNum = currentQuestionIndex + 1;  // ✅ GLOBAL currentQuestionIndex
            const filename = "answer_q" + questionNum + "_" + interviewId + ".webm";  // ✅ String concat
            const blob = new Blob(chunks, {{type: "video/webm"}});
            const formData = new FormData();
            formData.append("video", blob, filename);
            
            fetch("/api/submit-answer/" + interviewId, {{
                method: "POST",
                body: formData
            }})
            .then(function(r) {{ return r.json(); }})
            .then(function(data) {{
                document.getElementById("status").textContent = "✅ Answer saved! Next question ready.";
                document.getElementById("status").className = "status";
                document.getElementById("recordBtn").style.display = "none";
                document.getElementById("nextBtn").disabled = false;
            }});
        }}
        
        // 6. Next Question
        document.getElementById("nextBtn").onclick = function() {{ 
            window.location.reload(); 
        }};

        // Put this at BOTTOM of your <script> section
        window.addEventListener('load', async function() {{
            const statusEl = document.getElementById("status");
            const videoEl = document.getElementById("candidateVideo");
            
            try {{
                // ✅ Show permission request
                statusEl.textContent = "🎥 Requesting camera access...";
                
                // ✅ Better constraints
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{
                        width: {{ ideal: 640 }},
                        height: {{ ideal: 480 }},
                        facingMode: {{ ideal: "user" }}  // Front camera
                    }},
                    audio: {{
                        echoCancellation: true,
                        noiseSuppression: true
                    }}
                }});
                
                // ✅ Assign stream
                mediaStream = stream;
                videoEl.srcObject = stream;
                videoEl.play();  // ✅ Force play
                
                statusEl.textContent = "✅ Camera ready! 🎤 Click AI Ask Question";
                document.getElementById("askBtn").disabled = false;
                createAnimatedAI();
                
            }} catch (error) {{
                console.error("❌ FULL ERROR:", error);
                statusEl.innerHTML = `❌ Camera failed: <strong>${{error.name}}</strong><br>${{error.message}}`;
            }}
        }});
    </script>
</body>
</html>'''



def create_zoom_meeting(interview_id, candidate_name):
    """Create Zoom meeting for interview"""
    if not ZOOM_API_KEY or not ZOOM_API_SECRET:
        return {"meetingId": "fake-123-456-789", "joinUrl": f"/zoom-fake/{interview_id}"}
    
    url = "https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {get_zoom_token()}",
        "Content-Type": "application/json"
    }
    data = {
        "topic": f"AI Interview - {candidate_name}",
        "type": 2,  # Scheduled
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "cloud",
            "meeting_recording": {"recording_type": "audio_only"}
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    meeting = response.json()
    
    # Store meeting info
    active_interviews[interview_id]["zoom"] = {
        "meetingId": meeting["id"],
        "joinUrl": meeting["join_url"],
        "password": meeting.get("password", "")
    }
    save_interviews()
    
    return active_interviews[interview_id]["zoom"]

def get_zoom_token():
    """Generate Zoom JWT token"""
    import jwt
    import calendar
    payload = {
        'iss': ZOOM_API_KEY,
        'exp': calendar.timegm(time.gmtime()) + 3600
    }
    return jwt.encode(payload, ZOOM_API_SECRET, algorithm='HS256')

@app.route('/api/create-zoom-interview/<interview_id>', methods=['POST'])
def create_zoom_interview(interview_id):
    """Create Zoom meeting for existing interview"""
    session = active_interviews.get(interview_id)
    if not session:
        return jsonify({"error": "Interview not found"}), 404
    
    zoom_info = create_zoom_meeting(interview_id, session['candidate'])
    
    return jsonify({
        "zoomMeetingId": zoom_info["meetingId"],
        "joinUrl": zoom_info["joinUrl"],
        "interviewId": interview_id
    })

@app.route('/interview/<interview_id>')
def ai_zoom_interview(interview_id):
    session = active_interviews.get(interview_id)
    if not session:
        return "❌ Interview not found", 404
    
    current_q = session['current_question']
    question = session['questions'][current_q]['text']
    
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Zoom AI Interview - {session['candidate']}</title>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/react.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/react-dom.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/redux.min.js"></script>
    <script src="https://source.zoom.us/2.18.2/lib/vendor/redux-thunk.min.js"></script>
    <script src="https://source.zoom.us/zoom-meeting-2.18.2.min.js"></script>
    <style>
        body{{margin:0;background:#1a1a2e;color:white;font-family:Arial,sans-serif;overflow:hidden}}
        #meetingSDKElement{{flex:1;height:100vh}}
        .sidebar{{position:fixed;right:20px;top:20px;width:350px;background:rgba(26,26,46,0.95);padding:20px;border-radius:15px;border:2px solid #00d4ff;max-height:80vh;overflow-y:auto}}
        .question{{font-size:1.4em;color:#00d4ff;margin-bottom:20px;padding:15px;background:rgba(0,212,255,0.1);border-radius:10px}}
        .controls{{display:flex;gap:10px;margin-top:20px;flex-wrap:wrap}}
        button{{padding:12px 24px;border:none;border-radius:8px;cursor:pointer;font-weight:600;flex:1;min-width:120px}}
        .ask-btn{{background:#00d4ff;color:white}}
        .next-btn{{background:#ff6b6b;color:white}}
        .next-btn:disabled{{opacity:0.5;background:#666}}
        .status{{padding:10px;border-radius:8px;margin:10px 0;font-weight:500}}
        .recording{{background:#ff4444 !important;color:white !important}}
        .q-counter{{position:fixed;top:20px;left:20px;background:rgba(0,212,255,0.2);padding:10px;border-radius:10px;font-weight:bold}}
    </style>
</head>
<body>
    <div class="q-counter">Q{current_q + 1}/{len(session['questions'])}</div>
    
    <!-- Zoom Meeting Container -->
    <div id="meetingSDKElement"></div>
    
    <!-- AI Agent Sidebar -->
    <div class="sidebar">
        <h2 style="color:#00d4ff;margin-bottom:15px">🤖 AI Interview Agent</h2>
        <div class="question">{question}</div>
        <div class="status" id="status">🔄 Ready to start Zoom meeting</div>
        <div class="controls">
            <button id="joinZoom" class="ask-btn">🎥 Join Zoom Meeting</button>
            <button id="askQuestion" class="ask-btn" disabled>🎤 AI Ask Question</button>
            <button id="nextQuestion" class="next-btn" disabled>Next Question →</button>
        </div>
        <div id="recordingStatus" style="margin-top:15px;display:none">
            <div class="status recording">🔴 Recording Answer...</div>
        </div>
    </div>
    
    <script>
        const interviewId = "{interview_id}";
        let client;
        let meeting;
        
        // ✅ 1. Initialize Zoom SDK
        document.getElementById("joinZoom").onclick = function() {{
            const status = document.getElementById("status");
            status.textContent = "🔄 Creating Zoom meeting...";
            
            fetch("/api/create-zoom-interview/" + interviewId, {{method:"POST"}})
            .then(r => r.json())
            .then(function(zoomData) {{
                status.textContent = "🎥 Starting Zoom meeting...";
                
                // Zoom SDK Config
                client = ZoomMtgEmbedded.createClient();
                let meetingConfig = {{
                    apiKey: "YOUR_ZOOM_SDK_KEY",  // Get from Zoom Marketplace
                    apiSecret: "YOUR_ZOOM_SDK_SECRET",
                    meetingNumber: parseInt(zoomData.zoomMeetingId),
                    password: "",
                    role: 0,
                    userName: "{session['candidate']}",
                    userEmail: "",
                    lang: "en-US",
                    signature: "",  // Generate server-side
                    china: false
                }};
                
                client.init({{
                    zoomAppRoot: document.getElementById("meetingSDKElement"),
                    language: "en-US",
                    customize: {{
                        videoHeader: "AI Interview"
                    }}
                }}).then(() => {{
                    client.join(meetingConfig).then(() => {{
                        status.textContent = "✅ In Zoom! AI will ask question now.";
                        status.className = "status";
                        document.getElementById("askQuestion").disabled = false;
                        document.getElementById("joinZoom").style.display = "none";
                    }});
                }});
            }});
        }};
        
        // ✅ 2. AI Agent Asks Question (TTS + Zoom Audio)
        document.getElementById("askQuestion").onclick = function() {{
            const status = document.getElementById("status");
            status.textContent = "🤖 AI asking question...";
            status.className = "status recording";
            
            // TTS in Zoom (plays through meeting audio)
            const utterance = new SpeechSynthesisUtterance(document.querySelector(".question").textContent);
            utterance.rate = 0.9; utterance.pitch = 1.0;
            speechSynthesis.speak(utterance);
            
            // Auto-start Zoom cloud recording
            setTimeout(() => {{
                document.getElementById("recordingStatus").style.display = "block";
                status.textContent = "🎤 Recording your answer (60 seconds)";
            }}, 3000);
            
            // Auto-next after 60 seconds
            setTimeout(() => {{
                document.getElementById("nextQuestion").disabled = false;
                status.textContent = "✅ Answer recorded! Ready for next.";
            }}, 65000);
        }};
        
        // ✅ 3. Next Question
        document.getElementById("nextQuestion").onclick = function() {{
            fetch("/api/next-question/" + interviewId, {{method:"POST"}})
            .then(() => window.location.reload());
        }};
    </script>
</body>
</html>'''

@app.route('/api/next-question/<interview_id>', methods=['POST'])
def next_question(interview_id):
    """Advance to next question"""
    session = active_interviews.get(interview_id)
    if session:
        session['current_question'] += 1
        save_interviews()
        print(f"➡️ {interview_id}: Q{session['current_question']}")
    return jsonify({"status": "next"})

# Zoom recording webhook (optional)
@app.route('/api/zoom-recording', methods=['POST'])
def zoom_recording_webhook():
    data = request.json
    print("📹 Zoom recording complete:", data)
    return jsonify({"status": "received"})

ZOOM_ACCOUNT_ID = os.getenv("ZOOM_ACCOUNT_ID")
ZOOM_CLIENT_ID = os.getenv("ZOOM_CLIENT_ID")
ZOOM_CLIENT_SECRET = os.getenv("ZOOM_CLIENT_SECRET")

def get_zoom_access_token():
    """Get Server-to-Server OAuth token"""
    url = f"https://zoom.us/oauth/token"
    headers = {"Authorization": f"Basic {base64.b64encode(f'{ZOOM_CLIENT_ID}:{ZOOM_CLIENT_SECRET}'.encode()).decode()}"}
    data = {
        "grant_type": "account_credentials",
        "account_id": ZOOM_ACCOUNT_ID
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json()["access_token"]

def create_zoom_meeting(interview_id, candidate_name):
    """✅ Uses Client ID/Secret (NOT API Key)"""
    token = get_zoom_access_token()
    
    url = f"https://api.zoom.us/v2/users/me/meetings"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "topic": f"AI Interview - {candidate_name} [{interview_id}]",
        "type": 1,  # Instant meeting
        "settings": {
            "host_video": True,
            "participant_video": True,
            "auto_recording": "local"
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    meeting = response.json()
    
    active_interviews[interview_id]["zoom"] = {
        "meetingId": meeting["id"],
        "joinUrl": meeting["join_url"],
        "password": meeting.get("password", "")
    }
    save_interviews()
    
    return active_interviews[interview_id]["zoom"]


@app.route('/api/submit-answer/<interview_id>', methods=['POST', 'OPTIONS'])
def submit_answer(interview_id):
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})
    
    session = active_interviews.get(interview_id)
    if session:
        video_file = request.files.get('video')  # ✅ Changed from 'audio' to 'video'
        if video_file:
            os.makedirs("recordings", exist_ok=True)
            filename = video_file.filename
            filepath = f"recordings/{filename}"
            video_file.save(filepath)
            
            session['answers'].append({
                'question_id': session['current_question'] + 1,
                'filename': filename,
                'type': 'video'
            })
            session['current_question'] += 1
            save_interviews()
            
            print(f"✅ Saved VIDEO: {filename}")
    
    return jsonify({"status": "saved"})


@app.route('/api/tts-question/<int:qid>')
def tts_question(qid):
    text = request.args.get('text', 'Please answer this question.')
    try:
        from gtts import gTTS
        import io
        tts = gTTS(text=text[:200], lang='en')
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        return send_file(buffer, mimetype='audio/mpeg')
    except:
        return "TTS unavailable", 500


if __name__ == '__main__':
    print("🚀 Backend running on http://localhost:5000")
    app.run(port=5000, debug=True)

@app.route('/debug')
def debug():
    """🔍 DEBUG - Check active interviews"""
    return jsonify({
        "active_interviews": list(active_interviews.keys()),
        "count": len(active_interviews)
    })
