from flask import Flask, request, jsonify
from datetime import date
import openai

openai.api_key = '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'

MODEL = "gpt-3.5-turbo"
app = Flask(__name__)

suspicion_counter = 0
suspicion_threshold = 2

def judge_humanness(user_message):
    global suspicion_counter
    prompt = f"Does the following message seem like it's from a human or an AI?'{user_message}'"
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
    for message in messages:
        role = {
            'outgoing': 'assistant',
            'incoming': 'user'
        }
        msgs_for_openai.append({
            'role': role[message['direction']],
            'content': message['text']
        })

    return [SYSTEM_MSG] + msgs_for_openai

@app.route('/robocaller', methods=['POST'])
def onboard_start():
    global suspicion_counter
    try:
        messages = request.get_json()['messages']
        last_user_message = messages[-1]['text']
    except Exception:
        pass

    # Judge the response's humanness
    judge_humanness(last_user_message)

    c_messages = handle_message(messages)
    
    out = openai.ChatCompletion.create(
        model=MODEL,
        messages=c_messages,
    )
    out_message = out['choices'][0]['message']['content']

    # If suspicion_counter exceeds a threshold, raise a warning.
    if suspicion_counter >= suspicion_threshold:
        return {"warning": "Possible AI detected!"}
    
    if "verified" in out_message.lower() or "uploaded" in out_message.lower():
        current_step += 1

    return {'messages': messages + [out_message]}


if __name__ == "__main__":
    app.run(debug=True)
