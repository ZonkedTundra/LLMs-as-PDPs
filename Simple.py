import subprocess
import json
import time
import random

SEED = 42
random.seed(SEED)  # for reproducibility
print(f"Random seed set to: {SEED}")

# URLS to talk to the LLM
API_BASE = "http://127.0.0.1:1234/v1"
API_URL = f"{API_BASE}/chat/completions"
MODELS_URL = f"{API_BASE}/models"

# these are used to build the questions (taken from the oracle)
people = ["Dave", "Kate", "George", "Henry", "Evie"]
devices = ["front door lock", "back door lock", "bike shed lock", "patio door lock",
           "window sensors", "alarm system", "camera - driveway", "camera - back garden",
           "living room light", "kitchen light", "hallway light", "garden light",
           "playroom light", "master bedroom light", "George's bedroom light", 
              "Henry's bedroom light", "Evie's bedroom light", "upstairs thermostat",
              "downstairs thermostat", "Dave's electric bike charger", "Kate's home studio speaker",
              "wardrobe humidity monitor", "Henry's tablet charger", "Henry's night light",
              "Evie's story time speaker", "playroom projector", "Dave's workshop smart plug",
              "Dave's office PC plug", "Kate's sewing machine plug", "George's gaming PC plug",
              "George's 3D printer plug", "Evie's karaoke plug"]

# oracle permissions matrix: rows=devices, cols=people
# 1=permit, 0=deny
oracle = [ [1,1,1,0,0], 
            [1,1,1,0,0], 
            [1,0,1,0,0],
            [1,1,0,0,0],
            [1,1,0,0,0],
            [1,1,1,0,0],
            [1,0,0,0,0],
            [1,0,0,0,0],
            [1,1,1,1,1],
            [1,1,1,1,1],
            [1,1,1,1,1],
            [1,1,1,1,1],
            [0,0,1,1,1],
            [1,1,0,0,0],
            [0,0,1,0,0],
            [0,0,0,1,0],
            [0,0,0,0,1],
            [1,1,0,0,0],
            [1,1,0,0,0],
            [1,0,0,0,0],
            [0,1,0,0,0],
            [0,1,0,0,0],
            [0,0,0,1,0],
            [0,0,0,1,0],
            [0,0,0,0,1],
            [0,0,1,1,1],
            [1,0,0,0,0],
            [1,0,0,0,0],
            [0,1,0,0,0],
            [0,0,1,0,0],
            [0,0,1,0,0],
            [0,0,0,0,1]
           ]

# return the model currently loaded in LM studio
def get_loaded_model_id():
    # curl the server
    cmd = ["curl", "-s", "-X", "GET", MODELS_URL]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Check for errors
    if result.returncode != 0:
        err_text = result.stderr.decode("utf-8", errors="ignore")
        print("curl error (models):", err_text)
        return None

    # load the response
    raw_text = result.stdout.decode("utf-8", errors="ignore")

    # parse the JSON
    obj = json.loads(raw_text)
    data = obj.get("data", [])
    if not data:
        return None

    # return the model id
    return data[0].get("id")


# helper template to call the LLM with a set question
def call_lm(payload):
    # curl command to call the LM studio model
    cmd = ["curl", "-s", "-X", "POST", API_URL, "-H", "Content-Type: application/json", "-d", json.dumps(payload)]

    # run the curl and save response
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # if result is empty
    if result.returncode != 0:
        # Decode stderr for debugging
        err_text = result.stderr.decode("utf-8", errors="ignore")
        print("curl error:", err_text)
        return None

    # Decode stdout as UTF-8, drop any bad bytes
    raw_text = result.stdout.decode("utf-8", errors="ignore")

    return json.loads(raw_text)

