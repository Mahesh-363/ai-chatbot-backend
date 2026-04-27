# 🤖 AI Chatbot — Production-Ready Django Backend

A production-grade AI chatbot backend built with **Django 5**, **DRF**, **Celery**, **Redis**, and **PostgreSQL**.
Integrates with OpenAI's API, supports rate limiting, background tasks, session-based conversations, and is fully Dockerised.

---

## 🏗️ Architecture

```
┌────────────┐     HTTP      ┌──────────────────────────────────────────────┐
│   Client   │ ────────────► │  Nginx (rate limit + reverse proxy)          │
└────────────┘               └──────────────┬───────────────────────────────┘
                                            │
                             ┌──────────────▼───────────────────────────────┐
                             │  Django API  (Gunicorn / 4 workers)          │
                             │  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
                             │  │ /auth   │  │ /chat    │  │ /analytics │  │
                             │  └─────────┘  └──────────┘  └────────────┘  │
                             └──────┬────────────────────────────┬──────────┘
                                    │                            │
               ┌────────────────────▼──┐          ┌─────────────▼──────────┐
               │  PostgreSQL 16        │          │  Redis 7 (5 DBs)       │
               │  - users              │          │  0: cache              │
               │  - chat_sessions      │          │  1: rate limiting      │
               │  - chat_messages      │          │  2: sessions           │
               │  - summaries          │          │  3: celery broker      │
               └───────────────────────┘          │  4: celery results     │
                                                  └────────────┬───────────┘
                                                               │
                             ┌─────────────────────────────────▼───────────┐
                             │  Celery Workers                              │
                             │  ┌────────────┐  ┌────────────────────────┐ │
                             │  │ AI Worker  │  │ Background Worker      │ │
                             │  │ (Q: ai_)   │  │ (Q: background,        │ │
                             │  │ OpenAI API │  │    analytics, default) │ │
                             │  └────────────┘  └────────────────────────┘ │
                             │  ┌────────────┐                              │
                             │  │ Beat       │ (periodic tasks)             │
                             │  └────────────┘                              │
                             └─────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
ai_chatbot/
├── config/
│   ├── settings/
│   │   ├── base.py           # All shared settings
│   │   ├── development.py    # Dev overrides
│   │   └── production.py     # Prod hardening
│   ├── celery.py             # Celery app + queue routing
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── accounts/             # Custom User model, JWT auth, API keys
│   ├── chat/                 # Sessions, Messages, Celery tasks, Services
│   └── analytics/            # Admin-only usage stats, daily snapshots
├── utils/
│   ├── ai_client.py          # OpenAI wrapper with retries
│   ├── rate_limiter.py       # Redis sliding-window rate limiter
│   ├── throttling.py         # DRF throttle classes
│   ├── pagination.py
│   ├── exceptions.py
│   ├── middleware.py         # Request logging
│   └── views.py              # Health check, API root
├── nginx/
│   └── nginx.conf            # Rate limiting + reverse proxy
├── scripts/
│   ├── entrypoint.sh         # Docker entrypoint
│   └── setup_aws.sh          # EC2 bootstrap script
├── Dockerfile                # Multi-stage build
├── docker-compose.yml        # Full stack: API + Celery + Redis + PG + Nginx
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start (Docker)

```bash
# 1. Clone and configure
git clone https://github.com/YOUR_USERNAME/ai-chatbot.git
cd ai-chatbot
cp .env.example .env
# Edit .env — set OPENAI_API_KEY, SECRET_KEY, DB_PASSWORD

# 2. Start all services
docker-compose up --build -d

# 3. Create a superuser
docker-compose exec api python manage.py createsuperuser

