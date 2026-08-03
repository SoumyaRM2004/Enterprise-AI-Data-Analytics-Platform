# Enterprise AI Data Analytics Platform

A full-stack enterprise-grade data analytics platform built with **Django REST API + React**, featuring AI-powered natural language querying, automatic data preprocessing, interactive dashboards, ML forecasting, PDF report generation, and background task processing.

---

## Architecture

```
React (Vite) ─── Axios/Fetch ─── Django REST Framework ─── PostgreSQL
     │                    │                    │                    │
     │                    │                    │              Celery + Redis
     │                    │                    │
     │                    └── Configurable LLM Providers
     │                       (Gemini / OpenAI / Ollama / OpenRouter)
     │
     └── JWT Authentication ─── Role-Based Access ─── Audit Logs
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, Vite, TypeScript, Tailwind CSS, Chart.js, Zustand |
| **Backend** | Django 5, Django REST Framework, JWT Auth |
| **Database** | PostgreSQL 16 |
| **Cache/Queue** | Redis 7, Celery |
| **Data Processing** | Pandas, NumPy, scikit-learn, statsmodels |
| **AI/LLM** | Configurable providers (Gemini, OpenAI, Ollama, OpenRouter) |
| **Visualization** | Chart.js (frontend), Plotly/Matplotlib (backend) |
| **Reports** | ReportLab (PDF generation) |
| **Deployment** | Docker, Docker Compose, Nginx, Gunicorn |

## Features

### Core Features (MVP)
- **JWT Authentication** — Registration, login, token refresh, role-based access
- **Dataset Upload** — CSV, XLSX, XLS, TSV support with automatic parsing
- **Auto Preprocessing** — Null handling, type detection, outlier removal, deduplication
- **Data Profiling** — Column statistics, null percentages, unique counts, correlations
- **Interactive Dashboard** — KPI cards, dynamic charts, data tables
- **AI Chatbot** — ChatGPT-style interface for natural language data querying
- **NL-to-SQL** — Converts natural language questions to SQL queries
- **Interactive Charts** — Bar, line, pie, scatter, histogram visualizations

### Advanced Features
- **ML Forecasting** — ARIMA, SARIMAX, Holt-Winters, Prophet models
- **Anomaly Detection** — Isolation Forest, Z-Score, IQR methods
- **PDF Reports** — Professional reports with KPIs, charts, and AI insights
- **Scheduled Reports** — Daily/weekly/monthly email delivery via Celery
- **Audit Logs** — Complete action tracking with IP addresses
- **REST API** — Swagger/OpenAPI documentation
- **Dataset Versioning** — Track data changes over time
- **Data Quality Score** — Automated quality assessment

### AI Integration
- **Configurable LLM Providers** — Switch between Gemini, OpenAI, Ollama, OpenRouter
- **Context-Aware Responses** — AI understands dataset schema and statistics
- **Multi-Modal Output** — Text, SQL, charts, tables, forecasts
- **Conversation Memory** — Maintains context across chat sessions

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for local development)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd analytics-platform

# Copy environment template
cp .env.example .env

# Edit environment variables
# Set your LLM provider and API keys
```

### 2. Environment Variables

```bash
# Django
SECRET_KEY=your-super-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://analytics_user:analytics_pass@db:5432/analytics_platform

# Redis
REDIS_URL=redis://redis:6379/0

# LLM Provider
LLM_PROVIDER=openai_compatible
# Options: openai, gemini, ollama, openrouter, openai_compatible

# OpenAI Compatible (default - works with Ollama/local models)
OPENAI_API_BASE=http://host.docker.internal:11434/v1
OPENAI_API_KEY=not-needed-for-local

# OpenAI (if using GPT)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# Gemini
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=your-gemini-key

# Email (for scheduled reports)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. Deploy with Docker

```bash
chmod +x deploy.sh
./deploy.sh
```

Or manually:

```bash
docker compose build
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d
```

### 4. Access the Platform

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api |
| Admin Panel | http://localhost:8000/admin |
| API Docs | http://localhost:8000/api/docs/ |

**Default credentials:** admin / admin123

---

## Local Development

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A config worker -l info

# Start Celery beat (separate terminal)
celery -A config beat -l info
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Running Services Separately

You need three terminal sessions:

```bash
# Terminal 1 - PostgreSQL
docker run -d --name analytics_db \
  -e POSTGRES_DB=analytics_platform \
  -e POSTGRES_USER=analytics_user \
  -e POSTGRES_PASSWORD=analytics_pass \
  -p 5432:5432 postgres:16

# Terminal 2 - Redis
docker run -d --name analytics_redis -p 6379:6379 redis:7-alpine

# Terminal 3 - Backend
cd backend && python manage.py runserver

# Terminal 4 - Celery
cd backend && celery -A config worker -l info

# Terminal 5 - Frontend
cd frontend && npm run dev
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register/` | Register new user |
| POST | `/api/auth/login/` | Login (returns JWT) |
| POST | `/api/auth/login/token/refresh/` | Refresh token |
| GET | `/api/auth/profile/` | Get user profile |
| PATCH | `/api/auth/profile/` | Update profile |
| POST | `/api/auth/change-password/` | Change password |
| POST | `/api/auth/logout/` | Logout (blacklist token) |

### Datasets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/datasets/` | List datasets |
| POST | `/api/datasets/upload/` | Upload dataset |
| GET | `/api/datasets/:id/` | Get dataset details |
| DELETE | `/api/datasets/:id/` | Delete dataset |
| GET | `/api/datasets/:id/profile/` | Get data profile |
| GET | `/api/datasets/:id/versions/` | Get version history |
| POST | `/api/datasets/:id/cleaning/` | Run cleaning job |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/dashboard/:dataset_id/` | Dashboard data |
| GET | `/api/analytics/dashboard/:dataset_id/chart/` | Chart data |
| POST | `/api/analytics/dashboard/:dataset_id/query/` | Execute SQL query |
| GET | `/api/analytics/widgets/` | List dashboard widgets |
| POST | `/api/analytics/widgets/` | Create widget |

### AI Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chatbot/sessions/` | List chat sessions |
| POST | `/api/chatbot/sessions/` | Create session |
| POST | `/api/chatbot/sessions/:id/send/` | Send message |
| GET | `/api/chatbot/providers/` | List LLM providers |

