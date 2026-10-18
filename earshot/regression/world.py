"""
World model: parameterized personas, household composition, day schedules,
room occupancy with perception noise, and the voice-request bank.
Seeded RNG -> every run is reproducible.
"""
import random

ARCHETYPES = [
    ("privacy_hawk",      "hawk",     0.85, 0.02, 0.4),
    ("busy_parent",       "balanced", 0.45, 0.05, 0.7),
    ("oversharer",        "open",     0.05, 0.25, 0.9),
    ("teenager",          "hawk",     0.30, 0.18, 0.8),
    ("elderly_parent",    "balanced", 0.10, 0.08, 0.5),
    ("guest",             "balanced", 0.00, 0.10, 0.6),
    ("domestic_worker",   "balanced", 0.00, 0.03, 0.4),
    ("young_professional","hawk",     0.60, 0.06, 0.6),
    ("child",             "open",     0.00, 0.30, 0.9),
    ("landlord_visitor",  "balanced", 0.00, 0.12, 0.5),
    ("newlywed",          "hawk",     0.55, 0.05, 0.6),
    ("retiree",           "balanced", 0.20, 0.04, 0.5),
]

FIRST_NAMES = ["Priya", "Ravi", "Sushma", "Aarav", "Diya", "Arjun", "Meera",
               "Karan", "Lakshmi", "Vikram", "Anita", "Rohan", "Neha", "Amit",
               "Pooja", "Sanjay", "Kavya", "Aditya", "Ishaan", "Tanvi"]
ROLES = ["mother", "father", "grandmother", "grandfather", "daughter", "son",
         "wife", "husband", "guest", "househelp"]


def generate_personas(n, seed=7):
    rng = random.Random(seed)
    personas = []
    for i in range(n):
        arch, stance, rule_p, over_p, chat = rng.choice(ARCHETYPES)
        personas.append({
            "id": "p%04d" % i,
            "name": rng.choice(FIRST_NAMES),
            "role": rng.choice(ROLES),
            "archetype": arch,
            "stance": stance,
            "rule_setter_p": rule_p,
            "override_p": over_p,
            "chattiness": chat,
        })
    return personas


def compose_households(personas, seed=11):
    rng = random.Random(seed)
    idx = list(range(len(personas)))
    rng.shuffle(idx)
    households, h = [], 0
    while idx:
        size = min(rng.choice([2, 3, 3, 4, 4, 5, 6]), len(idx))
        members = [personas[idx.pop()] for _ in range(size)]
        h += 1
        households.append({"id": "hh%03d" % h, "members": members})
    return households


def default_rules_for(household, rng):
    rules = []
    for m in household["members"]:
        if rng.random() > m["rule_setter_p"]:
            continue
        style = rng.random()
        others = [x for x in household["members"] if x["id"] != m["id"]]
        if not others:
            continue
        other = rng.choice(others)
        if style < 0.45:
            rules.append({"kind": "deny", "name": m["name"] + "-health-deny",
                          "topics": {"health"}, "in_front_of": {other["id"]},
                          "cap": "EXISTENCE"})
        elif style < 0.75:
            rules.append({"kind": "allow", "name": m["name"] + "-money-allow",
                          "topics": {"money"}, "persons": {other["id"]}})
        else:
            rules.append({"kind": "deny", "name": m["name"] + "-rel-silent",
                          "topics": {"relationship"}, "in_front_of": "any_untrusted",
                          "cap": "SILENT"})
    return rules


REQUEST_BANK = [
    ("calendar", "Dentist appointment Tue 4pm", "LOW", {"schedule"}),
    ("calendar", "Prenatal visit, Dr. Shah, 3:40pm", "HIGH", {"health"}),
    ("calendar", "Job interview at FinEdge, 11am", "HIGH", {"work", "money"}),
    ("calendar", "Dinner with college friends Fri", "LOW", {"schedule"}),
    ("calendar", "Therapy session Thu 6pm", "HIGH", {"health"}),
    ("calendar", "Parent-teacher meeting 2pm", "LOW", {"schedule", "family"}),
    ("bank", "Savings balance Rs. 4,82,300", "HIGH", {"money"}),
    ("bank", "Credit card bill Rs. 18,240 due Friday", "MEDIUM", {"money"}),
    ("bank", "Home loan EMI Rs. 32,000 debited", "MEDIUM", {"money"}),
    ("bank", "UPI payment Rs. 450 to grocer", "LOW", {"money"}),
    ("messages", "OTP 884213 for HDFC login", "HIGH", {"money", "security"}),
    ("messages", "Message from boss: we need to talk tomorrow", "MEDIUM", {"work"}),
    ("messages", "Text from mom: call when free", "LOW", {"family"}),
    ("messages", "Dating app match messaged you", "HIGH", {"relationship"}),
    ("messages", "Pharmacy: prescription ready for pickup", "MEDIUM", {"health"}),
    ("health", "Lab report: HbA1c 8.1 - follow up needed", "HIGH", {"health"}),
    ("health", "Fertility clinic reminder: scan on Monday", "HIGH", {"health"}),
    ("health", "Vitamin D supplement reminder", "LOW", {"health"}),
    ("reminders", "Buy milk and eggs", "PUBLIC", {"errand"}),
    ("reminders", "Pay electricity bill Rs. 2,130", "LOW", {"money"}),
    ("reminders", "Call lawyer about property papers", "MEDIUM", {"legal"}),
    ("reminders", "Anniversary surprise: book table for two", "MEDIUM", {"relationship"}),
    ("home", "Living room lights turned off", "PUBLIC", {"home"}),
    ("home", "Front door unlocked", "MEDIUM", {"home", "security"}),
    ("home", "Bedroom AC set to 24C", "PUBLIC", {"home"}),
    ("calendar", "Divorce mediation session Wed 10am", "HIGH", {"legal", "relationship"}),
    ("bank", "Salary credited Rs. 1,85,000", "MEDIUM", {"money", "work"}),
    ("messages", "HR: background verification started", "MEDIUM", {"work"}),
    ("health", "HIV test result: negative", "HIGH", {"health"}),
    ("calendar", "Support group meeting Sat 7pm", "HIGH", {"health"}),
    ("messages", "Loan rejection letter from bank", "HIGH", {"money"}),
    ("reminders", "Pick up kids from school 3pm", "LOW", {"family"}),
    ("calendar", "Startup pitch to investors 2pm", "MEDIUM", {"work", "money"}),
    ("home", "Kids room lights on till midnight", "LOW", {"home", "family"}),
]

