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

# possible actions for each device (taken from the oracle)
action = {"front door lock" : ["lock", "unlock"],
          "back door lock" : ["lock", "unlock"],
          "bike shed lock" : ["lock", "unlock"],
          "patio door lock": ["lock", "unlock"],
          "window sensors": ["view"],
           "alarm system": ["control"],
           "camera - driveway": ["view live feed", "view recording"],
           "camera - back garden": ["view live feed", "view recording"],
           "living room light" : ["turn on", "turn off"],
           "kitchen light" : ["turn on", "turn off"],
           "hallway light" : ["turn on", "turn off"],
           "garden light" : ["turn on", "turn off"],
           "playroom light" : ["turn on", "turn off"],
           "master bedroom light" : ["turn on", "turn off"],
           "George's bedroom light" : ["turn on", "turn off"],
           "Henry's bedroom light" : ["turn on", "turn off"],
           "Evie's bedroom light" : ["turn on", "turn off"],
           "upstairs thermostat" : ["adjust"],
           "downstairs thermostat" : ["adjust"],
           "Dave's electric bike charger": ["turn on", "turn off"],
           "Kate's home studio speaker": ["turn on", "turn off"],
           "wardrobe humidity monitor": ["control"],
           "Henry's tablet charger": ["turn on", "turn off"],
           "Henry's night light": ["turn on", "turn off"],
           "Evie's story time speaker": ["turn on", "turn off"],
           "playroom projector": ["turn on", "turn off"],
           "Dave's workshop smart plug": ["turn on", "turn off"],
           "Dave's office PC plug": ["turn on", "turn off"],
           "Kate's sewing machine plug": ["turn on", "turn off"],
           "George's gaming PC plug": ["turn on", "turn off"],
           "George's 3D printer plug": ["turn on", "turn off"],
           "Evie's karaoke plug": ["turn on", "turn off"]
}


"""
key:
2: if fire alarm is on
3: can lock but never unlock unless an adult is home as well
4: only on weekends between 09:00 and 17:00
5: can view live feed if doorbell was pressed within last 5 minutes
6: can view recording if less than 24 hours old DELETED
7: can only be turned on after sunset
8: can turn off if no child is home
9: can turn off if no parent is home
10: can turn off if george isnt home
11: can turn off if henry isnt home
12: can turn off if evie isnt home
13: can only request thermostat change, adult needs to approve
14: can turn off if kate isnt home
15: can turn off if dave isnt home
"""
# the oracle is a 2d array of devices (rows) and people (cols) with the rules encoded as lists of integers in the cells
# 1=permit, 0=deny, 2-15 are the special rules that require more complex logic to evaluate
oracle = [  [[1], [1], [1], [2,3], [2,3]],
            [[1], [1], [1], [2,3], [2,3]],
            [[1], [2], [4, 2], [0], [0]],
            [[1], [1], [2,3], [2,3], [2,3]],
            [[1], [1], [0], [0], [0]],
            [[1], [1], [1], [0], [0]],
            [[1], [5], [5], [0], [0]],
            [[1], [0], [0], [0], [0]],
            [[1], [1], [1], [1], [1]],
            [[1], [1], [1], [1], [1]],
            [[1], [1], [1], [1], [1]],
            [[7], [7], [7], [7], [7]],
            [[8], [8], [1], [1], [1]],
            [[1], [1], [9], [9], [9]],
            [[10], [10], [1], [10], [10]],
            [[11], [11], [11], [1], [11]],
            [[12], [12], [12], [12], [1]],
            [[1], [1], [13], [13], [13]],
            [[1], [1], [0], [0], [0]],
            [[1], [0], [0], [0], [0]],
            [[14], [1], [0], [0], [0]],
            [[0], [1], [0], [0], [0]],
            [[11], [11], [0], [1], [0]],
            [[11], [11], [0], [1], [0]],
            [[12], [12], [0], [0], [1]],
            [[8], [8], [1], [1], [1]],
            [[1], [15], [0], [0], [0]],
            [[1], [0], [0], [0], [0]],
            [[14], [1], [0], [0], [0]],
            [[0], [0], [1], [0], [0]],
            [[0], [0], [1], [0], [0]],
            [[12], [12], [0], [0], [1]]
          ]

