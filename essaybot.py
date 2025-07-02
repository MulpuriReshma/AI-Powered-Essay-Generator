from flask import Flask, render_template, request, redirect, url_for, session 
import requests
import os
import webbrowser
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Set your Together AI API key here
API_KEY = "32ab2d221266a7ced2f57caebac6d0638cfe9bef0283944dcc6d3c62d72d5bf1"

# Supported languages
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi"
}

# Translation of UI elements
TRANSLATIONS = {
    "en": {
        "title": "AI Essay Generator",
        "enter_topic": "Enter your essay topic",
        "topic_placeholder": "e.g., The impact of artificial intelligence on society",
        "word_count": "Approximate word count",
        "paragraph_count": "Number of paragraphs",
        "language": "Essay language",
        "light": "Light",
        "dark": "Dark",
        "generate": "Generate Essay",
        "new_chat": "New Essay",
        "loading": "Generating your essay... This may take a few moments.",
        "generated_on": "Generated on",
        "previous_essays": "Previous Essays",
        "no_previous_essays": "No previous essays available.",
        "view_essay": "View"
    },
    "es": {
        "title": "Generador de Ensayos IA",
        "enter_topic": "Ingresa el tema de tu ensayo",
        "topic_placeholder": "ej., El impacto de la inteligencia artificial en la sociedad",
        "word_count": "Número aproximado de palabras",
        "paragraph_count": "Número de párrafos",
        "language": "Idioma del ensayo",
        "light": "Claro",
        "dark": "Oscuro",
        "generate": "Generar Ensayo",
        "new_chat": "Nuevo Ensayo",
        "loading": "Generando tu ensayo... Esto puede tomar unos momentos.",
        "generated_on": "Generado el",
        "previous_essays": "Ensayos Anteriores",
        "no_previous_essays": "No hay ensayos anteriores disponibles.",
        "view_essay": "Ver"
    },
    # Add other language translations here if needed
}

