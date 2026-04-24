from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path


FIELDNAMES = [
    "question",
    "questionImages",
    "options",
    "answer",
    "Explanation",
    "explanationImages",
]

PLACEHOLDER_ACTIVITY_OPTION = [
    {"label": "A", "text": "See Explanation section for answer.", "images": []}
]


def option_rows(*texts: str) -> list[dict[str, object]]:
    return [
        {"label": chr(ord("A") + index), "text": text, "images": []}
        for index, text in enumerate(texts)
    ]


PATCHES: dict[int, dict[str, object]] = {
    45: {
        "expected": "ports on DNSSrv must remain open",
        "options": option_rows("20", "21", "22", "23", "53"),
        "answer": "E",
    },
    51: {
        "expected": "proxy server has two interfaces",
        "question": "HOTSPOT (Drag and Drop is not supported) A systems administrator deployed a new web proxy server onto the network. The proxy server has two interfaces: the first is connected to an internal corporate firewall, and the second is connected to an internet-facing firewall. Many users at the company are reporting they are unable to access the Internet since the new proxy was introduced. Analyze the network diagram and the proxy server's host routing table to resolve the Internet connectivity issues. INSTRUCTIONS Perform the following steps: 1. Click on the proxy server to display its routing table. 2. Modify the appropriate route entries to resolve the Internet connectivity issue. If at any time you would like to bring back the initial state of the simulation, please click the Reset All button. Hot Area:",
        "options": PLACEHOLDER_ACTIVITY_OPTION,
        "answer": "A",
    },
    55: {
        "expected": "4U rack servers",
        "question": "A data center has 4U rack servers that need to be replaced using VMs but without losing any data. Which of the following methods will MOST likely be used to replace these servers?",
        "options": option_rows("VMFS", "Unattended scripted OS installation", "P2V", "VM cloning"),
        "answer": "C",
        "Explanation": "P2V (Physical to Virtual) is a method of converting a physical server into a virtual machine that can run on a hypervisor. This method can be used to replace 4U rack servers with VMs without losing any data, as it preserves the configuration and state of the original server. P2V can also reduce hardware costs, power consumption, and space requirements. References: [What is P2V?]",
    },
    65: {
        "expected": "open ports should be closed",
        "options": option_rows("21", "22", "23", "53", "443", "636"),
        "answer": "AC",
    },
    72: {
        "expected": "storage servers",
        "question": "A server administrator is building a pair of new storage servers. The servers will replicate; therefore, no redundancy is required, but usable capacity must be maximized. Which of the following RAID levels should the server administrator implement?",
        "options": option_rows("0", "1", "5", "6", "10"),
        "answer": "A",
    },
    99: {
        "expected": "new domain controller",
        "options": option_rows("135", "636", "3268", "3389"),
        "answer": "D",
    },
    100: {
        "expected": "new secure web server",
        "options": option_rows("53", "80", "389", "443", "445", "3389", "8080"),
        "answer": "DF",
        "Explanation": "Port 443 is used for HTTPS, which a secure web server needs for client traffic. Port 3389 is used for RDP, which is the only permitted administration method in this scenario. Therefore, the two ports that should remain allowed are 443 and 3389.",
    },
    105: {
        "expected": "allow SSH, FTP, and LDAP traffic",
        "options": option_rows("21", "22", "53", "67", "69", "110", "123", "389"),
        "answer": "ABH",
    },
    114: {
        "expected": "A recent power Outage caused email services to go down",
        "question": "DRAG DROP (Drag and Drop is not supported) A recent power outage caused email services to go down. A server administrator also received alerts from the datacenter's UPS. After some investigation, the server administrator learned that each PDU was rated at a maximum of 12A. INSTRUCTIONS Ensure power redundancy is implemented throughout each rack and UPS alarms are resolved. Ensure the maximum potential PDU consumption does not exceed 80% or 9.6A.",
        "options": PLACEHOLDER_ACTIVITY_OPTION,
        "answer": "A",
    },
    123: {
        "expected": "hosting a secure website",
        "options": option_rows("25", "443", "3389", "8080"),
        "answer": "B",
    },
    134: {
        "expected": "survive the failure of two drives",
        "options": option_rows("0", "1", "5", "6"),
        "answer": "D",
        "Explanation": "RAID 6 is a level of RAID that can survive the failure of two drives without the loss of data. RAID 6 uses block-level striping with two parity blocks distributed across all member disks. RAID 6 can tolerate two simultaneous drive failures and still provide data access and redundancy. RAID 0 uses striping without parity or mirroring and offers no fault tolerance. RAID 1 can survive one drive failure, but not two. RAID 5 can tolerate one drive failure, but not two.",
    },
    137: {
        "expected": "10GB of RAID 1 for log files",
        "options": option_rows("6", "7", "8", "9"),
        "answer": "C",
    },
    142: {
        "expected": "ports on DNSSrv must remain open",
        "question": "A security analyst completed a port scan of the corporate production-server network. Results of the scan were then provided to a systems administrator for immediate action. The following table represents the requested changes: The systems administrator created local firewall rules to block the ports indicated above. Immediately, the service desk began receiving calls about the internet being down. The systems administrator then reversed the changes, and the internet became available again. Which of the following ports on DNSSrv must remain open when the firewall rules are reapplied?",
        "options": option_rows("20", "21", "22", "23", "53"),
        "answer": "E",
    },
    146: {
        "expected": "warm site",
        "question": "A site is considered a warm site when it:",
        "options": option_rows(
            "has basic technical facilities connected to it.",
            "has faulty air conditioning that is awaiting service.",
            "is almost ready to take over all operations from the primary site.",
            "is fully operational and continuously providing services.",
        ),
        "answer": "C",
    },
    154: {
        "expected": "monitor and record",
        "question": "A technician is deploying a single server to monitor and record the security cameras at a remote site. Which of the following architecture types should be used to minimize cost?",
        "options": option_rows("Virtual", "Blade", "Tower", "Rack mount"),
        "answer": "C",
    },
    171: {
        "expected": "driver's license",
        "question": "A data center employee shows a driver's license to enter the facility. Once the employee enters, the door immediately closes and locks, triggering a scale that then weighs the employee before granting access to another locked door. This is an example of:",
        "options": option_rows("mantrap.", "a bollard.", "geofencing.", "RFID."),
        "answer": "A",
    },
    241: {
        "expected": "storage servers",
        "question": "A server administrator is building a pair of new storage servers. The servers will replicate; therefore, no redundancy is required, but usable capacity must be maximized. Which of the following RAID levels should the server administrator implement?",
        "options": option_rows("0", "1", "5", "6", "10"),
        "answer": "A",
    },
    253: {
        "expected": "A recent power Outage caused email services to go down",
        "question": "DRAG DROP (Drag and Drop is not supported) A recent power outage caused email services to go down. A server administrator also received alerts from the datacenter's UPS. After some investigation, the server administrator learned that each PDU was rated at a maximum of 12A. INSTRUCTIONS Ensure power redundancy is implemented throughout each rack and UPS alarms are resolved. Ensure the maximum potential PDU consumption does not exceed 80% or 9.6A.",
        "options": PLACEHOLDER_ACTIVITY_OPTION,
        "answer": "A",
    },
}