### Forecasting
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/forecasting/` | List models |
| POST | `/api/forecasting/:dataset_id/create/` | Create forecast |
| POST | `/api/forecasting/:dataset_id/anomalies/` | Detect anomalies |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/reports/` | List reports |
| POST | `/api/reports/:dataset_id/generate/` | Generate report |
| GET | `/api/reports/:id/download/` | Download PDF |
| POST | `/api/reports/scheduled/` | Create schedule |

---

## LLM Provider Configuration

The platform supports multiple AI providers through a unified interface:

```python
# In .env file
LLM_PROVIDER=gemini  # or: openai, ollama, openrouter, openai_compatible
```

| Provider | Description | Setup |
|----------|-------------|-------|
| `openai_compatible` | Any OpenAI-compatible API (default) | Set `OPENAI_API_BASE` |
| `openai` | OpenAI GPT-4/GPT-3.5 | Set `OPENAI_API_KEY` |
| `gemini` | Google Gemini | Set `GEMINI_API_KEY` |
| `ollama` | Local Ollama models | Set `OLLAMA_BASE_URL` |
| `openrouter` | OpenRouter multi-model | Set `OPENROUTER_API_KEY` |

### Adding a New Provider

1. Create provider class in `backend/chatbot/llm_provider.py`
2. Register in `LLMProviderFactory`
3. Add environment variables to `.env.example`

---

## Database Schema

```
├── accounts_user          # Custom user model with roles
├── accounts_auditlog      # Audit trail
├── datasets_dataset       # Uploaded datasets + metadata
├── datasets_project       # Project grouping
├── datasets_uploadedfile  # File storage
├── datasets_cleaningjob   # Data cleaning tasks
├── datasets_dataversion   # Version history
├── analytics_widget       # Dashboard widgets
├── analytics_report       # Saved report configs
├── analytics_savedquery   # Saved SQL queries
├── chatbot_chatsession    # Chat sessions
├── chatbot_chatmessage    # Messages with metadata
├── forecasting_forecastmodel  # ML forecast models
├── forecasting_anomalyresult  # Anomaly detection results
├── reports_report         # Generated PDF reports
└── reports_scheduledreport    # Email schedules
```

---

## Celery Tasks

| Task | Description | Trigger |
|------|-------------|---------|
| `process_dataset_task` | Upload processing + profiling | On upload |
| `clean_dataset_task` | Run data cleaning pipeline | On cleaning request |
| `generate_report_task` | Create PDF report | On report request |
| `create_forecast_task` | Train and run forecast model | On forecast creation |
| `detect_anomalies_task` | Run anomaly detection | On anomaly request |
| `check_and_send_scheduled_reports` | Send scheduled reports | Every 30 min |
| `cleanup_old_reports` | Clean old reports (>90 days) | Daily |

---

## Project Structure

```
analytics-platform/
├── backend/
│   ├── accounts/          # Auth, users, roles, audit logs
│   │   ├── models.py      # CustomUser, AuditLog
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── datasets/          # Dataset management
│   │   ├── models.py      # Dataset, Project, UploadedFile, CleaningJob
│   │   ├── views.py
│   │   ├── tasks.py       # Celery processing tasks
│   │   └── urls.py
│   ├── analytics/         # Data processing & visualization
│   │   ├── engine.py      # DataProcessor class
│   │   ├── chart_generator.py  # Chart creation
│   │   ├── sql_engine.py  # Pandas SQL executor
│   │   ├── models.py
│   │   └── views.py
│   ├── chatbot/           # AI chat & NL-to-SQL
│   │   ├── engine.py      # ChatbotEngine
│   │   ├── llm_provider.py  # Configurable providers
│   │   ├── models.py
│   │   └── views.py
│   ├── forecasting/       # ML forecasting
│   │   ├── engine.py      # ForecastingEngine
│   │   ├── models.py
│   │   └── views.py
│   ├── reports/           # PDF reports & scheduling
│   │   ├── generator.py   # ReportLab PDF generator
│   │   ├── models.py
│   │   ├── tasks.py       # Report generation tasks
│   │   └── views.py
│   ├── config/            # Django settings
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── celery.py
│   │   └── wsgi.py
│   ├── Dockerfile
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # MainLayout, shared components
│   │   ├── pages/         # Login, Dashboard, Chat, Reports, etc.
│   │   ├── services/      # API service layer
│   │   ├── utils/         # Zustand stores
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── deploy.sh
├── .env.example
└── README.md
```

---

## Security Features

- **JWT Authentication** with access/refresh token rotation
- **Token Blacklisting** for secure logout
- **Role-Based Access Control** (Admin, Analyst, Viewer)
- **Input Sanitization** on all SQL queries
- **File Upload Validation** (type, size, content)
- **Audit Logging** for all sensitive operations
- **CORS Configuration** for API security
- **Environment Variables** for sensitive configuration

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `python manage.py test`
4. Submit a pull request

---

## License

MIT License

---

## Acknowledgments

Built with Django, React, and open-source AI models.