def generate_text(prompt, word_count=1000, paragraph_count=5, language="en", model="meta-llama/Llama-3.3-70B-Instruct-Turbo"):
    url = "https://api.together.xyz/v1/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Language-specific instructions
    lang_instructions = {
        "en": "Write in English",
        "es": "Escribe en español",
        "fr": "Écrivez en français",
        "de": "Schreiben Sie auf Deutsch",
        "it": "Scrivi in italiano",
        "pt": "Escreva em português",
        "ru": "Пишите на русском",
        "zh": "用中文写",
        "ja": "日本語で書いてください",
        "ko": "한국어로 작성하세요",
        "ar": "اكتب باللغة العربية",
        "hi": "हिंदी में लिखें"
    }

    # Add detailed instructions to the prompt
    lang_instruction = lang_instructions.get(language, lang_instructions["en"])
    
    formatted_prompt = (
        f"{lang_instruction}. Write a detailed and well-formatted essay on: {prompt}. "
        f"The essay should be approximately {word_count} words and contain exactly {paragraph_count} paragraphs. "
        f"Include an introduction, {paragraph_count-2} body paragraphs, and a conclusion. "
        "Ensure the content is structured logically. "
        "Provide examples and explanations to support your points."
    )

    # Calculate max_tokens based on word count (approximation)
    max_tokens = min(word_count * 1.5, 4000)  # Safeguard against very large requests

    data = {
        "model": model,  
        "prompt": formatted_prompt,
        "max_tokens": int(max_tokens),
        "temperature": 0.7,
        "top_p": 0.9,
        "n": 1,
        "stop": None
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        response_json = response.json()
        
        # Extract text correctly
        if "choices" in response_json and len(response_json["choices"]) > 0:
            essay_text = response_json["choices"][0].get("text", "").strip()
            return essay_text if essay_text else "Error: Empty response from API"
        else:
            return "Error: No choices found in response"
    except requests.exceptions.RequestException as e:
        return f"Error: Failed to connect to the API. {e}"
    except ValueError as e:
        return f"Error: Invalid JSON response. {e}"

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get the interface language (default to English)
    ui_lang = request.args.get('ui_lang', 'en')
    if ui_lang not in TRANSLATIONS:
        ui_lang = 'en'
    
    # Get translations for the selected language
    t = TRANSLATIONS.get(ui_lang, TRANSLATIONS["en"])
    
    # Get theme preference
    theme = request.args.get('theme', session.get('theme', 'light'))
    session['theme'] = theme
    
    # Initialize session for essay history if not exists
    if 'essay_history' not in session:
        session['essay_history'] = []
    
    essay_text = ""
    prompt = ""
    generation_time = ""
    word_count = 1000
    paragraph_count = 5
    essay_lang = "en"
    
    if request.method == 'POST':
        prompt = request.form.get('prompt', '')
        word_count = int(request.form.get('word_count', 1000))
        paragraph_count = int(request.form.get('paragraph_count', 5))
        essay_lang = request.form.get('essay_lang', 'en')
        
        if prompt:
            essay_text = generate_text(prompt, word_count, paragraph_count, essay_lang)
            generation_time = datetime.now().strftime('%B %d, %Y at %H:%M')
            
            # Save the essay to history
            essay_id = len(session['essay_history'])
            essay_data = {
                'id': essay_id,
                'prompt': prompt,
                'essay': essay_text,
                'generation_time': generation_time,
                'word_count': word_count,
                'paragraph_count': paragraph_count,
                'essay_lang': essay_lang
            }
            
            # Add to session history (most recent first)
            session['essay_history'] = [essay_data] + session['essay_history']
            session.modified = True
            
            # Save to file (optional)
            with open("generated_essay.txt", "w", encoding="utf-8") as file:
                file.write(essay_text)
    
    # Get view_id from query params
    view_id = request.args.get('view_id')
    
    # If view_id is provided, show that specific essay
    if view_id is not None:
        try:
            view_id = int(view_id)
            for essay in session['essay_history']:
                if essay['id'] == view_id:
                    essay_text = essay['essay']
                    prompt = essay['prompt']
                    generation_time = essay['generation_time']
                    word_count = essay['word_count']
                    paragraph_count = essay['paragraph_count']
                    essay_lang = essay['essay_lang']
                    break
        except (ValueError, IndexError):
            pass  # Invalid ID, just show the form
    
    return render_template('index.html', 
                          essay=essay_text, 
                          prompt=prompt,
                          generation_time=generation_time,
                          word_count=word_count,
                          paragraph_count=paragraph_count,
                          essay_lang=essay_lang,
                          ui_lang=ui_lang,
                          languages=LANGUAGES,
                          theme=theme,
                          t=t,
                          essay_history=session.get('essay_history', []))

@app.route('/new', methods=['GET'])
def new_chat():
    # Get current theme and language
    theme = session.get('theme', 'light')
    ui_lang = request.args.get('ui_lang', 'en')
    
    # Redirect to fresh form while preserving theme and language
    return redirect(url_for('index', theme=theme, ui_lang=ui_lang))

@app.route('/view/<int:essay_id>', methods=['GET'])
def view_essay(essay_id):
    # Get current theme and language
    theme = session.get('theme', 'light')
    ui_lang = request.args.get('ui_lang', 'en')
    
    # Redirect to index with the essay_id to view
    return redirect(url_for('index', view_id=essay_id, theme=theme, ui_lang=ui_lang))

def open_browser():
    # Wait a short time for the server to start
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

# Create the templates directory if it doesn't exist
os.makedirs('templates', exist_ok=True)

# Create the index.html template
with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write('''<!DOCTYPE html>
<html lang="{{ ui_lang }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ t.title }}</title>
    <style>
        :root {
            --bg-color: {{ 'var(--dark-bg)' if theme == 'dark' else 'var(--light-bg)' }};
            --text-color: {{ 'var(--dark-text)' if theme == 'dark' else 'var(--light-text)' }};
            --card-bg: {{ 'var(--dark-card)' if theme == 'dark' else 'var(--light-card)' }};
            --button-color: {{ 'var(--dark-button)' if theme == 'dark' else 'var(--light-button)' }};
            --button-hover: {{ 'var(--dark-button-hover)' if theme == 'dark' else 'var(--light-button-hover)' }};
            --border-color: {{ 'var(--dark-border)' if theme == 'dark' else 'var(--light-border)' }};
            
            --light-bg: #f5f5f5;
            --light-text: #333;
            --light-card: white;
            --light-button: #3498db;
            --light-button-hover: #2980b9;
            --light-border: #ddd;
            
            --dark-bg: #1a1a1a;
            --dark-text: #f0f0f0;
            --dark-card: #2d2d2d;
            --dark-button: #2980b9;
            --dark-button-hover: #3498db;
            --dark-border: #444;
        }
        
        body {
            font-family: 'Georgia', serif;
            line-height: 1.6;
            color: var(--text-color);
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background-color: var(--bg-color);
            transition: background-color 0.3s, color 0.3s;
            position: relative;
        }
        h1, h2, h3 {
            color: var(--text-color);
        }
        form {
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], select {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            box-sizing: border-box;
            margin-bottom: 15px;
            background-color: var(--card-bg);
            color: var(--text-color);
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-row {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-col {
            flex: 1;
            min-width: 200px;
        }
        button {
            background-color: var(--button-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: var(--button-hover);
        }
        .essay-container {
            background-color: var(--card-bg);
            padding: 30px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        .meta {
            color: {{ '#aaa' if theme == 'dark' else '#7f8c8d' }};
            font-style: italic;
            margin-bottom: 30px;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            font-style: italic;
            color: {{ '#aaa' if theme == 'dark' else '#666' }};
        }
        p {
            margin-bottom: 20px;
            text-align: justify;
        }
        .action-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .new-chat-button {
            background-color: {{ '#555' if theme == 'dark' else '#e67e22' }};
        }
        .new-chat-button:hover {
            background-color: {{ '#666' if theme == 'dark' else '#d35400' }};
        }
        .top-buttons {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .app-header {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .new-essay-top {
            background-color: {{ '#555' if theme == 'dark' else '#e67e22' }};
        }
        .new-essay-top:hover {
            background-color: {{ '#666' if theme == 'dark' else '#d35400' }};
        }
        .theme-toggle {
            background-color: transparent;
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: center;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            font-size: 20px;
            padding: 0;
        }
        .controls-right {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .history-container {
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            margin-bottom: 30px;
        }
        .history-item {
            padding: 15px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .history-item:last-child {
            border-bottom: none;
        }
        .history-meta {
            color: {{ '#aaa' if theme == 'dark' else '#7f8c8d' }};
            font-size: 0.9em;
        }
        .view-button {
            background-color: {{ '#444' if theme == 'dark' else '#2ecc71' }};
            padding: 5px 15px;
        }
        .view-button:hover {
            background-color: {{ '#555' if theme == 'dark' else '#27ae60' }};
        }
        .main-container {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        .essay-section {
            flex: 2;
            min-width: 300px;
        }
        .history-section {
            flex: 1;
            min-width: 250px;
        }
        
        @media (max-width: 768px) {
            .top-buttons {
                flex-direction: column;
                gap: 15px;
                align-items: flex-start;
            }
            .controls-right {
                width: 100%;
                justify-content: space-between;
            }
            .main-container {
                flex-direction: column;
            }
        }
        
        @media print {
            form, .action-buttons, .top-buttons, .history-section {
                display: none;
            }
            body {
                background-color: white;
                color: black;
            }
            .essay-container {
                box-shadow: none;
                background-color: white;
                color: black;
            }
        }
    </style>
</head>
<body>
    <div class="top-buttons">
        <div class="app-header">
            <a href="{{ url_for('new_chat', ui_lang=ui_lang) }}">
                <button class="new-essay-top">{{ t.new_chat }}</button>
            </a>
            <h1>{{ t.title }}</h1>
        </div>
        
        <div class="controls-right">
            <select id="ui-language" onchange="changeLanguage(this.value)">
                {% for code, name in languages.items() %}
                <option value="{{ code }}" {% if code == ui_lang %}selected{% endif %}>{{ name }}</option>
                {% endfor %}
            </select>
            
            <button class="theme-toggle" onclick="toggleTheme()">
                {{ '🌙' if theme == 'light' else '☀️' }}
            </button>
        </div>
    </div>
    
    <div class="main-container">
        <div class="essay-section">
            <form id="essay-form" method="POST" onsubmit="document.getElementById('loading').style.display='block';">
                <h2>{{ t.enter_topic }}</h2>
                <div class="form-group">
                    <input type="text" name="prompt" placeholder="{{ t.topic_placeholder }}" value="{{ prompt }}" required>
                </div>
                
                <div class="form-row">
                    <div class="form-col">
                        <label for="word_count">{{ t.word_count }}</label>
                        <select name="word_count" id="word_count">
                            <option value="500" {% if word_count == 500 %}selected{% endif %}>500</option>
                            <option value="750" {% if word_count == 750 %}selected{% endif %}>750</option>
                            <option value="1000" {% if word_count == 1000 %}selected{% endif %}>1000</option>
                            <option value="1500" {% if word_count == 1500 %}selected{% endif %}>1500</option>
                            <option value="2000" {% if word_count == 2000 %}selected{% endif %}>2000</option>
                        </select>
                    </div>
                    
                    <div class="form-col">
                        <label for="paragraph_count">{{ t.paragraph_count }}</label>
                        <select name="paragraph_count" id="paragraph_count">
                            <option value="3" {% if paragraph_count == 3 %}selected{% endif %}>3</option>
                            <option value="4" {% if paragraph_count == 4 %}selected{% endif %}>4</option>
                            <option value="5" {% if paragraph_count == 5 %}selected{% endif %}>5</option>
                            <option value="6" {% if paragraph_count == 6 %}selected{% endif %}>6</option>
                            <option value="7" {% if paragraph_count == 7 %}selected{% endif %}>7</option>
                        </select>
                    </div>
                    
                    <div class="form-col">
                        <label for="essay_lang">{{ t.language }}</label>
                        <select name="essay_lang" id="essay_lang">
                            {% for code, name in languages.items() %}
                            <option value="{{ code }}" {% if code == essay_lang %}selected{% endif %}>{{ name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
                
                <button type="submit">{{ t.generate }}</button>
            </form>
            
            <div id="loading" class="loading">
                <p>{{ t.loading }}</p>
            </div>
            
            {% if essay %}
            <div class="essay-container">
                <h2>{{ prompt }}</h2>
                {% if generation_time %}
                <div class="meta">{{ t.generated_on }} {{ generation_time }}</div>
                {% endif %}
                
                {% for paragraph in essay.split('\n\n') %}
                    {% if paragraph.strip() %}
                        <p>{{ paragraph | replace('\n', '<br>') | safe }}</p>
                    {% endif %}
                {% endfor %}
            </div>
            {% endif %}
        </div>
        
        <div class="history-section">
            <div class="history-container">
                <h3>{{ t.previous_essays }}</h3>
                
                {% if essay_history and essay_history|length > 0 %}
                    {% for item in essay_history %}
                        <div class="history-item">
                            <div>
                                <div><strong>{{ item.prompt }}</strong></div>
                                <div class="history-meta">{{ item.generation_time }}</div>
                            </div>
                            <a href="{{ url_for('view_essay', essay_id=item.id, ui_lang=ui_lang, theme=theme) }}">
                                <button class="view-button">{{ t.view_essay }}</button>
                            </a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>{{ t.no_previous_essays }}</p>
                {% endif %}
            </div>
        </div>
    </div>
    
    <script>
        // Reset loading indicator when page loads
        window.onload = function() {
            document.getElementById('loading').style.display = 'none';
        }
        
        // Toggle theme
        function toggleTheme() {
            const newTheme = '{{ theme }}' === 'light' ? 'dark' : 'light';
            window.location.href = window.location.pathname + '?theme=' + newTheme + '&ui_lang={{ ui_lang }}';
        }
        
        // Change interface language
        function changeLanguage(lang) {
            window.location.href = window.location.pathname + '?ui_lang=' + lang + '&theme={{ theme }}';
        }
    </script>
</body>
</html>''')

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Opening web browser automatically...")
    
    # Start browser in a separate thread
    threading.Thread(target=open_browser).start()
    
    # Start the Flask server
    app.run(debug=True)