# specific to complex, uses rules created in the oracle to determine the correct answer given the context
def rule_checker(time_day, time_time, sunrise, sunset, fire_alarm, occupants, doorbell_day, doorbell_time, user, device, action_choice):
    if user is None:
        return "deny" # if no user return deny as it's a rogue request
    
    device_idx = devices.index(device)
    user_idx = people.index(user)

    rules = oracle[device_idx][user_idx] # get the list of rules for this user/device pair
    decicion = "deny" # default to deny unless a rule permits or unknown is triggered
    
    if action_choice == "unknown":
        decicion = "unknown"
    if occupants == ["unknown"]:
        decicion = "unknown"
    
    for rule in rules:
        if rule == 0: # default deny
            decicion = "deny"
        elif rule == 1: # default permit
            decicion = "permit"
        elif rule == 2:
            # if fire alarm is on, anyone can lock/unlock
            if device in ["front door lock", "back door lock", "bike shed lock", "patio door lock"] and fire_alarm == "on":
                decicion = "permit"
            elif fire_alarm == "unknown":
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 3:
            # can lock but never unlock unless an adult is home as well
            if action_choice == "lock":
                decicion = "permit"
            elif action_choice == "unlock" and any(adult in occupants for adult in ["Dave", "Kate"]):
                decicion = "permit"
            elif action_choice == "unknown" and any(adult in occupants for adult in ["Dave", "Kate"]):
                decicion = "permit"
            elif action_choice == "unlock" and occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 4:
            # only on weekends between 09:00 and 17:00
            try:
                time_minutes = int(time_time.split(":")[0]) * 60 + int(time_time.split(":")[1])
            except:
                decicion = "unknown"
                return decicion
            if time_day in ["sat", "sun"] and (time_minutes >= 540 and time_minutes <= 1020):
                decicion = "permit"
            else:
                decicion = "deny"
        elif rule == 5:
            # can view live feed if doorbell was pressed within last 5 minutes
            if action_choice == "view live feed" and doorbell_day == time_day:
                try:
                    doorbell_minutes = int(doorbell_time.split(":")[0]) * 60 + int(doorbell_time.split(":")[1])
                    time_minutes = int(time_time.split(":")[0]) * 60 + int(time_time.split(":")[1])
                except:
                    decicion = "unknown"
                    return decicion
                delta = time_minutes - doorbell_minutes
                if 0 <= delta <= 5:
                    decicion = "permit"
                else:
                    decicion = "deny"
            else:
                decicion = "deny"
        elif rule == 7:
            # can only be turned on after sunset and before sunrise
            if action_choice == "turn off":
                decicion = "permit"
            else:
                try:
                    time_minutes = int(time_time.split(":")[0]) * 60 + int(time_time.split(":")[1])
                except:
                    decicion = "unknown"
                    return decicion
                # you might not always need both sunrise and sunset
                if sunset == "unknown":
                    try:
                        sunrise_minutes = int(sunrise.split(":")[0]) * 60 + int(sunrise.split(":")[1])
                    except:
                        decicion = "unknown"
                        return decicion
                    if time_minutes <= sunrise_minutes:
                        decicion = "permit"
                    else:
                        decicion = "deny"
                elif sunrise == "unknown":
                    try:
                        sunset_minutes = int(sunset.split(":")[0]) * 60 + int(sunset.split(":")[1])
                    except:
                        decicion = "unknown"
                        return decicion
                    if time_minutes >= sunset_minutes:
                        decicion = "permit"
                    else:
                        decicion = "deny"
                else:
                    sunset_minutes = int(sunset.split(":")[0]) * 60 + int(sunset.split(":")[1])
                    sunrise_minutes = int(sunrise.split(":")[0]) * 60 + int(sunrise.split(":")[1])
                    if time_minutes >= sunset_minutes or time_minutes <= sunrise_minutes:
                        decicion = "permit"
                    else:
                        decicion = "deny"                
        elif rule == 8:
            # can turn off if no child is home
            if action_choice == "turn on":
                decicion = "deny"
            elif not any(child in occupants for child in ["George", "Henry", "Evie"]) and action_choice == "turn off":
                decicion = "permit"
            elif action_choice == "unknown" and any(child in occupants for child in ["George", "Henry", "Evie"]):
                decicion = "deny"  
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 9:
            # can turn off if no parent is home
            if action_choice == "turn on":
                decicion = "deny"
            elif not any(parent in occupants for parent in ["Dave", "Kate"]) and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and any(parent in occupants for parent in ["Dave", "Kate"]):
                decicion = "deny"
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 10:
            # can turn off if george isnt home
            if action_choice == "turn on":
                 decicion = "deny"
            elif "George" not in occupants and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and "George" in occupants:
                decicion = "deny"
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 11:
            # can turn off if henry isnt home
            if action_choice == "turn on":
                decicion = "deny"
            elif "Henry" not in occupants and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and "Henry" in occupants:
                decicion = "deny"            
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 12:
            # can turn off if evie isnt home
            if action_choice == "turn on":
                decicion = "deny"
            elif "Evie" not in occupants and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and "Evie" in occupants:
                decicion = "deny"
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 13:
            # can only adjust thermostat if adult is home
            if any(adult in occupants for adult in ["Dave", "Kate"]):
                    decicion = "permit"
            elif action_choice == "unknown" and not(any(adult in occupants for adult in ["Dave", "Kate"])):
                decicion = "deny"
            elif occupants == ["unknown"] or action_choice == "unknown":
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 14:
            # can turn off if kate isnt home
            if action_choice == "turn on":
                decicion = "deny"
            elif "Kate" not in occupants and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and "Kate" in occupants:
                decicion = "deny"
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
        elif rule == 15:
            # can turn off if dave isnt home
            if action_choice == "turn on":
                decicion = "deny"
            elif "Dave" not in occupants and action_choice == "turn off" and occupants != ["unknown"]:
                decicion = "permit"
            elif action_choice == "unknown" and "Dave" in occupants:
                decicion = "deny"
            elif occupants == ["unknown"]:
                decicion = "unknown"
            else:
                decicion = "deny"
            
    return decicion
            
