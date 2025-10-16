# Ilaro Community Suggestion Box

A Flask-based web application for community suggestions with AI-powered categorization, summarization, sentiment analysis, and duplicate detection.

## Features

- **Public Suggestion Submission**: Users can submit suggestions with optional anonymity.
- **AI-Powered Processing**: Automatic categorization, summarization, and sentiment analysis using Gemini, Groq, OpenRouter, or RapidFuzz fallbacks.
- **Duplicate Detection**: Prevents duplicates by comparing semantic similarity using AI or text similarity, auto-upvoting existing suggestions.
- **Public Feed**: View approved suggestions with sorting, filtering, and voting.
- **Admin Dashboard**: Secure login to manage suggestions, announcements, landmark images, community areas, and view analytics.
- **Announcements**: Image carousel and marquee for urgent news.
- **Data Export**: Export suggestions to CSV or Excel.

## Setup

1. **Clone or Download** the project.

2. **Create Virtual Environment**:
   ```
   python -m venv venv
   ```

3. **Activate Virtual Environment**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

4. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

5. **Set Environment Variables** (optional for AI features):
   Copy `.env.example` to `.env` and fill in your API keys:
   ```
   cp .env.example .env
   ```
   - `GEMINI_API_KEY`: For Google Gemini API
   - `GROQ_API_KEY`: For Groq API
   - `OPENROUTER_API_KEY`: For OpenRouter API
   - `SECRET_KEY`: For Flask sessions (default provided)

6. **Create Database and Admin User**:
   ```
   python create_admin.py
   ```

7. **Seed Sample Data (Optional)**:
   ```
   python seed_data.py
   ```

7. **Run the Application**:
   ```
   python run.py
   ```

   Access at `http://localhost:5000`

## Admin Access

- Username: `admin`
- Password: `admin123`
- Login at `/admin/login`

### Admin Features

- **Suggestion Management**: Approve, reject, merge, and track suggestion status
- **Announcement Management**: Create and manage community announcements
- **Landmark Images**: Upload and manage community landmark photos
- **Community Areas**: Add, edit, activate/deactivate, and delete community areas
- **Analytics Dashboard**: View charts and statistics about community engagement
- **Data Export**: Export suggestions to CSV or Excel formats
- **AI Metrics**: Monitor AI service performance and usage

## API Keys

- **Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Groq**: Get from [Groq Console](https://console.groq.com/)
- **OpenRouter**: Get from [OpenRouter](https://openrouter.ai/)

Without keys, the app falls back to keyword-based categorization and text similarity.

## Project Structure

```
/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # Database models
│   ├── ai.py                # AI processing functions
│   ├── routes.py            # Public routes
│   └── admin_routes.py      # Admin routes
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── submit.html
│   ├── feed.html
│   └── admin/
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── suggestions.html
│       ├── announcements.html
│       ├── announcement_form.html
│       ├── landmarks.html
│       └── landmark_form.html
├── static/                  # Static files (CSS, JS, images)
├── uploads/                 # Uploaded images
├── run.py                   # Entry point
├── create_admin.py          # Admin user creation
└── README.md
```

## Extending Features

- **Add More Categories**: Update `categorize` function in `ai.py`
- **Custom AI Models**: Modify fallback chain in AI functions
- **Email Notifications**: Integrate Flask-Mail for admin alerts
- **User Registration**: Add user model and registration routes
- **API Endpoints**: Expose REST API for mobile apps

## Technologies

- Flask
- SQLAlchemy
- Flask-Login
- Bootstrap 5
- Chart.js
- Google Generative AI
- Groq
- OpenRouter
- RapidFuzz
- Pandas