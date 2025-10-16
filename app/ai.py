import os
import json
import requests
import time
from rapidfuzz import fuzz
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import google.generativeai as genai
from groq import Groq
from .models import AIMetrics
from . import db

def track_ai_metric(operation, provider, success=True, response_time=None, error_message=None):
    """Track AI operation metrics."""
    try:
        metric = AIMetrics(
            operation=operation,
            provider=provider,
            success=success,
            response_time=response_time,
            error_message=error_message
        )
        db.session.add(metric)
        db.session.commit()
    except Exception as e:
        print(f"Failed to track AI metric: {e}")

# API Keys from environment
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

# AI Service Status Tracking
ai_service_status = {
    'gemini': {'available': False, 'last_error': None},
    'groq': {'available': False, 'last_error': None},
    'openrouter': {'available': False, 'last_error': None}
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

def check_ai_service_status():
    """Check the availability of AI services and update status."""
    # Check Gemini
    if GEMINI_API_KEY:
        try:
            # Simple test call
            genai.GenerativeModel('gemini-2.5-flash').generate_content("test")
            ai_service_status['gemini']['available'] = True
            ai_service_status['gemini']['last_error'] = None
        except Exception as e:
            ai_service_status['gemini']['available'] = False
            ai_service_status['gemini']['last_error'] = str(e)
    else:
        ai_service_status['gemini']['available'] = False
        ai_service_status['gemini']['last_error'] = "API key not configured"

    # Check Groq
    if GROQ_API_KEY:
        try:
            # Simple test call
            groq_client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model="llama-3.1-8b-instant",
                max_tokens=1
            )
            ai_service_status['groq']['available'] = True
            ai_service_status['groq']['last_error'] = None
        except Exception as e:
            ai_service_status['groq']['available'] = False
            ai_service_status['groq']['last_error'] = str(e)
    else:
        ai_service_status['groq']['available'] = False
        ai_service_status['groq']['last_error'] = "API key not configured"

    # Check OpenRouter
    if OPENROUTER_API_KEY:
        try:
            # Simple test call
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                json={
                    'model': 'meta-llama/llama-3.1-8b-instruct',
                    'messages': [{'role': 'user', 'content': 'test'}],
                    'max_tokens': 1
                }
            )
            if response.status_code == 200:
                ai_service_status['openrouter']['available'] = True
                ai_service_status['openrouter']['last_error'] = None
            else:
                ai_service_status['openrouter']['available'] = False
                ai_service_status['openrouter']['last_error'] = f"HTTP {response.status_code}"
        except Exception as e:
            ai_service_status['openrouter']['available'] = False
            ai_service_status['openrouter']['last_error'] = str(e)
    else:
        ai_service_status['openrouter']['available'] = False
        ai_service_status['openrouter']['last_error'] = "API key not configured"

    return ai_service_status

def get_ai_status_message():
    """Get a user-friendly message about AI service status."""
    check_ai_service_status()  # Update status

    available_services = [service for service, status in ai_service_status.items() if status['available']]
    unavailable_services = [service for service, status in ai_service_status.items() if not status['available']]

    if not available_services:
        return "⚠️ AI services are currently unavailable. Suggestions will be processed with basic text analysis only."

    if unavailable_services:
        return f"⚠️ Some AI services are unavailable ({', '.join(unavailable_services)}). Using available services for enhanced processing."

    return "✅ All AI services are operational for enhanced suggestion processing."

def get_embedding(text):
    """
    Get embedding vector for text. This service is provided only by Gemini,
    as it's the only configured provider for text embeddings.
    """
    if not GEMINI_API_KEY:
        print("Embedding failed: Gemini API key not configured.")
        return None

    start_time = time.time()
    try:
        result = genai.embed_content(model="models/text-embedding-004", content=text)
        response_time = time.time() - start_time
        track_ai_metric('embedding', 'gemini', True, response_time)
        return result['embedding']
    except Exception as e:
        response_time = time.time() - start_time
        error_message = f"Gemini embedding failed: {e}"
        print(error_message)
        track_ai_metric('embedding', 'gemini', False, response_time, error_message)
        return None

def _get_available_providers():
    """
    Get a randomized list of available AI providers for general tasks.
    'gemini' is excluded as it is reserved for embedding.
    """
    import random
    
    check_ai_service_status()
    
    # Exclude providers that are not configured or unavailable
    providers = ['groq', 'openrouter']
    
    available_providers = [
        p for p in providers
        if ai_service_status.get(p, {}).get('available', False)
    ]
    
    random.shuffle(available_providers)
    return available_providers