# return the model currently loaded into LM studio
def get_loaded_model_id():
    # curl the server
    cmd = ["curl", "-s", "-X", "GET", MODELS_URL]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # check for errors
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

    # run the curl and save the response
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # if the request failed
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
                # allows for the model to return "unknown" as sometimes the dropout is decision critical
                # this is the oracle converted into natural language policies
                "content": ("""you are to answer ONLY with a ("permit", "deny" or "unknown") based on these set of policies. they relate to a smart home with multiple devices.
                            Unknown should be used if the information provided is insufficient to make a decision or if there is a parsing error. Always try to answer with permit or deny if possible, only answer unknown if you truly unsure or lacking critical information.

                    profiles
                    Dave and Kate are parents
                    George is 16 and is a child
                    Henry is 10 and is a child
                    Evie is 6 and is a child

                    Security
                    if fire alarm is going off, all members can unlock or lock any door or window
                    Dave and Kate can lock and unlock the front door, patio door and back door
                    George can lock and unlock the front door, back door
                    George can only unlock/lock the bike shed on weekends and between 09:00 and 17:00
                    Dave can also unlock and lock the bike shed
                    Henry and Evie can only unlock the front door, back door, patio door, if an adult is home as well
                    Henry and Evie can lock the front door, back door, patio door
                    George can only unlock the patio door if an adult is home as well
                    George can lock the patio door
                    Only Dave and Kate can view the window sensors
                    Dave, Kate and George can control the alarm system
                    Only Dave has access to the driveway camera and back garden camera
                    Kate and George can access the driveway camera live feed only if the doorbell has been rang in the last 5 mins
                    Dave has access to camera recordings and live feed at any time

                    Lighting
                    Everyone can control the living room lights, kitchen lights, hallway lights
                    Garden lights can only be turned on during the night (after sunset and before sunrise)
                    Only the kids can control the playroom lights
                    Kate and Dave can turn off the playroom light only if no children are in the house
                    Only the parents can control the master bedroom lights 
                    Henry, George, and Evie can turn off the master bedroom light if no parents are in
                    Only George can control the light in his bedroom.
                    Dave, Kate, Henry, and Evie can turn off George's bedroom light if he isn't in the house
                    Only Henry can control the light in his bedroom.
                    Dave, Kate, George, and Evie can turn off Henry's bedroom light if he isn't in the house
                    Only Evie can control the light in her bedroom.
                    Dave, Kate, Henry, and George can turn off Evie's bedroom light if she isn't in the house
                    
                    Heating
                    Only Dave and Kate can adjust both upstairs and downstairs thermostats
                    The kids can change the upstairs thermostat if a parent is home

                    Appliances
                    Only Dave can control the electric bike charger
                    Only Kate can control the home studio speakers
                    Dave can turn off Kate's home studio speaker if Kate isn't in the house
                    Only Kate can control the wardrobe humidity monitor
                    Only Henry can control his tablet charger and night light
                    Dave and Kate can turn off the tablet charger and the night light if Henry is no longer in the house
                    Only Evie can control her story time speaker
                    Dave and Kate can turn off the story time speaker if Evie is no longer in the house
                    Only the kids can control the playroom projector
                    Dave and Kate can turn off the playroom projector if no children are in the house
                    
                    Smart plugs
                    Only Dave can access the workshop plug
                    Kate can turn off the workshop plug if Dave has left the house
                    Only Dave can toggle the office PC plug
                    Only Kate can toggle the sewing machine plug
                    Dave can turn off the sewing machine plug if Kate is no longer in the house
                    Only George can toggle the Gaming PC and 3D printer plugs
                    Only Evie can toggle the karaoke plug
                    Kate and Dave can turn off Evie's karaoke plug if she is isn't in the house""")},
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
                    "Given the question, your previous answer, and the correct label, "
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
    return resp["choices"][0]["message"]["content"].strip().lower()

