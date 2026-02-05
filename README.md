# 🧠 RegCap GPT: AI-Powered Regulatory Intelligence Assistant

**RegCap GPT** is a specialized AI Agent designed to help professionals interpret, analyze, and interact with complex regulatory documents. Built with OpenAI's GPT-4o and vector search, it enables smart question answering, visual explanations, and persistent session-based workflows for regulatory compliance and documentation use cases.

---

🏆 **Featured In**  
- TechBullion: [AI-Powered Compliance Innovation – Ayushi on Building Financial Stability through RegCap GPT](https://techbullion.com/ai-powered-compliance-innovation-ayushi-on-building-financial-stability-through-regcap-gpt/)   
- Medium: [RegCap GPT: Building the Future of AI-Driven Compliance in Financial Services](https://medium.com/@ayushis.nmims/regcap-gpt-building-the-future-of-ai-driven-compliance-in-financial-services-57ea1c4775d0)  
- Winner: 2025 Globee Silver Award for Compliance Management Solutions  [https://credential.globeeawards.com/1f647147-b147-4423-bcdf-fe20563b0d74#acc.mEzXqQcd]

## 🚀 Key Features

### 📄 PDF Document Processing
- Upload and process **multiple PDF documents**
- Automatically extract and chunk text for analysis
- Maintain vectorized representations for fast retrieval

### 🔍 Vector-Based Document Search
- Generate embeddings for document chunks using **OpenAI**
- Build and maintain **FAISS vector stores**
- Retrieve relevant sections dynamically to answer user queries

### 💬 AI-Powered Q&A
- Understand **natural language questions**
- Provide **context-aware answers** based on the uploaded documents
- Use **GPT-4o** for intelligent, human-like response generation

### 📊 Diagram Generation
- Detect requests for **visual explanations**
- Generate **Mermaid.js** diagrams (flowcharts, sequences, etc.)
- View diagrams with inline explanations in a dedicated visual tab

---

## 🧑‍💻 User Interface & Experience

### 🗂️ Multi-Tab Interface
- **Chat**: Interactive Q&A
- **Documents**: Upload/manage PDFs
- **Diagrams**: Browse generated visuals
- **Sessions**: Manage persistent chat/document states

### 💾 Session Management
- Create, switch, and persist multiple sessions
- Conversations, documents, and diagrams are saved per session
- Asynchronous, fast transitions between sessions

### 🌓 UI Enhancements
- **Dark mode toggle** (with OS preference detection)
- Notification badges for new diagrams
- Responsive layout via **Bootstrap**
- Visual indicators for processing/loading states

---

## ⚙️ Technical Highlights

### 📈 Performance Optimizations
- Background workers for long-running tasks
- Auto-refresh mechanisms for pending OpenAI responses
- Retry logic with **exponential backoff** for API failures
- Async Mermaid.js rendering for diagrams

### 🔧 Error Handling
- Graceful fallback mechanisms for API & file processing errors
- Clear, user-friendly error messages

### 🗂️ Data Persistence
- Store conversations, vector stores, diagrams, and document metadata
- Maintain timestamps for session tracking and history management

---

## 🧭 Use Case

**RegCap GPT** is ideal for:
- Regulatory professionals
- Compliance officers
- FinTech analysts
- Legal advisors working with structured regulations

It empowers users to extract actionable insights, generate visual aids, and navigate compliance frameworks without manual overhead.

---

📌** Roadmap & Phased Rollout (2025–2027)**

**Phase 1 (Q4 2025–Q2 2026)**
- CCAR Stress Testing Module  
- SOX Internal Controls Engine  
- AI PDF Parser (RAG)  
- BI Dashboards  

**Phase 2 (Q3 2026–Q2 2027)**
- ISO 20022 Translator  
- Sanctions & AML Screening  
- Compliance API Gateway  
- Cloud SaaS Deployment  

**Phase 3 (Q3–Q4 2027)**
- AI Audit Trail & Anomaly Detection  
- Cybersecurity Monitoring & Alerts  
- Continuous Compliance Notifications  
- Centralized Knowledge Hub  

---

## 📜 AI Ethics

RegCap GPT was developed with a focus on responsible AI use.  
Read our [AI_ETHICS.md](./AI_ETHICS.md) to learn more about the principles guiding this project.

---

## 🧠 Built With

- [OpenAI GPT-4o](https://platform.openai.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Flask](https://flask.palletsprojects.com/)
- [PyPDF2](https://pypdf2.readthedocs.io/)
- [Mermaid.js](https://mermaid.js.org/)
- [Bootstrap](https://getbootstrap.com/)

---

## Getting Started

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ayushineu/regcap.git
   cd regcap
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY='your_api_key_here'
   ```

### Running the Application

1. Start the Flask server:
   ```
   python simplified_app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

---

## 💼 Author

**Ayushi, FRSA**  
FinTech Strategist | RegTech Innovator | Judge for AI & Technology Awards  
[LinkedIn](https://www.linkedin.com/in/ayushi-ayushi)

---

## 📄 License

This project is licensed under the MIT License — see the `LICENSE` file for full terms.

Please note: This repository is intended for **learning, research, and demonstration purposes only**.  
Commercial use, distribution, or deployment of the RegCap GPT platform as a service or product may require **separate written permission** or licensing.


