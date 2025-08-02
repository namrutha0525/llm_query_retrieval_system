# LLM-Powered Intelligent Query–Retrieval System

A comprehensive document processing and query-retrieval system powered by Google Gemini LLM, designed for real-world applications in insurance, legal, HR, and compliance domains.

## 🚀 Features

- **Multi-format Document Processing**: Supports PDF documents via Blob URLs
- **Semantic Search**: FAISS-powered vector embeddings for intelligent retrieval  
- **Google Gemini Integration**: Advanced LLM for query understanding and answer generation
- **Explainable AI**: Provides source citations and reasoning for all answers
- **RESTful API**: FastAPI-based with comprehensive documentation
- **Authentication**: Secure token-based authentication
- **Real-time Processing**: Handles multiple queries efficiently

## 🏗️ System Architecture

```
1. Input Documents (PDF Blob URL) 
   ↓
2. LLM Parser (Extract structured query using Gemini)
   ↓  
3. Embedding Search (FAISS/Pinecone retrieval)
   ↓
4. Clause Matching (Semantic similarity)
   ↓
5. Logic Evaluation (Decision processing)
   ↓
6. JSON Output (Structured response)
```

## 📋 Requirements

- Python 3.8+
- Google Gemini API Key
- FastAPI
- FAISS (CPU version)
- Sentence Transformers
- PDF processing libraries

## 🔧 Installation

1. **Clone and setup**:
   ```bash
   cd llm_query_retrieval_system
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   - Copy `.env` file and update with your API keys:
   ```bash
   GEMINI_API_KEY=your-gemini-api-key
   HACKRX_API_TOKEN=your-auth-token
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

   Or use the startup script:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

## 🌐 API Endpoints

### Main Processing Endpoint
```http
POST /api/v1/hackrx/run
Authorization: Bearer <token>
Content-Type: application/json

{
    "documents": "https://example.com/document.pdf",
    "questions": [
        "What is the grace period for premium payment?",
        "What is the waiting period for pre-existing diseases?"
    ]
}
```

### Response Format
```json
{
    "answers": [
        "A grace period of thirty days is provided...",
        "There is a waiting period of thirty-six months..."
    ],
    "detailed_responses": [...],
    "document_id": "doc_12345",
    "processing_time": 2.45
}
```

### Other Endpoints
- `GET /health` - Health check
- `GET /stats` - Service statistics  
- `POST /api/v1/query` - Single query processing
- `DELETE /api/v1/index/clear` - Clear embedding index

## 🔑 Authentication

All API endpoints (except health checks) require authentication:

```http
Authorization: Bearer 479309883e76b7aff59e87e1e032ce655934c42516b75cc1ceaea8663351e3ba
```

## 📖 Usage Examples

### Python Client Example
```python
import requests

url = "http://localhost:8000/api/v1/hackrx/run"
headers = {
    "Authorization": "Bearer 479309883e76b7aff59e87e1e032ce655934c42516b75cc1ceaea8663351e3ba",
    "Content-Type": "application/json"
}

data = {
    "documents": "https://example.com/policy.pdf",
    "questions": [
        "What is the coverage limit?",
        "Are pre-existing conditions covered?"
    ]
}

response = requests.post(url, json=data, headers=headers)
result = response.json()

for i, answer in enumerate(result["answers"]):
    print(f"Q{i+1}: {data['questions'][i]}")
    print(f"A{i+1}: {answer}\n")
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/api/v1/hackrx/run" \
     -H "Authorization: Bearer 479309883e76b7aff59e87e1e032ce655934c42516b75cc1ceaea8663351e3ba" \
     -H "Content-Type: application/json" \
     -d '{
       "documents": "https://example.com/document.pdf",
       "questions": ["What is the waiting period?"]
     }'
```

## 🔬 Technical Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Document Parser** | Extract text from PDFs | pdfplumber, PyPDF2 |
| **Embedding Generator** | Create semantic vectors | Sentence-BERT |
| **Vector Database** | Store and search embeddings | FAISS |
| **LLM Engine** | Query understanding & generation | Google Gemini Pro |
| **API Framework** | RESTful web service | FastAPI |
| **Authentication** | Secure access control | Bearer tokens |

## 📁 Project Structure

```
llm_query_retrieval_system/
├── app/
│   ├── api/
│   │   └── endpoints.py          # API route definitions
│   ├── core/
│   │   ├── auth.py              # Authentication logic
│   │   └── middleware.py        # Custom middleware
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   └── services/
│       ├── gemini_service.py    # Google Gemini integration
│       ├── document_service.py  # Document processing
│       ├── embedding_service.py # Embedding & search
│       └── query_service.py     # Main orchestration
├── config/
│   └── config.py               # Configuration settings
├── data/                       # Data storage (indexes, etc.)
├── tests/                      # Test files
├── main.py                     # FastAPI application
├── requirements.txt            # Dependencies
├── .env                        # Environment variables
└── start.sh                    # Startup script
```

## 🧪 Testing

The system includes comprehensive error handling and logging. Check `app.log` for detailed execution logs.

**Health Check**:
```bash
curl http://localhost:8000/health
```

## 🔒 Security Features

- Token-based authentication
- Request size validation
- Rate limiting middleware
- Input sanitization
- CORS protection
- Comprehensive logging

## 🚀 Production Deployment

For production deployment:

1. Set `reload=False` in `main.py`
2. Use a production WSGI server (Gunicorn + Uvicorn)
3. Configure proper CORS origins
4. Use environment-specific configuration
5. Set up monitoring and logging
6. Consider using Pinecone instead of FAISS for distributed deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the logs in `app.log`
- Review API documentation at `/docs`
- Ensure all environment variables are set correctly
- Verify Google Gemini API key is valid