# 4. Test the health endpoint
curl http://localhost/health/
```

---

## 🔌 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register/` | Register new user |
| POST | `/api/v1/auth/login/` | Get JWT tokens |
| POST | `/api/v1/auth/token/refresh/` | Refresh access token |
| POST | `/api/v1/auth/logout/` | Blacklist refresh token |
| GET/PATCH | `/api/v1/auth/profile/` | View / update profile |
| GET/POST/DELETE | `/api/v1/auth/api-key/` | Manage API key |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/v1/chat/sessions/` | List / create sessions |
| GET/PATCH/DELETE | `/api/v1/chat/sessions/<id>/` | Session detail / update / archive |
| GET | `/api/v1/chat/sessions/<id>/messages/` | Paginated message history |
| POST | `/api/v1/chat/sessions/<id>/summarise/` | Trigger background summarisation |
| GET | `/api/v1/chat/sessions/<id>/summary/` | Get AI-generated summary |
| **POST** | **`/api/v1/chat/messages/send/`** | **Send a message → async AI response** |
| GET | `/api/v1/chat/messages/<id>/status/` | Poll for AI response |
| POST | `/api/v1/chat/messages/<id>/feedback/` | Thumbs up/down feedback |

### Analytics (staff only)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/overview/` | Live system metrics |
| GET | `/api/v1/analytics/users/` | Top users by token usage |
| GET | `/api/v1/analytics/snapshots/` | Daily usage history |

---

## 💬 Send Message Flow

```
POST /api/v1/chat/messages/send/
{
  "content": "Explain recursion in Python",
  "session_id": "optional-existing-session-uuid"
}

→ 202 Accepted
{
  "session_id": "...",
  "user_message_id": "...",
  "assistant_message_id": "...",
  "task_id": "celery-task-uuid",
  "status": "processing"
}

# Poll until completed:
GET /api/v1/chat/messages/<assistant_message_id>/status/
→ { "status": "completed", "message": { "content": "...", "total_tokens": 245, ... } }
```

---

## 🔒 Rate Limiting (Layered)

| Layer | Limit |
|-------|-------|
| Nginx (chat endpoint) | 20 req/min burst=5 |
| DRF throttle (burst) | 30/minute |
| DRF throttle (sustained) | 500/day |
| Redis sliding window (per user) | 20/min · 200/hr · 1000/day |

---

## ⚙️ Celery Queue Architecture

| Queue | Workers | Tasks |
|-------|---------|-------|
| `ai_processing` | 4 concurrent | `process_ai_response` |
| `background` | 2 concurrent | `summarize_conversation`, `cleanup_expired_sessions`, `warm_cache` |
| `analytics` | 1 | `generate_daily_report` |
| `default` | 2 | Everything else |

**Periodic tasks (Beat):**
- Every hour: summarise old conversations (30+ messages, no summary)
- Every 30 min: warm Redis cache for active sessions
- Every day: cleanup archived sessions, generate analytics report

---

## ☁️ AWS EC2 Deployment

```bash
# On your EC2 instance (Ubuntu 22.04 / Amazon Linux 2023)
bash scripts/setup_aws.sh

# Recommended EC2 specs:
# - t3.medium (2 vCPU, 4GB) for small-medium load
# - t3.large (2 vCPU, 8GB) for production

# For prod, also set up:
# - RDS PostgreSQL instead of containerised PG
# - ElastiCache Redis instead of containerised Redis
# - ACM SSL certificate + ALB HTTPS termination
# - ECR for container images
# - Systems Manager Parameter Store for secrets
```

---

## 🛠️ Local Development (without Docker)

```bash
# 1. Create virtualenv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Start Redis and Postgres locally
# (or use Docker for just infra)
docker run -d -p 5432:5432 -e POSTGRES_DB=ai_chatbot -e POSTGRES_USER=chatbot_user -e POSTGRES_PASSWORD=chatbot_pass postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# 3. Set env
cp .env.example .env
export DJANGO_SETTINGS_MODULE=config.settings.development

# 4. Migrate and run
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# 5. Start Celery (separate terminals)
celery -A config worker -Q ai_processing -c 2 -l debug
celery -A config worker -Q background,analytics,default -c 1 -l info
celery -A config beat -l info

# 6. Monitor with Flower
celery -A config flower --port=5555
```