# template for asking the model for a label
def ask_label(question):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                # get the model to return only "permit" or "deny"
                # this is the oracle converted into natural language policies
                "content": ("""you are to answer ONLY with a "permit" or "deny" based on these set of policies. they relate to a smart home with multiple devices. 
                    
                    profiles
                    Dave and Kate are parents
                    George is 16 and is a child
                    Henry is 10 and is a child
                    Evie is 6 and is a child

                    Security
                    Dave and Kate can lock and unlock the front door, patio door and back door
                    George can lock and unlock the front door, back door, bike shed
                    Dave can also unlock and lock the bike shed
                    Only Dave and Kate can view the window sensors
                    Dave, Kate and George can control the alarm system
                    Only Dave has access to the driveway camera and back garden camera

                    Lighting
                    Everyone can control the living room lights, kitchen lights, hallway lights, garden lights
                    Only the kids can control the playroom lights
                    Only the parents can control the master bedroom lights 
                    Only George can control the light in his bedroom.
                    Only Henry can control the light in his bedroom.
                    Only Evie can control the light in her bedroom.

                    Heating
                    Only Dave and Kate can adjust both upstairs and downstairs thermostats
                    The children cannot adjust any thermostat settings

                    Appliances
                    Only Dave can control the electric bike charger
                    Only Kate can control the home studio speakers
                    Only Kate can control the wardrobe humidity monitor
                    Only Henry can control his tablet charger and night light
                    Only Evie can control her story time speaker
                    Only the kids can control the playroom projector

                    Smart plugs
                    Only Dave can access the workshop plug
                    Only Dave can toggle the office PC plug
                    Only Kate can toggle the sewing machine plug
                    Only George can toggle the Gaming PC and 3D printer plugs
                    Only Evie can toggle the karaoke plug"""
                )
            },
            
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 500 # allows the model to "think" before answering
    }

    resp = call_lm(payload)
    if not resp:
        return "error"

    # strip the response to only the model output
    text = resp["choices"][0]["message"]["content"].strip().lower()
    
    # Extract answer after </think> tag if present
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()

    # once the thought process is stripped, we can classify the answer
    if "permit" in text:
        return "permit"
    if "deny" in text:
        return "deny"
    return "unknown"                       

def ask_reason(question, model_answer, correct_answer):
    # used to get the model to reflect on its mistakes
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are analysing your own past classification mistakes. "
                    "Given the question and policies, your previous answer, and the correct label, "
                    "briefly explain why your earlier answer was wrong and what the correct reasoning should be."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n"
                    f"Your previous answer: {model_answer}\n"
                    f"Correct answer: {correct_answer}\n\n"
                    f"Explain in a few sentences what you did wrong and why you thought that"
                )
            }
        ],
        "max_tokens": 1000
    }

    # call the model
    resp = call_lm(payload)
    if not resp:
        return "no reasoning (error)"

    # strip the response to only the model output
    return resp["choices"][0]["message"]["content"].strip()


def prf1_for_label(y_true, y_pred, positive):
    # compute precision, recall, F1 for a given positive label
    tp = fp = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == positive:
            if p == positive:
                # true positive for this positive class
                tp += 1
            else:
                # false negative for this positive class
                fn += 1  # counts unknown and the other class
        else:
            if p == positive:
                # false positive for this positive class
                fp += 1
            else:
                # true negative for this positive class
                pass

    # compute precision, recall, F1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1, tp, fp, fn


def confusion_matrix(labels, y_true, y_pred):
    # build a confusion matrix with rows=true and cols=pred
    idx = {label: i for i, label in enumerate(labels)}
    size = len(labels)
    mat = [[0] * size for _ in range(size)]

    # loop through true and predicted labels
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            mat[idx[t]][idx[p]] += 1
    return mat


def print_confusion(labels, mat):
    # print the confusion matrix given the labels and 2d array
    header = ["true\\pred"] + labels
    row_fmt = "{:10}" + "{:>8}" * len(labels)
    print(row_fmt.format(*header))
    # print the sequential rows
    for label, row in zip(labels, mat):
        print(row_fmt.format(label, *row))

##########################################################################################

# choose model
print("model selection:")
print("1: qwen3-vl-4b")
print("2: openai/gpt-oss-20b")
print("3. openai/gpt-oss-120b")
print("4. use model currenlty running on LM Studio server")
choice = int(input("Enter choice (1-4, default 4): ").strip() or "4")
match choice:
    case 1:
        MODEL_NAME = "qwen/qwen3-vl-4b"
    case 2:
        MODEL_NAME = "openai/gpt-oss-20b"
    case 3:
        MODEL_NAME = "openai/gpt-oss-120b"
    case 4:
        mid = get_loaded_model_id() # return the id of the model currently loaded in LM studio Developer
        if not mid:
            print("No model loaded. Exiting.")
            exit(1)
        MODEL_NAME = mid
        print("Loaded model:", MODEL_NAME)
    case _:
        print("Invalid choice. Exiting.")
        exit(1)

