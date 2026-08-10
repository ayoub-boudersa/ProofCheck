import json

with open("report.json") as f:
    data = json.load(f)

failed_tests = [t for t in data["results"]["tests"] if t["status"] == "failed"]

for test in failed_tests:
    print(test["name"])
    print(test["trace"])
    print("—"*90)