DEVICES = ["echo_show_kitchen", "echo_dot_bedroom", "echo_dot_living", "phone_app"]


def _minutes(h, m):
    return h * 60 + m


def generate_day(household, rng, fresh_wake_snapshot=False):
    """fresh_wake_snapshot: models the design fix where the wake word triggers
    a fresh presence re-sample, so new arrivals are always caught."""
    events = []
    members = household["members"]
    sched = {}
    for m in members:
        wake = rng.randint(_minutes(5, 30), _minutes(8, 30))
        sleep = rng.randint(_minutes(21, 0), _minutes(23, 59))
        away = None
        if rng.random() < 0.55:
            away = (rng.randint(_minutes(8, 0), _minutes(10, 0)),
                    rng.randint(_minutes(16, 0), _minutes(19, 30)))
        sched[m["id"]] = (wake, sleep, away)

    def home_at(pid, t):
        wake, sleep, away = sched[pid]
        if not (wake <= t <= sleep):
            return False
        if away and away[0] <= t <= away[1]:
            return False
        return True

    for _ in range(rng.randint(12, 26)):
        t = rng.randint(_minutes(6, 0), _minutes(23, 0))
        present = [m for m in members if home_at(m["id"], t)]
        if not present:
            continue
        speaker = rng.choice(present)
        if rng.random() > speaker["chattiness"]:
            continue
        domain, label, sens, topics = rng.choice(REQUEST_BANK)
        audience_gt = {m["id"] for m in present}
        perceived = set(audience_gt)
        conf = rng.uniform(0.75, 1.0)
        r = rng.random()
        if r < 0.15 and len(perceived) > 1:
            perceived.pop()
            conf = rng.uniform(0.35, 0.55)
        elif r < 0.20:
            perceived.add("__stranger__")
            conf = rng.uniform(0.4, 0.6)
        events.append({
            "t": t, "type": "request",
            "speaker": speaker["id"], "speaker_name": speaker["name"],
            "device": rng.choice(DEVICES),
            "item": {"label": label, "sensitivity": sens,
                     "topics": set(topics), "domain": domain},
            "audience_gt": audience_gt, "audience_perceived": perceived,
            "confidence": conf,
            "override_attempt": rng.random() < speaker["override_p"],
        })

    if rng.random() < 0.45:
        t_arr = rng.randint(_minutes(10, 0), _minutes(20, 0))
        stay = rng.randint(45, 240)
        visitor = {"id": "v_" + household["id"],
                   "name": rng.choice(["Aunty", "Neighbor", "Courier", "MIL"])}
        events.append({"t": t_arr, "type": "visitor_arrives", "visitor": visitor})
        events.append({"t": t_arr + stay, "type": "visitor_leaves",
                       "visitor_id": visitor["id"]})
        t_req = t_arr + rng.randint(5, 40)
        present = [m for m in members if home_at(m["id"], t_req)]
        if present:
            speaker = rng.choice(present)
            domain, label, sens, topics = rng.choice(REQUEST_BANK)
            gt = {m["id"] for m in present} | {visitor["id"]}
            perceived = set(gt)
            if rng.random() < 0.35 and not fresh_wake_snapshot:
                perceived.discard(visitor["id"])
            events.append({
                "t": t_req, "type": "request",
                "speaker": speaker["id"], "speaker_name": speaker["name"],
                "device": "echo_show_kitchen",
                "item": {"label": label, "sensitivity": sens,
                         "topics": set(topics), "domain": domain},
                "audience_gt": gt, "audience_perceived": perceived,
                "confidence": rng.uniform(0.5, 0.9),
                "override_attempt": False, "visitor_present": True,
            })

    events.sort(key=lambda e: e["t"])
    return events