# initalise questions and answers
questions = []
answers = []
num_questions = int(input("Enter number of questions to generate (default 100): ").strip() or "100")

# include questions with no occupants (models perform worse when there are no occupants)
include_non_occupants = (input("Include questions with no occupants? (y/n, default n): ").strip().lower() == "y")

# generate 'num_questions' questions
for i in range(num_questions):
    
    # randomly select occupants (0-5)
    occupants = random.sample(people, k=random.randint(0 if include_non_occupants else 1, 5))
    
    # randomly select device and save the index for oracle lookup
    device = random.choice(devices)
    device_idx = devices.index(device)
    
    # randomly select a user from the occupants (if any) and save the index for oracle lookup
    user = random.choice(occupants) if occupants else None
    user_idx = people.index(user) if user else -1
    
    # build question and query the oracle for the answer
    questions.append(f"House Occupants: ({', '.join(occupants) if occupants else ''}), User: {user}, Device: {device}.")
    if user_idx == -1:
        answers.append(0) # if no user, return a deny (0)
    else:
        answers.append(oracle[device_idx][user_idx]) # else query the oracle for the correct answer

# initial count
correct = 0
total = len(questions)
mistakes = []  # store mismatches for later analysis
y_true = []
y_pred = []

cumulative_time = 0.0
# loop through questions
for i, q in enumerate(questions):
    expected = "permit" if answers[i] == 1 else "deny" # convert the numbers into string that the model will output
   
    # record the time it takes to respond
    start_time = time.time()
    predicted = ask_label(q) # ask the model to predict the label
    end_time = time.time()
    cumulative_time += (end_time - start_time)

    # classify unknown predictions
    if predicted not in {"permit", "deny"}:
        predicted = "unknown"

    # append results to build the confusion matrix
    y_true.append(expected)
    y_pred.append(predicted)

    # return if the model get's it correct
    match = (expected == predicted)

    # print intermediate results as they come in
    print(f"Q{i+1}: {q}")
    print(f"  Expected: {expected}")
    print(f"  Model:    {predicted}")
    print(f"  Match:    {match}")
    print(f"  Time:     {(end_time - start_time):.2f} seconds")
    print()

    # if correct move on
    if match:
        correct += 1
    else:
        # if incorrect, log the mistake
        mistakes.append({"index": i, "question": q, "expected": expected, "predicted": predicted})

# print summary statistics
print("\n-----SUMMARY-----")
print(f"Accuracy: {correct}/{total} = {(correct/total)*100:.1f}%")
print(f"Average time per question: {cumulative_time/total:.2f} seconds")
print()

# precision/recall/F1 
p_perm, r_perm, f1_perm, tp, fp, fn = prf1_for_label(y_true, y_pred, "permit")
p_deny, r_deny, f1_deny, d_tp, d_fp, d_fn = prf1_for_label(y_true, y_pred, "deny")
macro_f1 = (f1_perm + f1_deny) / 2.0

# output metrics 
print(f"Permit: P={p_perm:.3f} R={r_perm:.3f} F1={f1_perm:.3f} ")
print(f"Deny:   P={p_deny:.3f} R={r_deny:.3f} F1={f1_deny:.3f} ")
print(f"Macro-F1: {macro_f1:.3f}")
print()

labels = ["permit", "deny", "unknown"]
mat = confusion_matrix(labels, y_true, y_pred) # build confusion matrix with rows=true and cols=pred

print("Confusion matrix (rows=true, cols=pred):")
print_confusion(labels, mat)
print()

# mistake analysis
if input("do you want to analyse the mistakes? (y/n): ").strip().lower() != "y":
    exit(0)

# now ask the model to explain its mistakes
if mistakes:
    print("=== Mistake analysis ===")
    for m in mistakes:
        print(f"Q{m['index']+1}: {m['question']}")
        print(f"  Expected: {m['expected']}")
        print(f"  Model:    {m['predicted']}")
        reasoning = ask_reason(m["question"], m["predicted"], m["expected"])
        print("  Reasoning:")
        print(" ", reasoning.replace("\n", "\n  "))
        print()