def load_records(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def dump_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True)


def apply_patches(records: list[dict[str, str]]) -> list[int]:
    patched_rows: list[int] = []

    for row_number, patch in PATCHES.items():
        if not (1 <= row_number <= len(records)):
            raise ValueError(f"Row {row_number} is out of range for {len(records)} exported questions")

        record = records[row_number - 1]
        expected = str(patch["expected"]).lower()
        if expected not in record["question"].lower():
            raise ValueError(
                f"Row {row_number} no longer matches the expected question signature. "
                f"Expected fragment {expected!r}, got {record['question']!r}"
            )

        for field in ("question", "answer", "Explanation"):
            if field in patch:
                record[field] = str(patch[field])

        if "options" in patch:
            record["options"] = dump_json(patch["options"])

        if "questionImages" in patch:
            record["questionImages"] = dump_json(patch["questionImages"])

        if "explanationImages" in patch:
            record["explanationImages"] = dump_json(patch["explanationImages"])

        patched_rows.append(row_number)

    return patched_rows


def validate_records(records: list[dict[str, str]]) -> None:
    for row_number, patch in PATCHES.items():
        record = records[row_number - 1]
        options = json.loads(record["options"])
        answer = record["answer"].strip()

        if not options:
            raise ValueError(f"Row {row_number} still has no selectable options after patching")

        labels = {option["label"] for option in options}
        missing_labels = [label for label in answer if label not in labels]
        if missing_labels:
            raise ValueError(
                f"Row {row_number} answer {answer!r} does not map to option labels {sorted(labels)}"
            )

        if patch.get("options") == PLACEHOLDER_ACTIVITY_OPTION and answer != "A":
            raise ValueError(f"Row {row_number} is an activity placeholder but answer is not 'A'")


