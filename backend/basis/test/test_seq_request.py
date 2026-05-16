import requests
import json

BASE = "http://localhost:8000/basis"

def test_single_sequence():
    data = {
        "genome_id": "1",
        "seq_type": "mRNA",
        "seq_id": "AT1G01020.3",
        "start": 100,
        "end": 200
    }
    r = requests.post(f"{BASE}/sequence", json=data)
    print("Single Sequence Result:")
    print(json.dumps(r.json(), indent=2))


def test_batch_sequence():
    data = {
        "genome_id": "1",
        "seq_type": "genome",
        "regions": [
            {"seq_id": "Chr1", "start": 100, "end": 500},
            {"seq_id": "Chr2", "start": 200, "end": 600},
            {"seq_id": "Chr3", "start": 1, "end": 100}
        ]
    }
    r = requests.post(f"{BASE}/sequences/batch", json=data)
    result = r.json()
    print("Batch Sequence Result:")
    print(json.dumps(result, indent=2))
    if result.get("download_url"):
        print("➡️ Download available at:", result["download_url"])


'''
def download_if_needed(resp: dict):
    if resp.get("download_url"):
        print(f"Download from: {resp['download_url']}")
        download_resp = requests.get(resp["download_url"])
        fname = resp["download_url"].split("/")[-1]
        with open(fname, "wb") as f:
            f.write(download_resp.content)
        print(f"Downloaded to {fname}")
'''


if __name__ == "__main__":
    test_single_sequence()
    test_batch_sequence()