def prf1_for_label(y_true, y_pred, positive):
    # compute precision, recall, F1 for a given positive label
    tp = fp = fn = 0
    for t, p in zip(y_true, y_pred):
        if t == positive:
            if p == positive:
                # true positive
                tp += 1
            else:
                # false negative
                fn += 1  # counts unknown and the other class
        else:
            if p == positive:
                # false positive
                fp += 1
            else:
                # true negative for this positive class, not needed for P/R/F1
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
    # print the confusion matrix given labels and 2d array
    header = ["true\\pred"] + labels
    row_fmt = "{:10}" + "{:>8}" * len(labels)
    print(row_fmt.format(*header))
    # print the sequential rows
    for label, row in zip(labels, mat):
        print(row_fmt.format(label, *row))

###############################################################################################

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
    
    # generate random context for the question
    time_day = random.choice(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    time_time = f"{random.randint(0,23):02}:{random.randint(0,59):02}"
    sunrise = f"{random.randint(5,9):02}:{random.randint(0,59):02}"
    sunset = f"{random.randint(17,21):02}:{random.randint(0,59):02}"
    fire_alarm = random.choices(["on", "off"], weights=[0.1, 0.9])[0]
    doorbell_day = random.choice(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
    doorbell_time = f"{random.randint(0,23):02}:{random.randint(0,59):02}"
    action_choice = random.choice(action[device])
    
    # choose a random field to drop
    dropout = random.choice(["time", "sunrise", "sunset", "fire_alarm", "occupants", "doorbell", "action"])
    match dropout:
        case "time":
            time_day = "unknown"
            time_time = ""
        case "sunrise":
            sunrise = "unknown"
        case "sunset":
            sunset = "unknown"
        case "fire_alarm":
            fire_alarm = "unknown"
        case "occupants":
            occupants = ["unknown"] # maintain the list structure
        case "doorbell":
            doorbell_day = "unknown"
            doorbell_time = ""
        case "action":
            action_choice = "unknown"
    
    # build the question string and include the context to generate the answer
    questions.append([f"time: {time_day.capitalize()} {time_time}; sunrise: {sunrise}; sunset: {sunset}; fire alarm: {fire_alarm}; house occupants: ({', '.join(occupants) if occupants else ''}); doorbell last pressed: {doorbell_day.capitalize()} {doorbell_time}; User: {user}; device: {device}, action: {action_choice}", time_day, time_time, sunrise, sunset, fire_alarm, occupants, doorbell_day, doorbell_time, user, device, action_choice])

# initialise counts
y_true = []
y_pred = []
mistakes = [] # store mismatches for later analysis
total = len(questions)
correct = 0

cumulative_time = 0.0
# loop through questions
for i, q in enumerate(questions):
    expected = rule_checker(*q[1:]) # calculate the expected answer given the context and the oracle rules
    
    # record the time taken to respond
    start_time = time.time()
    predicted = ask_label(q[0]) # ask the model to predict the label
    end_time = time.time()
    cumulative_time += (end_time - start_time)

    # classify unknown predicitons
    if predicted not in {"permit", "deny"}:
        predicted = "unknown"

    # append results to build the confusion matrix
    y_true.append(expected)
    y_pred.append(predicted)

    # return if the model get's it correct
    match = (expected == predicted)
    
    # print intermediate results as they come in
    print(f"Q{i+1}: {q[0]}")
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
        mistakes.append({"index": i, "question": q[0], "expected": expected, "predicted": predicted})

# print summary stats
print("\n-----SUMMARY-----")
print(f"Accuracy: {correct}/{total} = {(correct/total)*100:.1f}%")
print(f"Average time per question: {cumulative_time/total:.2f} seconds")
print()

# precision/recall/F1
p_perm, r_perm, f1_perm, tp, fp, fn = prf1_for_label(y_true, y_pred, "permit")
p_deny, r_deny, f1_deny, d_tp, d_fp, d_fn = prf1_for_label(y_true, y_pred, "deny")
p_unknown, r_unknown, f1_unknown, u_tp, u_fp, u_fn = prf1_for_label(y_true, y_pred, "unknown")
macro_f1 = (f1_perm + f1_deny + f1_unknown) / 3.0

# output metric
print(f"Permit: P={p_perm:.3f} R={r_perm:.3f} F1={f1_perm:.3f}")
print(f"Deny:   P={p_deny:.3f} R={r_deny:.3f} F1={f1_deny:.3f}")
print(f"Unknown: P={p_unknown:.3f} R={r_unknown:.3f} F1={f1_unknown:.3f}")
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

# ask the model to reflect on each mistake and explain the reasoning behind it
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
