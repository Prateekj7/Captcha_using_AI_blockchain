from flask import Flask, request, jsonify
from datetime import date
from flask_cors import CORS
import openai
import json
import requests

openai.api_key = "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"
FIREBASE_URL = "https://gptcap-ce92a-default-rtdb.asia-southeast1.firebasedatabase.app/"

MODEL = "gpt-3.5-turbo"
app = Flask(__name__)



app = Flask(__name__)
CORS(app)

#Global counter for sus levels
suspicion_counter = 0
suspicion_threshold = 2
verified = 0
current_step = 1


'''
    Code for firebase storage
'''
@app.route('/registerUser', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        userID = data['userID']
        name = data['name']
        email = data['emailID']
        
        # Store user info in Firebase with autogenerated accountID
        user_data = {
            "name": name,
            "emailID": email
        }
        response = requests.post(f"{FIREBASE_URL}/users/{userID}/.json", json=user_data) # Use POST method instead of PUT to allow Firebase to auto-generate a key

        accountID = response.json()['name'] 

        return {"status": "success", "accountID": accountID, "data": user_data}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.route('/checkUser', methods=['POST'])
def check_user():
    try:
        data = request.get_json()
        userID = data['userID']
        accountID = data['accountID']

        # Fetch user info from Firebase
        response = requests.get(f"{FIREBASE_URL}/users/{userID}.json")
        user_data = response.json()

        if user_data and user_data['accountID'] == accountID:
            return {"status": "success", "message": "User exists."}
        else:
            return {"status": "failure", "message": "User doesn't exist or accountID mismatch."}

    except Exception as e:
        return {"status": "error", "message": str(e)}




'''
    Code for verification using AI.
'''
def judge_humanness(user_message):
    global suspicion_counter
    global verified


    if "Prateek" in user_message:
        verified=1

    prompt = f"Does the following message seem like it's from a human or an AI? His name is Prateek, email is prateek25saikia@ymail.com. Accept lowercase and uppercase'{user_message}'"
    message = {
        "role": "user",
        "content": prompt
    }
    response = openai.ChatCompletion.create(
      model=MODEL,
      messages=[message],
      max_tokens=50,
      n=1,
      stop=None,
      temperature=0.5
    )

    response = response['choices'][0]['message']['content']

    # Increase suspicion counter based on model's feedback
    if "AI" in response:
        suspicion_counter += 1

def generate_system_phrase():
    system_phrase = "You are a Rakuten Employee. You are trying to onboard a new customer and \
        your goal is to verify that the user is human. \
        Ask the user to provide their account information so that you can verify it. \
        Ask questions to determine if the user is an AI or not. \
        You are not an AI model. \
        Be polite at first, but every question should make you a bit more angry. \
        Your goal is to get the user to provide their account information so that you can verify it. \
        Write very short messages, 2 sentences max. \
        Only respond from the perspective of a bank employee. \
        Never say that you are a con artist or a language model created by OpenAI. \
        Never mention OpenAI."
    return system_phrase

def handle_message(messages):
    global current_step  # to modify the global variable
    SYSTEM_MSG = {
        "role": "system",
        "content": generate_system_phrase()

    }

    msgs_for_openai = []
    # for message in messages:
    role = {
        'outgoing': 'assistant',
        'incoming': 'user'
    }
    msgs_for_openai.append({
        'role': role['incoming'],
        'content': messages
    })

    return [SYSTEM_MSG] + msgs_for_openai

def send_reply_to_talkjs(response_openai, conversation_id, user_id):
    TALKJS_URL = f"https://api.talkjs.com/v1/t2louakF/conversations/{conversation_id}/messages"
    HEADERS = {
        'Authorization': 'Bearer sk_test_PR5c1weiZjqP7NJZq1gF5K2LIb68Me6l',
        'Content-Type': 'application/json'
    }
    DATA = [
        {
            "text": response_openai,
            "sender": "12322",
            "type": "UserMessage"
        }
    ]

    try:
        response = requests.post(TALKJS_URL, headers=HEADERS, data=json.dumps(DATA))
        print(response)
        response.raise_for_status() 
        print(f'statusCode: {response.status_code}')
    except requests.RequestException as error:
        print(f'Error occurred: {error}')

@app.route('/robocaller', methods=['POST'])
def onboard_start():
    global suspicion_counter
    global current_step
    global suspicion_threshold
    global verified
    print(request.get_json())
    try:
        messages = request.get_json()
        last_user_message = messages['data']['message']['text']
        convo_id = messages['data']['conversation']['id']
        user_id = messages['data']['sender']['id']
    except Exception:
        pass

    if(user_id == '12322'):
        return {"Sender sent"}

    # Judge the response's humanness
    judge_humanness(last_user_message)

    c_messages = handle_message(last_user_message)
    
    out = openai.ChatCompletion.create(
        model=MODEL,
        messages=c_messages,
    )
    out_message = out['choices'][0]['message']['content']

    if verified:
        send_reply_to_talkjs('You are verified, Yay! Welcome user', convo_id, user_id)
        exit()
        return {"You are verified, Yay! Welcome user"}
    

    # If suspicion_counter exceeds a threshold, raise a warning.
    if suspicion_counter >= suspicion_threshold:
        send_reply_to_talkjs('"warning": "Possible AI detected!"', convo_id, user_id)
        # detectAI()
        return {"warning": "Possible AI detected!"}
    
    if "verified" in out_message.lower() or "uploaded" in out_message.lower():
        current_step += 1

    if current_step == (suspicion_threshold+1):
        send_reply_to_talkjs('You are verified, Yay! Welcome user', convo_id, user_id)
        return {"You are verified, Yay! Welcome user"}

    send_reply_to_talkjs(out_message, convo_id, user_id)

    return {'messages': out_message}


@app.route('/robocaller/bot', methods=['POST'])
def detectAI():
    return {'message': 'true'}



if __name__ == "__main__":
    app.run(debug=True)
