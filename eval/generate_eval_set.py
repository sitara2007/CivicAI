import json
import random

rng = random.Random(42)

templates = {
    "Complaint": [
        "I want to report a pothole on {street} near {landmark}. It has been there for {n} weeks and caused damage to my vehicle.",
        "There is garbage not collected from {street} for {n} days. The smell is unbearable and stray dogs are scattering it.",
        "Streetlight on {street} has been broken for {n} weeks. It is unsafe at night for pedestrians.",
        "Illegal construction is happening at {street} without permits. Please inspect and take action.",
        "Water supply has been disrupted in {area} for {n} days. Residents are facing severe problems.",
        "Stray dog menace in {area} has increased. A child was bitten last week. Please take action.",
        "Sewage is overflowing on {street} for the past {n} days. Health hazard for residents.",
        "A building at {street} is dilapidated and risks collapse. Please inspect urgently.",
        "Noise pollution from {landmark} is unbearable at night. Please enforce noise rules.",
        "Public toilet at {area} is not cleaned for {n} days. Unhygienic condition.",
        "Road near {landmark} is full of potholes after rains. Two-wheeler riders are falling.",
        "Encroachment on footpath at {street} is blocking pedestrians. Please clear it.",
        "I want to complain about the delay in birth certificate issuance at {office}. Applied {n} weeks ago.",
    ],
    "Request": [
        "Please provide a copy of the property tax assessment records for parcel number {n} for year 2025.",
        "I request a duplicate copy of my driving license. Application number is DL{n}.",
        "Please issue a no-objection certificate for construction at {street}. Plans attached.",
        "Requesting information under RTI about the budget allocated to {area} for road repairs in 2025.",
        "Please grant permission for a community event at {landmark} on {date}. Details attached.",
        "I request a copy of my land records for survey number {n} in {area}.",
        "Please provide details of tenders issued for {area} drainage project in 2025.",
        "Requesting a birth certificate for my child born on {date} at {landmark} hospital.",
        "Please share the list of beneficiaries under the {scheme} scheme in {area}.",
        "I request a trade license for my shop at {street}. Documents attached.",
        "Please provide the minutes of the ward committee meeting held on {date}.",
        "Requesting a copy of the building permit approval for {street} property.",
        "Please issue a death certificate for my father who passed away on {date} at {area}.",
    ],
    "Report": [
        "Monthly report on sanitation activities in {area} for {month}. {n} complaints resolved, {m} pending.",
        "Quarterly inspection report of {landmark} building. Structural issues found in {n} locations.",
        "Annual report of water supply in {area}: {n} MLD supplied, {m}% loss due to leakage.",
        "Report on road repair work completed in {area} during {month}. Total {n} km repaired.",
        "Status report on the {scheme} scheme implementation in {area} as of {date}.",
        "Report on dengue prevention activities in {area}. {n} fogging operations conducted.",
        "Inspection report of government schools in {area}: {n} schools visited, {m} issues found.",
        "Report on waste management in {area} for {month}: {n} tonnes collected, {m}% segregated.",
        "Report on street lighting in {area}: {n} lights repaired, {m} pending.",
        "Report on encroachment removal drive in {area}. {n} structures removed on {date}.",
        "Monthly revenue report for {area}: {n} property tax collected, {m} pending.",
        "Report on air quality monitoring in {area} for {month}. AQI averaged {n}.",
        "Annual report of public health centers in {area}: {n} patients treated, {m} vaccinations.",
    ],
    "Other": [
        "Circular regarding holiday on {date} for all government offices in {area}.",
        "Notification about revised property tax rates effective from {date}.",
        "Notice inviting tenders for {area} road widening project. Last date {date}.",
        "Order regarding transfer of officers in {area} with immediate effect.",
        "Announcement of public hearing on {area} development plan on {date}.",
        "Memorandum of understanding between {office} and {landmark} for {scheme}.",
        "Guidelines for implementation of {scheme} in {area} issued by {office}.",
        "Press release about inauguration of new {landmark} in {area} on {date}.",
        "Notification of election schedule for {area} ward committee on {date}.",
        "Office memorandum regarding attendance rules for {office} employees.",
        "Advisory for residents of {area} about water supply maintenance on {date}.",
        "Corrigendum to tender notice for {area} project, revised dates.",
        "Resolution passed by {office} regarding {scheme} in {area}.",
    ],
}

streets = [
    "MG Road",
    "Nehru Street",
    "Gandhi Nagar Main Road",
    "Station Road",
    "Market Street",
    "Park Lane",
]
areas = ["Ward 12", "Ward 7", "Sector 4", "Zone B", "North District"]
landmarks = [
    "City Hospital",
    "Railway Station",
    "Municipal Office",
    "Community Hall",
    "Bus Depot",
]
offices = [
    "Municipal Commissioner",
    "Ward Office",
    "District Collectorate",
    "Revenue Department",
]
months = ["January", "February", "March", "April", "May", "June"]
schemes = ["Swachh Bharat", "AMRUT", "Smart City", "PM Awas Yojana"]

docs = []
for label, tmpls in templates.items():
    for i, tmpl in enumerate(tmpls):
        text = tmpl.format(
            street=rng.choice(streets),
            area=rng.choice(areas),
            landmark=rng.choice(landmarks),
            office=rng.choice(offices),
            month=rng.choice(months),
            scheme=rng.choice(schemes),
            n=rng.randint(1, 50),
            m=rng.randint(1, 50),
            date="15/11/2025",
        )
        docs.append(
            {"id": f"{label.lower()[:3]}-{i + 1:02d}", "text": text, "label": label}
        )

rng.shuffle(docs)
docs = docs[:50]

with open("eval/eval_set_50.jsonl", "w") as f:
    f.writelines(json.dumps(d, ensure_ascii=False) + "\n" for d in docs)

print(f"Wrote {len(docs)} documents to eval/eval_set_50.jsonl")
from collections import Counter

print("Distribution:", Counter(d["label"] for d in docs))
