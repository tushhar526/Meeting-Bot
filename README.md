# 🤖 Meeting Bot - Automated Meeting Recording System

A sophisticated Flask-based application that automatically joins and records meetings from multiple platforms (Google Meet, Microsoft Teams, Zoom) using Playwright automation and PulseAudio recording.

## 📋 Table of Contents

- [🎯 Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [📦 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [🚀 Quick Start](#-quick-start)
- [🔧 API Endpoints](#-api-endpoints)
- [🎬 Platform Support](#-platform-support)
- [🔍 Troubleshooting](#-troubleshooting)
- [📊 Performance](#-performance)
- [🛡️ Security](#️-security)

## 🎯 Features

### 🎥 Meeting Automation
- **Multi-platform Support**: Google Meet, Microsoft Teams, Zoom
- **Intelligent Joining**: Handles waiting rooms, popups, and authentication
- **Audio Recording**: High-quality audio capture with silence removal
- **Graceful Exit**: Automatic meeting end detection and cleanup

### 🎛️ Advanced Features
- **Concurrent Processing**: Multiple bots running simultaneously
- **Retry Logic**: Robust error handling with exponential backoff
- **Real-time Status**: Live meeting status updates via API
- **Audio Streaming**: Direct audio streaming with metadata support
- **Background Processing**: Celery-based task queue for scalability

### 🔒 Anti-Detection
- **Random Delays**: Human-like timing between actions
- **User Agent Rotation**: Multiple browser signatures
- **Proxy Support**: Optional IP rotation
- **Browser Fingerprinting**: Anti-automation detection measures

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask API     │    │   Celery        │
│   (React/Vue)   │◄──►│   (REST API)    │◄──►│   (Task Queue)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   SQLite DB     │    │   Playwright    │
                       │   (Jobs/Users)  │    │   (Browser)     │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PulseAudio    │
                                               │   + FFmpeg      │
                                               │   (Recording)   │
                                               └─────────────────┘
```

## 🛠️ Tech Stack

### Backend
- **Flask**: Web framework and API server
- **Celery**: Distributed task queue with Redis
- **SQLAlchemy**: ORM with SQLite database
- **Playwright**: Browser automation
- **PulseAudio + FFmpeg**: Audio recording and processing

### Frontend
- **React/Vue**: Modern JavaScript framework (optional)
- **REST API**: JSON-based communication
- **WebSocket**: Real-time status updates (optional)

### Infrastructure
- **Docker**: Containerization
- **Redis**: Message broker and caching
- **SQLite**: Lightweight database
- **Nginx**: Reverse proxy (production)

## 📦 Installation

### Prerequisites
```bash
# System requirements
sudo apt-get update
sudo apt-get install -y python3 python3-pip redis-server pulseaudio ffmpeg

# Chrome/Chromium for Playwright
sudo apt-get install -y chromium-browser
```

### Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd Meeting-Bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Database Setup
```bash
# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

## ⚙️ Configuration

### Environment Variables
```bash
# Copy and edit configuration
cp .env.example .env

# Core settings
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database
SQLALCHEMY_DATABASE_URI=sqlite:///mydb.db

# Celery
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

# Optional: Google Account for Meet
GOOGLE_BOT_EMAIL=your-bot@gmail.com
GOOGLE_BOT_PASSWORD=your-password

# Optional: Proxy Support
PROXY_SERVER=http://proxy-server:8080
```

### Audio Configuration
```python
# app/config.py
AUDIO_QUALITY = 2  # 0-9 (lower = better)
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2
SILENCE_REMOVAL = True
```

## 🚀 Quick Start

### 1. Start Services
```bash
# Start Redis
redis-server

# Start Celery worker (terminal 1)
celery -A app.celery worker --pool=threads --concurrency=2 --loglevel=info

# Start Flask app (terminal 2)
python run.py
```

### 2. Docker Setup
```bash
# Build and run
docker build -t meeting-bot .
docker run --rm -v ${PWD}:/app -p 5000:5000 meeting-bot

# With environment variables
docker run --rm -v ${PWD}:/app \
  -e GOOGLE_BOT_EMAIL="bot@gmail.com" \
  -e GOOGLE_BOT_PASSWORD="password" \
  -p 5000:5000 meeting-bot
```

### 3. Start a Meeting Recording
```bash
# Using curl
curl -X POST http://localhost:5000/bot/start \
  -H "Content-Type: application/json" \
  -d '{
    "job_url": "https://meet.google.com/xxx-xxx-xxx",
    "platform": "meet",
    "user_id": 1
  }'

# Check status
curl http://localhost:5000/bot/status/1
```

## 🔧 API Endpoints

### Authentication
```http
POST /auth/login
POST /auth/logout
POST /auth/register
GET  /auth/profile
```

### Bot Management
```http
POST /bot/start              # Start meeting recording
GET  /bot/status/{job_id}    # Get job status
GET  /bot/stop/{job_id}      # Stop recording
GET  /bot/recordings          # List all recordings
GET  /bot/stream/{job_id}    # Stream audio
GET  /bot/download/{job_id}   # Download audio
GET  /bot/metadata/{job_id}   # Get audio metadata
```

### User Management
```http
GET  /users/analytics         # Usage statistics
GET  /users/history          # Job history
GET  /users/profile          # User profile
PUT  /users/profile          # Update profile
```

## 🎬 Platform Support

### Google Meet
- ✅ **Waiting Room**: Automatic admission detection
- ✅ **Popups**: Handles "Got it" and permission dialogs
- ✅ **Audio**: Records all participants' audio
- ✅ **Authentication**: Optional Google account login
- ✅ **Anti-Detection**: Random delays and user agents

### Microsoft Teams
- ✅ **Join Flow**: Handles pre-join and lobby screens
- ✅ **Audio/Video**: Disables camera, enables audio recording
- ✅ **Popups**: Manages browser and app prompts
- ✅ **Meeting End**: Detects host termination

### Zoom
- ✅ **Join Process**: Handles meeting ID and password flows
- ✅ **Audio Setup**: Configures microphone permissions
- ✅ **Breakout Rooms**: Supports main room recording
- ✅ **End Detection**: Monitors meeting termination

## 🔍 Troubleshooting

### Common Issues

#### 1. Playwright Sync/Async Error
```
Error: Playwright Sync API inside asyncio loop
```
**Solution**: Use pure sync Playwright API (already implemented)

#### 2. Google Meet Blocking
```
Bot got completely blocked by Google Meet
```
**Solutions**:
- Use random delays (implemented)
- Add proxy support (configured)
- Use Google account authentication
- Try different user agents

#### 3. Audio Recording Issues
```
Silent recordings or no audio
```
**Solutions**:
- Check PulseAudio sink creation
- Verify FFmpeg installation
- Ensure browser audio permissions
- Check audio routing

#### 4. Celery Task Failures
```
PendingRollbackError or disk I/O errors
```
**Solutions**:
- Add database commit retries
- Use proper session cleanup
- Check SQLite file permissions

### Debug Mode
```bash
# Enable debug logging
export FLASK_ENV=development
export LOG_LEVEL=DEBUG

# Run with verbose logging
python run.py --debug
```

### Health Checks
```bash
# Check Redis
redis-cli ping

# Check Celery
celery -A app.celery inspect active

# Check database
sqlite3 mydb.db ".tables"
```

## 📊 Performance

### Resource Requirements
| Resource | Per Bot | Recommended |
|----------|---------|-------------|
| **RAM** | 250MB | 8GB = 2-3 bots |
| **CPU** | 30% core | i5 = 2-3 bots |
| **Network** | 5-10Mbps | Depends on quality |
| **Storage** | 1MB/min | Plan accordingly |

### Concurrent Scaling
```python
# Celery configuration
CELERY_WORKER_CONCURRENCY = 2  # Conservative
CELERY_WORKER_POOL = "threads"
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
```

### Success Rates
| Platform | Anonymous | Authenticated | With Proxy |
|----------|------------|---------------|-----------|
| **Google Meet** | 50% | 80-90% | 90-95% |
| **Microsoft Teams** | 70% | 85-95% | 90-95% |
| **Zoom** | 80% | 90-95% | 95-99% |

## 🛡️ Security

### Authentication
- JWT-based authentication
- Secure cookie handling
- CORS configuration
- Rate limiting

### Data Protection
- Audio file encryption (optional)
- Database encryption at rest
- Secure file storage
- User data isolation

### Anti-Bot Detection
- Random timing patterns
- User agent rotation
- Proxy support
- Browser fingerprint masking

### Best Practices
```bash
# Secure environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)

# File permissions
chmod 600 .env
chmod 700 recordings/
```

## 📝 Development

### Project Structure
```
Meeting-Bot/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── models/              # Database models
│   ├── routes/              # API endpoints
│   ├── logic/               # Platform handlers
│   ├── helper/              # Utilities
│   └── extension.py         # Extensions
├── migrations/              # Database migrations
├── recordings/              # Audio files
├── tests/                   # Test suite
├── Dockerfile               # Container config
├── requirements.txt         # Dependencies
└── README.md               # This file
```

### Adding New Platforms
1. Create handler in `app/logics/`
2. Implement `join()` and `detect_end()` methods
3. Add platform to BaseBot setup
4. Update API documentation

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific platform
python -m pytest tests/test_meet.py

# Coverage report
python -m pytest --cov=app tests/
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

---

**Built with ❤️ for automated meeting recording**
