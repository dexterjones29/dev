# Learning Python

# store the number 42 in a variable called answer
answer = 42

# create a second variable called double_answer that stores twice the value of answer

double_answer = answer * 2


if double_answer > 50:
    print(double_answer)
else:
    print("less than 50")

# wrap if/else logic inside a function called check_value that takes double_answer as a parameter

def _check_value(double_answer):
    if double_answer > 50:
        return "greater"
    elif double_answer == 50:
        return "equal"
    else:
        return "less"

result = _check_value(double_answer)

# write an if statement that prints "High value" when result is "greater"
# write an elif line so it checks whether result is "equal"
# write an else line that prints "Low value" when result is neither "greater" nor "equal"

if result == "greater":
    print("High value")
elif result == "equal":
    print("Equal")
else:
    print("Low value")

# Loop structure

# for <item> in <collection>:
#    <do something with item>

# print "High" for values over 50 and "Low" for values 50 or under inside the loop next to the actual number

values = [30, 50, 70]

for v in values:
    if v > 50:
        print(f"{v} High")
    else:
        print(f"{v} Low")

# create a new list called labels that stores "High" or "Low" for each value with the .append() method

values = [30, 50, 70]

labels = []

for v in values:
    if v > 50:
        labels.append("High")
    else:
        labels.append("Low")

print(labels)

# store BOTH the number and the label with the .append() method

values = [30, 50, 70]

labels = []

for v in values:
    if v > 50:
        labels.append(f'{v} High')
    else:
        labels.append(f'{v} Low')

print(labels)


# build a list of dictionaries
# if v is greater than 50, write the .append() line to add a dictionary like {"value": v, "label": "High"}

values = [30, 50, 70]

labels = []

for v in values:
    if v > 50:
        labels.append({"value": v, "label": "High"})
    else:
        labels.append({"value": v, "label": "Low"})

print(labels)

# add a new key called "double" to each dictionary that stores the value of v multiplied by 2

values = [30, 50, 70]

labels = []

for v in values:
    if v > 50:
        labels.append({"value": v, "double": v * 2, "label": "High"})
    else:
        labels.append({"value": v, "double": v * 2, "label": "Low"})

print(labels)

# Add a "status" key with a nested dictionary as its values, like {"code": 1, "text": "OK"}

values = [30, 50, 70]

labels = []

for v in values:
    if v > 50:
        labels.append({"value": v, "double": v * 2, "label": "High", "status": {"code": 1, "text": "OK"}})
    else:
        labels.append({"value": v, "double": v * 2, "label": "Low",  "status": {"code": 0, "text": "WARN"}})

print(labels)

# move the dictionary‑building logic into a function called make_record(v)

def _make_record(v):
    if v > 50:
        label = "High"
        status = {"code": 1, "text": "OK"}
    else:
        label = "Low"
        status = {"code": 0, "text": "WARN"}
    record = {
        "value": v,
        "double": v * 2,
        "label": label,
        "status": status
    }
    return record

values = [30, 50, 70]
threshold = 50

labels = []

for v in values:
    labels.append(_make_record(v))

print(labels)

# Add a second parameter called threshold

def _make_record(v, threshold):
    if v > threshold:
        label = "High"
        status = {"code": 1, "text": "OK"}
    else:
        label = "Low"
        status = {"code": 0, "text": "WARN"}
    record = {
        "value": v,
        "double": v * 2,
        "label": label,
        "status": status
    }
    return record

values =  [30, 50, 70]
threshold = 50

labels = []

for v in values:
    labels.append(_make_record(v, threshold))

print(labels)

# Add parameters for high and low status

def _make_record(v, threshold, high_label, low_label, status_high, status_low):
    if v > threshold:
        label = high_label
        status = {"code": 1, "text": status_high}
    else:
        label = low_label
        status = {"code": 0, "text": status_low}
    record = {
        "value": v,
        "double": v * 2,
        "label": label,
        "status": status
    }
    return record

values = [30, 50, 70]
threshold = 50
high_label = "High"
low_label = "Low"
status_high = "OK"
status_low = "WARN"

labels = []

for v in values:
    labels.append(_make_record(v, threshold, high_label, low_label, status_high, status_low))

print(labels)

# Write a function that returns a dictionary mapping each user_id to the number of events they generated.
events = [
    {"user_id": 1, "timestamp": "2024-01-01 10:00:00", "event_type": "login"},
    {"user_id": 1, "timestamp": "2024-01-01 10:05:00", "event_type": "view"},
    {"user_id": 2, "timestamp": "2024-01-01 11:00:00", "event_type": "login"},
    {"user_id": 1, "timestamp": "2024-01-01 10:10:00", "event_type": "logout"},
]

def _count_events(events):
    counts = {}

    for event in events:
        user_id = event["user_id"]

        if user_id not in counts:
            counts[user_id] = 0

        counts[user_id] += 1

    return counts

result = _count_events(events)
print(result)

# You are given a list of event dictionaries. Each event has: a user_id, an event_type, and a timestamp.
# Write a function that returns a dictionary mapping each user_id to the number of distinct event types they generated.

events = [
    {"user_id": 1, "event_type": "login",  "timestamp": "2024-01-01 10:00:00"},
    {"user_id": 1, "event_type": "view",   "timestamp": "2024-01-01 10:05:00"},
    {"user_id": 2, "event_type": "login",  "timestamp": "2024-01-01 11:00:00"},
    {"user_id": 1, "event_type": "logout", "timestamp": "2024-01-01 10:10:00"},
    {"user_id": 2, "event_type": "view",   "timestamp": "2024-01-01 11:05:00"},
]

def event_types(events):
    user_events = {}

    for event in events:
        user_id = event["user_id"]
        event_type = event["event_type"]

        if user_id not in user_events:
            user_events[user_id] = set()