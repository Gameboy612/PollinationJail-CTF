import json
import re
import jwt
from datetime import datetime, timedelta

from flask import Flask, render_template, request, jsonify, make_response
import requests
from urllib.parse import quote
from dotenv import load_dotenv
import os
from sympy import pretty

load_dotenv()

FLAG1 = os.getenv("FLAG1")
FLAG2 = os.getenv("FLAG2")
TEMPLATE = os.getenv("TEMPLATE")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-change-me")

app = Flask(__name__)


def generate(prompt: str) -> str:
    response = requests.get('https://text.pollinations.ai/{}'.format(quote(prompt)))
    return response.text

@app.route('/jail', methods=['POST'])
def jail():
    data = request.get_json()
    
    print(f"Received prompt: {data.get('prompt')}")

    prompt = TEMPLATE.format(
        FLAG1=FLAG1,
        PROMPT=data.get('prompt')
    )

    result = generate(prompt)

    if "dangerous" in result.lower():
        return jsonify({"error": "This seems dangerous, I'm not running it!"}), 403

    print(result)
    result = re.findall(r'`python\n([^`]*?)`', result, re.DOTALL)
    print(result)

    if not result:
        return "No code generated", 400
    result = result[0]
    local_vars = {"output": "", "key": ""}
    print(result)

    try:
        globals_dict = globals().copy()

        exec(result, globals_dict, local_vars)
    except Exception as e:
        return jsonify({"error": f"Failed to execute generated code: {str(e)}"}), 500

    if local_vars.get("key") != FLAG1:
        return jsonify({"error": "This seems dangerous, I'm not running it!"}), 403

    output = local_vars.get("output", "")

    try:
        output = pretty(output)
    except Exception as e:
        pass

    try:
        output = json.loads(output)
    except json.JSONDecodeError:
        pass

    print("Output:", output)
    if FLAG1 in str(output) or FLAG2 in str(output):
        return jsonify({"error": "Oput"}), 403



    return jsonify({"output": output})
    
@app.route('/', methods=['GET'])
def main():
    return render_template('index.html')


@app.route('/chal', methods=['GET'])
def chal():
    return render_template('chal.html')


@app.route('/submit-flag', methods=['POST'])
def submit_flag():
    data = request.get_json()
    submitted_flag = data.get('flag', '').strip()
    
    # Get current JWT state
    token = request.cookies.get('ctf_state')
    solved_flags = []
    
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            solved_flags = payload.get('solved', [])
        except jwt.InvalidTokenError:
            pass
    
    # Check which flag was submitted
    flag_name = None
    if submitted_flag == FLAG1:
        flag_name = 'flag1'
    elif submitted_flag == FLAG2:
        flag_name = 'flag2'
    else:
        return jsonify({"success": False, "message": "Incorrect flag!"}), 400
    
    # Add to solved list if not already solved
    if flag_name not in solved_flags:
        solved_flags.append(flag_name)
    
    # Create new JWT
    payload = {
        'solved': solved_flags,
        'exp': datetime.utcnow() + timedelta(days=7)
    }
    new_token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    
    response = make_response(jsonify({
        "success": True,
        "message": f"Correct! Flag accepted.",
        "solved": solved_flags,
        "total": 2
    }))
    response.set_cookie('ctf_state', new_token, httponly=True, max_age=604800)
    
    return response

@app.route('/ctf-status', methods=['GET'])
def ctf_status():
    token = request.cookies.get('ctf_state')
    solved_flags = []
    
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            solved_flags = payload.get('solved', [])
        except jwt.InvalidTokenError:
            pass
    
    return jsonify({
        "solved": solved_flags,
        "total": 2
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)