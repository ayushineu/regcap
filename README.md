# 🧠 RegCap GPT: AI-Powered Regulatory Intelligence Assistant

**RegCap GPT** is a specialized AI Agent designed to help professionals interpret, analyze, and interact with complex regulatory documents. Built with OpenAI's GPT-4o and vector search, it enables smart question answering, visual explanations, and persistent session-based workflows for regulatory compliance and documentation use cases.

---

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

## 📌 Roadmap (Coming Soon)
- Document metadata filtering
- Citations for document-derived answers
- Admin interface for analytics and usage stats
- Enterprise version with user-level permissions

---

## 📜 AI Ethics

RegCap GPT was developed with a focus on responsible AI use.  
Read our [AI_ETHICS.md](./AI_ETHICS.md) to learn more about the principles guiding this project.

---

## 🧠 Built With

- [OpenAI GPT-4o](https://platform.openai.com/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Streamlit](https://streamlit.io/)
- [Mermaid.js](https://mermaid.js.org/)
- [Bootstrap](https://getbootstrap.com/)

---

## 💼 Author

**Ayushi, FRSA**  
FinTech Strategist | RegTech Innovator | Judge for AI & Technology Awards  
[LinkedIn](https://www.linkedin.com/in/ayushi-ayushi)

---

## 📄 License

This project is licensed under the MIT License — see the `LICENSE` file for details.
