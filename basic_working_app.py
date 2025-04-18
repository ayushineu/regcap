"""
Basic Working App - Simplified RegCap Interface

A bare-bones version of the application with minimal JavaScript and CSS
to ensure everything works correctly. This version strips down all complex
features and focuses on making sure the core UI elements work.
"""

from flask import Flask, render_template_string, session, request, jsonify
import uuid
import time
import threading

app = Flask(__name__)
app.secret_key = "basic-app-secret-key"

# Simple in-memory storage
chat_history = []
question_status = {}

@app.route('/')
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
    <title>Basic Working App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .tabs {
            display: flex;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            background-color: #f1f1f1;
            margin-right: 5px;
        }
        .tab.active {
            background-color: #007bff;
            color: white;
        }
        .tab-content {
            border: 1px solid #ddd;
            padding: 20px;
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 5px;
        }
        .user-message {
            background-color: #007bff;
            color: white;
            margin-left: 20%;
        }
        .bot-message {
            background-color: #f1f1f1;
            margin-right: 20%;
        }
        #chatContainer {
            height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin-bottom: 20px;
        }
        #questionForm {
            display: flex;
        }
        #questionInput {
            flex-grow: 1;
            padding: 8px;
            margin-right: 10px;
        }
        #submitButton {
            padding: 8px 15px;
            background-color: #007bff;
            color: white;
            border: none;
            cursor: pointer;
        }
        #darkModeToggle {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 5px 10px;
            background-color: #333;
            color: white;
            border: none;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Basic Working App</h1>
        <button id="darkModeToggle">Dark Mode</button>
        
        <div class="tabs">
            <div class="tab active" id="chatTab">Chat</div>
            <div class="tab" id="documentsTab">Documents</div>
            <div class="tab" id="sessionsTab">Sessions</div>
        </div>
        
        <div class="tab-content active" id="chatContent">
            <h2>Chat</h2>
            <div id="chatContainer">
                {% for msg in chat_history %}
                    <div class="message {{msg.type}}">
                        <strong>{{msg.sender}}:</strong> {{msg.text}}
                    </div>
                {% endfor %}
            </div>
            <div id="questionForm">
                <input type="text" id="questionInput" placeholder="Ask a question...">
                <button id="submitButton">Send</button>
            </div>
        </div>
        
        <div class="tab-content" id="documentsContent">
            <h2>Documents</h2>
            <p>You can upload documents here.</p>
            <input type="file" id="documentUpload" multiple>
            <button id="uploadButton">Upload</button>
        </div>
        
        <div class="tab-content" id="sessionsContent">
            <h2>Sessions</h2>
            <p>You can manage your sessions here.</p>
            <button id="newSessionButton">New Session</button>
        </div>
    </div>
    
    <script>
        // Simple tab switching functionality
        document.getElementById('chatTab').addEventListener('click', function() {
            switchTab('chatContent');
            document.getElementById('chatTab').classList.add('active');
            document.getElementById('documentsTab').classList.remove('active');
            document.getElementById('sessionsTab').classList.remove('active');
        });
        
        document.getElementById('documentsTab').addEventListener('click', function() {
            switchTab('documentsContent');
            document.getElementById('chatTab').classList.remove('active');
            document.getElementById('documentsTab').classList.add('active');
            document.getElementById('sessionsTab').classList.remove('active');
        });
        
        document.getElementById('sessionsTab').addEventListener('click', function() {
            switchTab('sessionsContent');
            document.getElementById('chatTab').classList.remove('active');
            document.getElementById('documentsTab').classList.remove('active');
            document.getElementById('sessionsTab').classList.add('active');
        });
        
        function switchTab(tabId) {
            document.getElementById('chatContent').classList.remove('active');
            document.getElementById('documentsContent').classList.remove('active');
            document.getElementById('sessionsContent').classList.remove('active');
            document.getElementById(tabId).classList.add('active');
        }
        
        // Dark mode toggle
        let darkMode = false;
        document.getElementById('darkModeToggle').addEventListener('click', function() {
            darkMode = !darkMode;
            if (darkMode) {
                document.body.style.backgroundColor = '#222';
                document.body.style.color = '#fff';
                this.innerText = 'Light Mode';
            } else {
                document.body.style.backgroundColor = '';
                document.body.style.color = '';
                this.innerText = 'Dark Mode';
            }
        });
        
        // Question submission
        document.getElementById('submitButton').addEventListener('click', function() {
            submitQuestion();
        });
        
        document.getElementById('questionInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitQuestion();
            }
        });
        
        function submitQuestion() {
            const questionInput = document.getElementById('questionInput');
            const question = questionInput.value.trim();
            
            if (!question) return;
            
            // Add user message to chat
            addMessage('You', question, 'user-message');
            
            // Add processing message
            const processingId = 'msg-' + Date.now();
            addMessage('Bot', 'Processing your question...', 'bot-message', processingId);
            
            // Clear input
            questionInput.value = '';
            
            // Simulate processing
            setTimeout(function() {
                const processingMsg = document.getElementById(processingId);
                if (processingMsg) {
                    processingMsg.innerHTML = '<strong>Bot:</strong> Here is an answer to your question: "' + question + '". In a real app, this would be generated based on your documents.';
                }
            }, 2000);
        }
        
        function addMessage(sender, text, messageType, id) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + messageType;
            messageDiv.innerHTML = '<strong>' + sender + ':</strong> ' + text;
            if (id) {
                messageDiv.id = id;
            }
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        // Document upload simulation
        document.getElementById('uploadButton').addEventListener('click', function() {
            const fileInput = document.getElementById('documentUpload');
            if (fileInput.files.length === 0) {
                alert('Please select at least one file to upload.');
                return;
            }
            
            alert('Simulated upload of ' + fileInput.files.length + ' files. In a real app, these would be processed and stored.');
        });
        
        // New session simulation
        document.getElementById('newSessionButton').addEventListener('click', function() {
            alert('New session created! In a real app, this would start a new knowledge context.');
        });
    </script>
</body>
</html>
    """, chat_history=chat_history)

@app.route('/ask-question', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question', '')
    
    # Generate a question ID
    question_id = str(uuid.uuid4())
    
    # Start processing in a background thread
    threading.Thread(target=process_question, args=(question, question_id)).start()
    
    return jsonify({'success': True, 'question_id': question_id})

def process_question(question, question_id):
    time.sleep(2)  # Simulate processing
    
    answer = f"This is a sample answer to '{question}'"
    
    # Add to chat history
    chat_history.append({
        'sender': 'You',
        'text': question,
        'type': 'user-message'
    })
    chat_history.append({
        'sender': 'Bot',
        'text': answer,
        'type': 'bot-message'
    })
    
    # Update question status
    question_status[question_id] = {
        'done': True,
        'answer': answer
    }

@app.route('/question-status/<question_id>', methods=['GET'])
def get_question_status(question_id):
    if question_id in question_status:
        return jsonify(question_status[question_id])
    return jsonify({'error': 'Question ID not found'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005)