"""Fetch and store data from all completed rounds.

Downloads: round details, initial states, ground truth, and our predictions.
Safe to re-run — skips data that's already stored locally.
"""

from api import get_rounds, get_round_detail, get_analysis, get_my_predictions
import store


def main():
    rounds = get_rounds()
    completed = [r for r in rounds if r["status"] == "completed"]
    completed.sort(key=lambda r: r["round_number"])

    print(f"Found {len(completed)} completed rounds\n")

    for rnd in completed:
        rn = rnd["round_number"]
        rid = rnd["id"]
        print(f"=== Round {rn} (id={rid}) ===")

        # Round detail + initial states
        if store.load_round_meta(rn) is None:
            detail = get_round_detail(rid)
            store.save_round(rn, detail)
            seeds = detail.get("seeds_count", len(detail.get("initial_states", [])))
            print(f"  Saved round meta + {seeds} initial states")
        else:
            meta = store.load_round_meta(rn)
            seeds = meta["seeds_count"]
            print(f"  Round meta already stored ({seeds} seeds)")

        # Ground truth for each seed
        for si in range(seeds):
            if store.load_ground_truth(rn, si) is None:
                try:
                    analysis = get_analysis(rid, si)
                    store.save_ground_truth(rn, si, analysis)
                    score = analysis.get("score")
                    print(f"  Seed {si}: ground truth saved (score={score})")
                except Exception as e:
                    print(f"  Seed {si}: ground truth failed — {e}")
            else:
                print(f"  Seed {si}: ground truth already stored")

        # Our predictions
        try:
            preds = get_my_predictions(rid)
            for p in preds:
                si = p["seed_index"]
                store.save_prediction(rn, si, p)
            if preds:
                print(f"  Saved {len(preds)} predictions")
            else:
                print(f"  No predictions submitted for this round")
        except Exception as e:
            print(f"  Predictions fetch failed — {e}")

        print()

    print("Done. Stored rounds:", store.list_stored_rounds())


if __name__ == "__main__":
    main()
