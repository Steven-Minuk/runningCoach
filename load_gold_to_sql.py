import json

from sql_loader import get_db_connection, insert_run_summary_if_not_exists


def load_gold_json(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    file_path = "output/2021-06-08-180353_summary.json"
    summary = load_gold_json(file_path)

    conn = get_db_connection()
    try:
        inserted = insert_run_summary_if_not_exists(conn, summary)
        if inserted:
            print(f"Inserted run_id={summary['run_id']} into runs table.")
        else:
            print(f"Skipped run_id={summary['run_id']} because it already exists.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()