def write_csv(records: list[dict[str, str]], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def write_sql(records: list[dict[str, str]], destination: Path) -> None:
    lines = [
        "BEGIN TRANSACTION;",
        "DROP TABLE IF EXISTS questions;",
        "CREATE TABLE questions (",
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,",
        "    question TEXT NOT NULL,",
        "    question_images TEXT NOT NULL DEFAULT '[]',",
        "    options TEXT NOT NULL,",
        "    answer TEXT,",
        "    explanation TEXT,",
        "    explanation_images TEXT NOT NULL DEFAULT '[]'",
        ");",
    ]

    for record in records:
        lines.append(
            "INSERT INTO questions (question, question_images, options, answer, explanation, explanation_images) VALUES "
            f"('{sql_escape(record['question'])}', "
            f"'{sql_escape(record['questionImages'])}', "
            f"'{sql_escape(record['options'])}', "
            f"'{sql_escape(record['answer'])}', "
            f"'{sql_escape(record['Explanation'])}', "
            f"'{sql_escape(record['explanationImages'])}');"
        )

    lines.append("COMMIT;")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sqlite_db(records: list[dict[str, str]], destination: Path) -> None:
    with sqlite3.connect(destination) as connection:
        cursor = connection.cursor()
        cursor.executescript(
            """
            DROP TABLE IF EXISTS questions;
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                question_images TEXT NOT NULL DEFAULT '[]',
                options TEXT NOT NULL,
                answer TEXT,
                explanation TEXT,
                explanation_images TEXT NOT NULL DEFAULT '[]'
            );
            """
        )
        cursor.executemany(
            """
            INSERT INTO questions (question, question_images, options, answer, explanation, explanation_images)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    record["question"],
                    record["questionImages"],
                    record["options"],
                    record["answer"],
                    record["Explanation"],
                    record["explanationImages"],
                )
                for record in records
            ],
        )
        connection.commit()


def main() -> None:
    workspace = Path(__file__).resolve().parent
    csv_path = workspace / "questions_sqlite.csv"
    sql_path = workspace / "questions_sqlite.sql"
    db_path = workspace / "questions.db"

    records = load_records(csv_path)
    patched_rows = apply_patches(records)
    validate_records(records)
    write_csv(records, csv_path)
    write_sql(records, sql_path)
    write_sqlite_db(records, db_path)

    print(f"Patched {len(patched_rows)} rows: {', '.join(str(row) for row in patched_rows)}")
    print(f"CSV: {csv_path}")
    print(f"SQL: {sql_path}")
    print(f"DB: {db_path}")


if __name__ == "__main__":
    main()