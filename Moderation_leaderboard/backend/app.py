from flask import Flask, request, jsonify , make_response
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
CORS(app)

MONGO_URI = "mongodb://mediafirewall01:ysvrSoY9e9sugv0@10.1.0.31:28018/?ssl=false&authSource=admin"
client = MongoClient(MONGO_URI)
batch_coll = client["moderation"]["batch"]

RETRY_WEIGHT = 3  

def name_from_email_expr(field: str):
    return {
        "$let": {
            "vars": {
                "email": f"${field}",
                "dot": {"$indexOfBytes": [f"${field}", ".media"]},
                "at": {"$indexOfBytes": [f"${field}", "@"]},
            },
            "in": {
                "$cond": [
                    {"$gte": ["$$dot", 0]},
                    {"$substrBytes": ["$$email", 0, "$$dot"]},
                    {"$cond": [
                        {"$gte": ["$$at", 0]},
                        {"$substrBytes": ["$$email", 0, "$$at"]},
                        "$$email"
                    ]}
                ]
            }
        }
    }

def fetch_leaderboard_rows(start_utc: datetime, end_utc: datetime, retry_weight: float = RETRY_WEIGHT):
    pipeline = [
        {"$match": {
            "assignedModerator": {"$type": "string"},
            "events.0.mfwEvent.eventStartTime": {"$gte": start_utc, "$lt": end_utc}
        }},
        {"$addFields": {
            "_ct": {"$toDouble": "$completeTime"},
            "_tmr": {"$toDouble": "$timer"},
            "_rc": {"$ifNull": ["$retryCount", 1]},
        }},
        {"$match": {"_ct": {"$type": "number"}}},
        {"$addFields": {
            "_realRetry": {"$cond": [{"$gt": ["$_rc", 1]}, {"$subtract": ["$_rc", 1]}, 0]}
        }},
        {"$group": {
            "_id": "$assignedModerator",
            "batches": {"$sum": 1},
            "total": {"$sum": "$_ct"},
            "realRetries": {"$sum": "$_realRetry"},
        }},
        {"$set": {
            "avg": {"$cond": [{"$gt": ["$batches", 0]}, {"$divide": ["$total", "$batches"]}, None]}
        }},
        {"$project": {
            "_id": 0,
            "moderator": "$_id",
            "name": name_from_email_expr("_id"),
            "batches": 1,
            "avg": {"$round": ["$avg", 2]},
            "realRetries": 1,
        }},
    ]

    rows = list(batch_coll.aggregate(pipeline, allowDiskUse=True))
    if not rows:
        return []

    total_batches = max(r["batches"] for r in rows)
    total_avg = min(r["avg"] for r in rows if r["avg"] is not None)
    total_retry = max(r["realRetries"] for r in rows)

    inverted_shares = []
    for r in rows:
        if total_retry > 0 and r["realRetries"] is not None:
            share = r["realRetries"] / total_retry
            inverted_share = 1 - share
        else:
            inverted_share = 1.0
        inverted_shares.append(inverted_share)

    sum_inverted = sum(inverted_shares)

    for i, r in enumerate(rows):
        r["batchesScore"] = round((r["batches"] / total_batches) * 100, 2) if total_batches else 0
        r["avgScore"] = round((total_avg / r["avg"]) * 100, 2) if r["avg"] else 0
        r["retryScore"] = round((1 - (r["realRetries"] / total_retry)) * 100, 2)
        # r["retryScore"] = round((inverted_shares[i] / sum_inverted) * 100, 2) if sum_inverted > 0 else 0

        r["points"] = round(
            r["batchesScore"] * 0.4 +
            r["avgScore"] * 0.4 +
            r["retryScore"] * 0.2, 2
        )

    rows = sorted(rows, key=lambda x: x["points"], reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    return rows

@app.get("/data")
def get_data():
    start = request.args.get("start")
    end = request.args.get("end")
    if not start or not end:
        return jsonify({"error": "start and end query params required"}), 400
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except Exception as e:
        return jsonify({"error": f"bad datetime: {e}"}), 400

    rows = fetch_leaderboard_rows(start_dt, end_dt)
    print(rows)
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
