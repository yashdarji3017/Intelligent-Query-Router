import concurrent.futures
import json
import time
import urllib.error
import urllib.request

PORT = 8001
URL = f"http://127.0.0.1:{PORT}/chat"

TEST_QUERIES = [
    {"user_id": "user_1", "query": "Hello, how are you today?"},
    {"user_id": "user_2", "query": "Our production API is down and throwing 500 errors!"},
    {"user_id": "user_3", "query": "Where can I download my billing invoice for last month?"},
    {"user_id": "user_4", "query": "I need to reset my account login password."},
    {"user_id": "user_5", "query": "Please help architect a multi-step database migration."},
    {"user_id": "user_6", "query": "It is not working."},
]


def send_request(item):
    data = json.dumps(item).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            elapsed = (time.perf_counter() - start_time) * 1000.0
            body = json.loads(resp.read().decode("utf-8"))
            return {
                "user": item["user_id"],
                "status": resp.status,
                "elapsed_ms": round(elapsed, 2),
                "data": body,
            }
    except urllib.error.HTTPError as e:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        err_body = e.read().decode("utf-8")
        return {
            "user": item["user_id"],
            "status": e.code,
            "elapsed_ms": round(elapsed, 2),
            "error": err_body,
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start_time) * 1000.0
        return {
            "user": item["user_id"],
            "status": "error",
            "elapsed_ms": round(elapsed, 2),
            "error": str(e),
        }


def main():
    print(f"============================================================")
    print(f"Sending 6 concurrent requests simultaneously to {URL}...")
    print(f"============================================================\n")

    overall_start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(send_request, TEST_QUERIES))

    total_wall_time = (time.perf_counter() - overall_start) * 1000.0

    print(f"{'USER':<8} | {'STATUS':<7} | {'CATEGORY':<12} | {'URGENCY':<9} | {'HANDLER':<18} | {'ROUNDTRIP'}")
    print("-" * 75)

    for r in results:
        user = r["user"]
        status = r["status"]
        elapsed = f"{r['elapsed_ms']} ms"

        if "data" in r:
            d = r["data"]
            category = d.get("category", "N/A")
            urgency = d.get("urgency", "N/A")
            handler = d.get("target_agent", "N/A")
            print(f"{user:<8} | {status:<7} | {category:<12} | {urgency:<9} | {handler:<18} | {elapsed}")
        else:
            err = r.get("error", "Unknown error")
            print(f"{user:<8} | {status:<7} | ERROR: {err[:40]} | {elapsed}")

    print("-" * 75)
    print(f"Total wall-clock duration for all 6 concurrent requests: {round(total_wall_time, 2)} ms\n")


if __name__ == "__main__":
    main()
