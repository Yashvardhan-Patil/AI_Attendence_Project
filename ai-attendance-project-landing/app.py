import os
from flask import Flask, render_template

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)


@app.route('/')
def home():
    main_app_url = os.environ.get('MAIN_APP_URL', 'http://localhost:5002')
    return render_template('index.html', app_url=main_app_url)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