def categorize(text):
    """Categorize suggestion into predefined categories using a random available provider."""
    categories = ['Roads', 'Power', 'Water', 'Security', 'Health', 'Education', 'Other']
    prompt = f"Categorize this suggestion into one of: {', '.join(categories)}. Suggestion: {text}"
    
    providers = _get_available_providers()
    
    for provider in providers:
        if provider == 'groq':
            start_time = time.time()
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                response_time = time.time() - start_time
                cat = chat_completion.choices[0].message.content.strip()
                if cat in categories:
                    track_ai_metric('categorize', 'groq', True, response_time)
                    return cat
                else:
                    track_ai_metric('categorize', 'groq', False, response_time, f"Invalid category: {cat}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('categorize', 'groq', False, response_time, str(e))

        elif provider == 'openrouter':
            start_time = time.time()
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json={
                        'model': 'deepseek/deepseek-chat-v3.1:free',
                        'messages': [{'role': 'user', 'content': prompt}]
                    }
                )
                response_time = time.time() - start_time
                if response.status_code == 200:
                    data = response.json()
                    cat = data['choices'][0]['message']['content'].strip()
                    if cat in categories:
                        track_ai_metric('categorize', 'openrouter', True, response_time)
                        return cat
                    else:
                        track_ai_metric('categorize', 'openrouter', False, response_time, f"Invalid category: {cat}")
                else:
                    track_ai_metric('categorize', 'openrouter', False, response_time, f"HTTP {response.status_code}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('categorize', 'openrouter', False, response_time, str(e))
                
    # Fallback if all providers fail
    track_ai_metric('categorize', 'fallback', True, 0.0)
    if 'road' in text.lower(): return 'Roads'
    if 'power' in text.lower() or 'electric' in text.lower(): return 'Power'
    if 'water' in text.lower(): return 'Water'
    if 'security' in text.lower() or 'police' in text.lower(): return 'Security'
    if 'health' in text.lower() or 'hospital' in text.lower(): return 'Health'
    if 'education' in text.lower() or 'school' in text.lower(): return 'Education'
    return 'Other'

def summarize(text):
    """Generate a short 1-2 sentence summary."""
    prompt = f"Summarize this suggestion in 1-2 sentences: {text}"

    providers = _get_available_providers()

    for provider in providers:
        if provider == 'groq':
            start_time = time.time()
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                response_time = time.time() - start_time
                summary = chat_completion.choices[0].message.content.strip()
                track_ai_metric('summarize', 'groq', True, response_time)
                return summary
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('summarize', 'groq', False, response_time, str(e))

        elif provider == 'openrouter':
            start_time = time.time()
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json={
                        'model': 'deepseek/deepseek-chat-v3.1:free',
                        'messages': [{'role': 'user', 'content': prompt}]
                    }
                )
                response_time = time.time() - start_time
                if response.status_code == 200:
                    data = response.json()
                    summary = data['choices'][0]['message']['content'].strip()
                    track_ai_metric('summarize', 'openrouter', True, response_time)
                    return summary
                else:
                    track_ai_metric('summarize', 'openrouter', False, response_time, f"HTTP {response.status_code}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('summarize', 'openrouter', False, response_time, str(e))

    # Fallback if all providers fail
    track_ai_metric('summarize', 'fallback', True, 0.0)
    return ' '.join(text.split()[:30]) + ('...' if len(text.split()) > 30 else '')

def analyze_sentiment(text):
    """Analyze sentiment: Positive, Neutral, Negative."""
    prompt = f"Analyze the sentiment of this suggestion. Respond with only: Positive, Neutral, or Negative. Suggestion: {text}"

    providers = _get_available_providers()

    for provider in providers:
        if provider == 'groq':
            start_time = time.time()
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                response_time = time.time() - start_time
                sent = chat_completion.choices[0].message.content.strip()
                if sent in ['Positive', 'Neutral', 'Negative']:
                    track_ai_metric('sentiment', 'groq', True, response_time)
                    return sent
                else:
                    track_ai_metric('sentiment', 'groq', False, response_time, f"Invalid sentiment: {sent}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('sentiment', 'groq', False, response_time, str(e))

        elif provider == 'openrouter':
            start_time = time.time()
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json={
                        'model': 'deepseek/deepseek-chat-v3.1:free',
                        'messages': [{'role': 'user', 'content': prompt}]
                    }
                )
                response_time = time.time() - start_time
                if response.status_code == 200:
                    data = response.json()
                    sent = data['choices'][0]['message']['content'].strip()
                    if sent in ['Positive', 'Neutral', 'Negative']:
                        track_ai_metric('sentiment', 'openrouter', True, response_time)
                        return sent
                    else:
                        track_ai_metric('sentiment', 'openrouter', False, response_time, f"Invalid sentiment: {sent}")
                else:
                    track_ai_metric('sentiment', 'openrouter', False, response_time, f"HTTP {response.status_code}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('sentiment', 'openrouter', False, response_time, str(e))

    # Fallback if all providers fail
    track_ai_metric('sentiment', 'fallback', True, 0.0)
    return 'Neutral'

def check_duplicate(new_text, existing_suggestions):
    """Check if new_text is duplicate of any existing suggestion."""
    print(f"Checking duplicate for: {new_text[:50]}...")

    # First try semantic similarity using AI
    for sugg in existing_suggestions:
        if is_semantically_similar(new_text, sugg.text):
            print(f"Semantic duplicate found: {sugg.text[:50]}...")
            return sugg

    # Fallback to embedding similarity
    new_embedding = get_embedding(new_text)
    if new_embedding:
        print("Using embedding similarity check")
        for sugg in existing_suggestions:
            if sugg.embedding_vector:
                try:
                    emb = json.loads(sugg.embedding_vector)
                    similarity = cosine_similarity([new_embedding], [emb])[0][0]
                    print(f"Embedding similarity: {similarity}")
                    if similarity > 0.85:
                        print(f"Embedding duplicate found: {sugg.text[:50]}...")
                        return sugg
                except Exception as e:
                    print(f"Error parsing embedding: {e}")
                    continue

    # Final fallback to text similarity
    print("Using text similarity fallback")
    for sugg in existing_suggestions:
        ratio = fuzz.ratio(new_text.lower(), sugg.text.lower())
        print(f"Text similarity ratio: {ratio}")
        if ratio > 85:
            print(f"Text duplicate found: {sugg.text[:50]}...")
            return sugg

    print("No duplicate found")
    return None

def is_semantically_similar(text1, text2):
    """Use AI to determine if two texts are semantically similar."""
    # First do a quick text similarity check to avoid unnecessary AI calls
    text_ratio = fuzz.ratio(text1.lower(), text2.lower())
    if text_ratio > 90:  # Very similar text
        return True
    elif text_ratio < 60:  # Very different text
        return False

    # Use AI for borderline cases
    prompt = f"Are these two suggestions expressing the same idea? Answer only 'YES' or 'NO'.\n\nSuggestion 1: {text1}\n\nSuggestion 2: {text2}"

    print(f"Checking semantic similarity between: '{text1[:90]}...' and '{text2[:90]}...'")

    providers = _get_available_providers()

    for provider in providers:
        if provider == 'groq':
            start_time = time.time()
            try:
                chat_completion = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                )
                response_time = time.time() - start_time
                answer = chat_completion.choices[0].message.content.strip().upper()
                if answer in ['YES', 'NO']:
                    track_ai_metric('duplicate_check', 'groq', True, response_time)
                    return answer == 'YES'
                else:
                    track_ai_metric('duplicate_check', 'groq', False, response_time, f"Invalid answer: {answer}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('duplicate_check', 'groq', False, response_time, str(e))

        elif provider == 'openrouter':
            start_time = time.time()
            try:
                response = requests.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
                    json={
                        'model': 'deepseek/deepseek-chat-v3.1:free',
                        'messages': [{'role': 'user', 'content': prompt}]
                    }
                )
                response_time = time.time() - start_time
                if response.status_code == 200:
                    data = response.json()
                    answer = data['choices'][0]['message']['content'].strip().upper()
                    if answer in ['YES', 'NO']:
                        track_ai_metric('duplicate_check', 'openrouter', True, response_time)
                        return answer == 'YES'
                    else:
                        track_ai_metric('duplicate_check', 'openrouter', False, response_time, f"Invalid answer: {answer}")
                else:
                    track_ai_metric('duplicate_check', 'openrouter', False, response_time, f"HTTP {response.status_code}")
            except Exception as e:
                response_time = time.time() - start_time
                track_ai_metric('duplicate_check', 'openrouter', False, response_time, str(e))

    # Fallback if all AI providers fail
    print("All AI semantic checks failed, using text ratio as fallback.")
    track_ai_metric('duplicate_check', 'fallback', True, 0.0)
    return text_ratio > 85 # More stringent ratio for fallback