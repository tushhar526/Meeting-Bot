# Meeting Bot Backend

A comprehensive meeting automation backend that handles calendar integration, meeting transcription, summarization, and webhook management.

## 🚀 Features

- **Multi-Platform Calendar Integration**: Google Meet, Zoom, Microsoft Teams
- **Automated Meeting Transcription**: Real-time audio processing and transcription
- **AI-Powered Summaries**: Intelligent meeting summaries using LangChain and Ollama
- **Webhook Management**: Handle platform-specific webhooks for meeting events
- **User Authentication**: JWT-based authentication with role-based access control
- **Task Scheduling**: Automated meeting scheduling and reminders
- **Audio Processing**: Support for various audio formats and streaming

## 🏗️ Architecture

### Core Components

- **Flask Web Framework**: RESTful API with CORS support
- **SQLAlchemy Database**: ORM with SQLite/PostgreSQL support
- **Celery Task Queue**: Asynchronous task processing
- **Redis**: Message broker and caching
- **JWT Authentication**: Token-based authentication system

### Key Services

- **CalendarService**: Multi-platform calendar integration
- **TranscriptionService**: Audio transcription and processing
- **SummaryService**: AI-powered meeting summaries
- **SchedulerService**: Automated meeting scheduling
- **WebhookService**: Platform webhook handling

## 📋 Requirements

### System Requirements

- Python 3.11+
- Redis Server
- FFmpeg (for audio processing)
- Docker (optional, for containerized deployment)

### Python Dependencies

See `requirements.txt` for complete list. Key dependencies include:

- Flask 3.1.2
- SQLAlchemy 2.0.46
- Celery 5.6.2
- Redis 7.1.0
- LangChain 1.2.14
- Ollama 0.6.1
- Playwright 1.58.0
- PyJWT 2.11.0

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Meeting-Bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start Redis server**
   ```bash
   redis-server
   ```

6. **Initialize database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

7. **Start Celery worker**
   ```bash
   celery -A app.celery_app:celery worker --loglevel=info &
   ```

8. **Run the application**
   ```bash
   python run.py
   ```

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
SQLALCHEMY_DATABASE_URI=sqlite:///meeting_bot.db
SQLALCHEMY_TRACK_MODIFICATIONS=False

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRES=1
JWT_REFRESH_TOKEN_EXPIRES=30
JWT_TOKEN_LOCATION=cookies
JWT_COOKIE_SECURE=False
JWT_COOKIE_SAMESITE=Lax
JWT_COOKIE_CSRF_PROTECT=False

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Calendar Integrations
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ZOOM_CLIENT_ID=your-zoom-client-id
ZOOM_CLIENT_SECRET=your-zoom-client-secret
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# AI/LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LANGCHAIN_API_KEY=your-langchain-api-key
LANGSMITH_TRACING=true

# Application
SECRET_KEY=your-app-secret-key
```

## 📚 API Documentation

### Authentication Endpoints

- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - User logout

### Calendar Endpoints

- `GET /calendar/connect` - Connect calendar service
- `POST /calendar/webhook` - Handle calendar webhooks
- `GET /calendar/events` - List calendar events

### Meeting Endpoints

- `POST /bot/join` - Join a meeting
- `POST /bot/leave` - Leave a meeting
- `GET /bot/status` - Get bot status

### Transcription Endpoints

- `POST /transcript/upload` - Upload audio for transcription
- `GET /transcript/{id}` - Get transcription by ID
- `GET /transcript/meeting/{meeting_id}` - Get meeting transcriptions

### Summary Endpoints

- `POST /summary/generate` - Generate meeting summary
- `GET /summary/{id}` - Get summary by ID
- `GET /summary/meeting/{meeting_id}` - Get meeting summaries

## 🔄 Task Queue

The application uses Celery for background task processing:

### Available Tasks

- **Transcription Tasks**: Process audio files and generate transcriptions
- **Summary Tasks**: Generate AI-powered meeting summaries
- **Bot Tasks**: Handle meeting bot operations

### Monitoring

- **Flower**: Celery monitoring tool (optional)
- **Redis CLI**: Monitor queue status

## 🐳 Docker Configuration

### Dockerfile Features

- Python 3.11-slim base image
- Audio processing dependencies (FFmpeg, PulseAudio)
- Browser automation (Playwright with Chromium)
- Multi-stage build for optimization
- Non-root user for security

### Docker Compose

- Single service deployment
- Volume mounting for development
- Port mapping (5000:5000)
- Audio device access for meeting bot functionality

## 🧪 Testing

### Running Tests

```bash
# Run unit tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=app tests/
```

### Test Structure

- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Test fixtures and data

## 📊 Monitoring & Logging

### Logging Configuration

- File logging: `app.log`
- Console logging for development
- Structured logging format
- Log levels: INFO, WARNING, ERROR

### Health Checks

- Database connectivity
- Redis connection
- Celery worker status
- External API integrations

## 🔒 Security

### Authentication & Authorization

- JWT token-based authentication
- Role-based access control (User, Admin, SuperAdmin)
- CSRF protection
- Secure cookie configuration

### Data Protection

- Environment variable encryption
- Database connection security
- API key management
- Input validation and sanitization

## 🚀 Deployment

### Production Considerations

- Use PostgreSQL for production database
- Configure Redis clustering for scalability
- Set up reverse proxy (Nginx)
- Enable SSL/TLS encryption
- Configure monitoring and alerting

### Environment-Specific Configurations

- Development: SQLite, local Redis
- Staging: PostgreSQL, Redis cluster
- Production: PostgreSQL HA, Redis cluster

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue in the repository
- Check the documentation in `readmeDocs/`
- Review the API documentation

## 🔄 Version History

- **v1.0.0**: Initial release with basic meeting bot functionality
- **v1.1.0**: Added multi-platform calendar integration
- **v1.2.0**: Enhanced transcription and summary features
- **v1.3.0**: Improved webhook handling and scheduling

---

**Note**: This is an active development project. Features and APIs may change as development progresses.
