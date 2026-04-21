from __future__ import annotations

import base64
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import TypedDict


PKG_NS = "http://schemas.microsoft.com/office/2006/xmlPackage"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
RELS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"pkg": PKG_NS, "w": W_NS, "a": A_NS, "r": R_NS, "rels": RELS_NS}

W_TAG = f"{{{W_NS}}}"
R_EMBED = f"{{{R_NS}}}embed"
PKG_NAME = f"{{{PKG_NS}}}name"
PKG_CONTENT_TYPE = f"{{{PKG_NS}}}contentType"

QUESTION_RE = re.compile(r"^NEW QUESTION\s+(\d+)(?:\s+.*)?$", re.IGNORECASE)
INLINE_OPTION_RE = re.compile(r"^(.*?[?:])\s+([A-Z])\.\s+(.+)$")
COMPACT_INLINE_OPTIONS_RE = re.compile(r"^(.*?[?:])\s+((?:[A-Z]\s+[^A-Z]+?\s*){2,})$")
COMPACT_OPTION_PAIR_RE = re.compile(r"([A-Z])\s+([^A-Z]+?)(?=\s+[A-Z]\s+|$)")
ANSWER_LINE_RE = re.compile(
    r"^(?:Correct\s+)?Answer:\s*([A-Z][A-Z,\s]*)\s*(?:Explanation:\s*(.*))?$",
    re.IGNORECASE,
)
SQUASHED_OPTION_RE = re.compile(r"^([A-Z])([0-9].*)$")
SHORT_LABELED_OPTION_RE = re.compile(r"^([A-Z])[.)]?\s+(.+)$")
REFERENCE_MARKER_RE = re.compile(r"\b(?:Verified\s+)?References?\s*[:=]\s*", re.IGNORECASE)
REFERENCE_LIKE_RE = re.compile(
    r"(?:https?://|www\.|comptia|exam objectives|certification study guide|\bdomain\s+\d|\bobjective\s+\d|^\[[^\]]+\])",
    re.IGNORECASE,
)
QUESTION_NUMBER_ONLY_RE = re.compile(r"^\d+$")
DEFAULT_SOURCE_FILES = [
    "sk0-005_0.pdf.xml",
    "sk0-005_2.pdf.xml",
    "sk0-005_5.xml",
]


class ParagraphPayload(TypedDict):
    text: str
    images: list[str]


class OptionDraft(TypedDict):
    text: str
    images: list[str]


class OptionRow(TypedDict):
    label: str
    text: str
    images: list[str]


class QuestionDraft(TypedDict):
    source: str
    questionID: int
    question_lines: list[str]
    question_images: list[str]
    options: list[OptionDraft]
    answer: str
    explanation_lines: list[str]
    explanation_images: list[str]


class QuestionRow(TypedDict):
    source: str
    questionID: int
    question: str
    questionImages: str
    options: str
    answer: str
    Explanation: str
    explanationImages: str


MANUAL_EXPLANATIONS = {
    "due to a disaster incident on a primary site, corporate users are redirected to cloud services where they will be required to be authenticated just once in order to use all cloud services. which of the following types of authentications is described in this scenario?": (
        "SSO is the correct answer because the scenario describes users authenticating one time and then being able to access multiple cloud services without signing in again. "
        "Single sign-on centralizes authentication through one identity provider, which is commonly used in disaster recovery or cloud failover scenarios so users can continue working across multiple applications with one login. "
        "MFA can be part of the sign-in flow, but it does not by itself provide access to multiple services after a single authentication event. NTLM and Kerberos are authentication protocols, not the broader user experience being described here."
    )
}


def normalize_text(value: str) -> str:
    value = value.replace("\xa0", " ")
    value = value.replace("\r", " ").replace("\n", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def tidy_text(value: str) -> str:
    value = normalize_text(value)
    replacements = {
        "it.References": "it. References",
        "leastamount": "least amount",
        "onedisk": "one disk",
        "limitthe": "limit the",
        "foreach": "for each",
        "requiredto": "required to",
        "clientsoftware": "client software",
        "thepingcommand": "the ping command",
        "thepingandipconfigcommands": "the ping and ipconfig commands",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+([,.;:?!])", r"\1", value)
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    value = re.sub(r"\\\\\s+", r"\\\\", value)
    value = re.sub(r"\s+\\", r" \\", value)
    return normalize_text(value)


def normalize_answer(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalpha())


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []

    for value in values:
        candidate = value.strip()
        if not candidate:
            continue
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)

    return deduped


def normalize_part_name(part_name: str, target: str) -> str:
    if target.startswith("/"):
        return target

    base = PurePosixPath(part_name).parent
    combined = base.joinpath(target)
    normalized_parts: list[str] = []
    for item in combined.parts:
        if item in ("", "/", "."):
            continue
        if item == "..":
            if normalized_parts:
                normalized_parts.pop()
            continue
        normalized_parts.append(item)
    return "/" + "/".join(normalized_parts)


class PackageAssets:
    def __init__(self, root: ET.Element, workspace: Path, source_path: Path) -> None:
        self.workspace = workspace
        self.source_path = source_path
        self.relationships = self._load_relationships(root)
        self.binary_parts = self._load_binary_parts(root)
        self.output_dir = workspace / "extracted_images" / self._source_key(source_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.saved_assets: dict[str, str] = {}

    def _source_key(self, source_path: Path) -> str:
        return re.sub(r"[^a-zA-Z0-9._-]+", "_", source_path.stem)

    def _load_relationships(self, root: ET.Element) -> dict[str, str]:
        part = root.find("pkg:part[@pkg:name='/word/_rels/document.xml.rels']/pkg:xmlData", NS)
        if part is None or not len(part):
            return {}

        relationships_root = part[0]
        relationships: dict[str, str] = {}
        for relationship in relationships_root.findall("rels:Relationship", NS):
            relationship_id = relationship.attrib.get("Id")
            target = relationship.attrib.get("Target")
            if relationship_id and target:
                relationships[relationship_id] = normalize_part_name("/word/document.xml", target)
        return relationships

    def _load_binary_parts(self, root: ET.Element) -> dict[str, tuple[str, str]]:
        parts: dict[str, tuple[str, str]] = {}
        for part in root.findall("pkg:part", NS):
            name = part.attrib.get(PKG_NAME)
            content_type = part.attrib.get(PKG_CONTENT_TYPE, "")
            binary = part.find("pkg:binaryData", NS)
            if name and binary is not None and binary.text:
                parts[name] = (content_type, binary.text)
        return parts

    def extract_paragraph_images(self, paragraph: ET.Element) -> list[str]:
        images: list[str] = []
        for blip in paragraph.iterfind(".//a:blip", NS):
            relationship_id = blip.attrib.get(R_EMBED)
            if not relationship_id:
                continue
            target = self.relationships.get(relationship_id)
            if not target:
                continue
            saved_path = self._save_image(target)
            if saved_path:
                images.append(saved_path)
        return dedupe_preserve_order(images)

    def _save_image(self, part_name: str) -> str | None:
        if part_name in self.saved_assets:
            return self.saved_assets[part_name]

        payload = self.binary_parts.get(part_name)
        if payload is None:
            return None

        _, binary_text = payload
        binary_bytes = base64.b64decode(re.sub(r"\s+", "", binary_text))
        output_path = self.output_dir / PurePosixPath(part_name).name
        output_path.write_bytes(binary_bytes)
        relative_path = output_path.relative_to(self.workspace).as_posix()
        self.saved_assets[part_name] = relative_path
        return relative_path


def paragraph_payload(paragraph: ET.Element, assets: PackageAssets | None = None) -> ParagraphPayload:
    parts: list[str] = []
    has_drawing = False

    for element in paragraph.iter():
        if element.tag == f"{W_TAG}t":
            parts.append(element.text or "")
        elif element.tag == f"{W_TAG}tab":
            parts.append(" ")
        elif element.tag == f"{W_TAG}br":
            parts.append(" ")
        elif element.tag == f"{W_TAG}drawing":
            has_drawing = True

    text = normalize_text("".join(parts))
    images = assets.extract_paragraph_images(paragraph) if assets else []
    if not text and has_drawing and not images:
        text = "[IMAGE]"
    return {"text": text, "images": images}


def paragraph_text(paragraph: ET.Element) -> str:
    payload = paragraph_payload(paragraph)
    if payload["text"]:
        return payload["text"]
    if payload["images"]:
        return "[IMAGE]"
    return ""


def has_numbering(paragraph: ET.Element) -> bool:
    return paragraph.find("w:pPr/w:numPr", NS) is not None


def question_record(question_id: int, source_name: str) -> QuestionDraft:
    return {
        "source": source_name,
        "questionID": question_id,
        "question_lines": [],
        "question_images": [],
        "options": [],
        "answer": "",
        "explanation_lines": [],
        "explanation_images": [],
    }


def add_option(record: QuestionDraft, text: str = "", images: list[str] | None = None) -> None:
    cleaned_text = tidy_text(text)
    option_images = dedupe_preserve_order(images or [])
    if not cleaned_text and not option_images:
        return
    record["options"].append({"text": cleaned_text, "images": option_images})


def is_promotional_record(record: QuestionRow) -> bool:
    question_text = str(record["question"]).lower()
    promotional_markers = [
        "thank you for trying our product",
        "powered by tcpdf",
        "practice exam features",
    ]
    return any(marker in question_text for marker in promotional_markers)


def parse_compact_inline_options(text: str) -> tuple[str, list[str]] | None:
    match = COMPACT_INLINE_OPTIONS_RE.match(text)
    if not match:
        return None

    option_block = normalize_text(match.group(2))
    option_matches = COMPACT_OPTION_PAIR_RE.findall(option_block)
    if len(option_matches) < 2:
        return None

    options = [normalize_text(option_text) for _, option_text in option_matches]
    return normalize_text(match.group(1)), options


def parse_answer_line(text: str) -> tuple[str, str] | None:
    compact_match = re.match(r"^(?:Correct\s+)?Answer:\s*Explanation:\s*([A-Z][A-Z,\s]*)$", text, re.IGNORECASE)
    if compact_match:
        return normalize_answer(compact_match.group(1)), ""

    match = ANSWER_LINE_RE.match(text)
    if not match:
        return None

    answer = normalize_answer(match.group(1))
    explanation = normalize_text(match.group(2) or "")
    return answer, explanation


def split_answer_tail(text: str) -> tuple[str, str, str]:
    compact_match = re.search(r"(?:Correct\s+)?Answer:\s*Explanation:\s*([A-Z][A-Z,\s]*)$", text, re.IGNORECASE)
    if compact_match:
        prefix = tidy_text(text[: compact_match.start()])
        answer = normalize_answer(compact_match.group(1))
        return prefix, answer, ""

    match = re.search(r"(?:Correct\s+)?Answer:\s*([A-Z][A-Z,\s]*)(?:\s*Explanation:\s*(.*))?$", text, re.IGNORECASE)
    if not match:
        return tidy_text(text), "", ""

    prefix = tidy_text(text[: match.start()])
    answer = normalize_answer(match.group(1))
    explanation = tidy_text(match.group(2) or "")
    return prefix, answer, explanation


def is_reference_like(text: str) -> bool:
    normalized = tidy_text(text)
    if not normalized:
        return False
    if REFERENCE_MARKER_RE.search(normalized):
        return True
    if REFERENCE_LIKE_RE.search(normalized):
        return True
    return normalized.startswith("[") and normalized.endswith("]")


def split_reference_marker(text: str) -> tuple[str, str]:
    match = REFERENCE_MARKER_RE.search(text)
    if not match:
        return tidy_text(text), ""

    main_text = tidy_text(text[: match.start()])
    reference_text = tidy_text(text[match.end() :])
    return main_text, reference_text


def reorganize_reference_text(
    question_lines: list[str],
    explanation_lines: list[str],
) -> tuple[list[str], list[str]]:
    clean_question_lines: list[str] = []
    clean_explanation_lines: list[str] = []
    reference_lines: list[str] = []

    def collect(lines: list[str], destination: list[str]) -> None:
        collecting_references = False

        for raw_line in lines:
            line = tidy_text(raw_line)
            if not line:
                continue

            main_text, inline_reference = split_reference_marker(line)
            if inline_reference:
                if main_text:
                    destination.append(main_text)
                reference_lines.append(inline_reference)
                collecting_references = True
                continue

            if collecting_references and is_reference_like(line):
                reference_lines.append(line)
                continue

            if is_reference_like(line):
                reference_lines.append(line)
                collecting_references = True
                continue

            destination.append(line)

    collect(question_lines, clean_question_lines)
    collect(explanation_lines, clean_explanation_lines)

    clean_question_lines = dedupe_preserve_order(clean_question_lines)
    clean_explanation_lines = dedupe_preserve_order(clean_explanation_lines)
    reference_lines = dedupe_preserve_order(reference_lines)

    if reference_lines:
        clean_explanation_lines.append(f"References: {' '.join(reference_lines)}")

    return clean_question_lines, clean_explanation_lines


def canonical_question(text: str) -> str:
    base_text, _ = split_reference_marker(tidy_text(text))
    return re.sub(r"\s+", " ", base_text).strip().lower()


def finalize_record(record: QuestionDraft) -> QuestionRow:
    question_lines = [line for line in record["question_lines"] if line]
    explanation_lines = [line for line in record["explanation_lines"] if line]
    question_lines, explanation_lines = reorganize_reference_text(question_lines, explanation_lines)

    question_text = tidy_text(" ".join(question_lines))
    explanation_text = tidy_text(" ".join(explanation_lines))
    if not explanation_text:
        explanation_text = MANUAL_EXPLANATIONS.get(canonical_question(question_text), "")

    question_images = dedupe_preserve_order(record["question_images"])
    explanation_images = dedupe_preserve_order(record["explanation_images"])
    normalized_options: list[OptionRow] = []
    for index, option in enumerate(record["options"]):
        normalized_options.append(
            {
                "label": chr(ord("A") + index),
                "text": tidy_text(option["text"]),
                "images": dedupe_preserve_order(option["images"]),
            }
        )

    return {
        "source": record["source"],
        "questionID": record["questionID"],
        "question": question_text,
        "questionImages": json.dumps(question_images, ensure_ascii=True),
        "options": json.dumps(normalized_options, ensure_ascii=True),
        "answer": normalize_answer(record["answer"]),
        "Explanation": explanation_text,
        "explanationImages": json.dumps(explanation_images, ensure_ascii=True),
    }


def extract_questions(source_path: Path) -> list[QuestionRow]:
    tree = ET.parse(source_path)
    root = tree.getroot()

    document_part = root.find("pkg:part[@pkg:name='/word/document.xml']/pkg:xmlData/w:document", NS)
    if document_part is None:
        raise ValueError("Could not locate /word/document.xml in the XML package.")

    body = document_part.find("w:body", NS)
    if body is None:
        raise ValueError("Could not locate the document body.")

    assets = PackageAssets(root, source_path.resolve().parent, source_path)
    paragraphs = list(body.iterfind(".//w:p", NS))

    records: list[QuestionRow] = []
    current: QuestionDraft | None = None
    mode = "idle"

    for paragraph in paragraphs:
        payload = paragraph_payload(paragraph, assets)
        text = payload["text"]
        images = payload["images"]
        if not text and not images:
            continue

        question_match = QUESTION_RE.match(text) if text else None
        if question_match:
            if current is not None:
                finalized = finalize_record(current)
                if not is_promotional_record(finalized):
                    records.append(finalized)
            current = question_record(int(question_match.group(1)), source_path.name)
            mode = "question"
            continue

        if current is None:
            continue

        parsed_answer = parse_answer_line(text) if text else None
        if parsed_answer:
            answer, explanation_text = parsed_answer
            current["answer"] = answer
            if explanation_text:
                current["explanation_lines"].append(explanation_text)
            if images:
                current["explanation_images"].extend(images)
            mode = "after_answer"
            continue

        if text.startswith("Explanation:") if text else False:
            explanation_text = tidy_text(text.split(":", 1)[1])
            if explanation_text:
                current["explanation_lines"].append(explanation_text)
            if images:
                current["explanation_images"].extend(images)
            mode = "explanation"
            continue

        if mode == "question":
            squashed_option_match = SQUASHED_OPTION_RE.match(text) if text else None
            if squashed_option_match:
                add_option(current, squashed_option_match.group(2), images)
                continue

            short_labeled_option_match = SHORT_LABELED_OPTION_RE.match(text) if text else None
            if short_labeled_option_match and text and len(text) <= 12:
                add_option(current, short_labeled_option_match.group(2), images)
                continue

            compact_inline_options = parse_compact_inline_options(text) if text else None
            if compact_inline_options and not has_numbering(paragraph):
                question_text, option_texts = compact_inline_options
                current["question_lines"].append(tidy_text(question_text))
                current["question_images"].extend(images)
                for option_text in option_texts:
                    add_option(current, option_text)
                continue

            inline_option_match = INLINE_OPTION_RE.match(text) if text else None
            if inline_option_match and not has_numbering(paragraph):
                current["question_lines"].append(tidy_text(inline_option_match.group(1)))
                current["question_images"].extend(images)
                add_option(current, inline_option_match.group(3))
                continue

            if has_numbering(paragraph):
                option_text, answer_text, explanation_text = split_answer_tail(text)
                if option_text and not QUESTION_NUMBER_ONLY_RE.match(option_text):
                    add_option(current, option_text, images)
                elif images:
                    add_option(current, "", images)
                if answer_text:
                    current["answer"] = answer_text
                    if explanation_text:
                        current["explanation_lines"].append(explanation_text)
                    mode = "after_answer"
                continue

            if text:
                current["question_lines"].append(tidy_text(text))
            if images:
                current["question_images"].extend(images)
            continue

        if text:
            current["explanation_lines"].append(tidy_text(text))
        if images:
            current["explanation_images"].extend(images)
        mode = "explanation"

    if current is not None:
        finalized = finalize_record(current)
        if not is_promotional_record(finalized):
            records.append(finalized)

    return records


def merge_records(source_paths: list[Path]) -> tuple[list[QuestionRow], list[dict[str, object]]]:
    merged: list[QuestionRow] = []
    duplicates: list[dict[str, object]] = []
    seen_by_question: dict[str, QuestionRow] = {}

    for source_path in source_paths:
        for record in extract_questions(source_path):
            key = canonical_question(record["question"])
            if key in seen_by_question:
                existing = seen_by_question[key]
                duplicates.append(
                    {
                        "source": record["source"],
                        "questionID": record["questionID"],
                        "duplicateOfSource": existing["source"],
                        "duplicateOfQuestionID": existing["questionID"],
                        "question": record["question"],
                    }
                )
                continue

            seen_by_question[key] = record
            merged.append(record)

    return merged, duplicates


def write_csv(records: list[QuestionRow], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "questionID",
                "question",
                "questionImages",
                "options",
                "answer",
                "Explanation",
                "explanationImages",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(records)


def write_duplicate_report(records: list[dict[str, object]], destination: Path) -> None:
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source",
                "questionID",
                "duplicateOfSource",
                "duplicateOfQuestionID",
                "question",
            ],
        )
        writer.writeheader()
        writer.writerows(records)


def sql_escape(value: str) -> str:
    return value.replace("'", "''")


def write_sql(records: list[QuestionRow], destination: Path) -> None:
    lines = [
        "BEGIN TRANSACTION;",
        "DROP TABLE IF EXISTS questions;",
        "CREATE TABLE questions (",
        "    id INTEGER PRIMARY KEY AUTOINCREMENT,",
        "    questionID INTEGER NOT NULL,",
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
            "INSERT INTO questions (questionID, question, question_images, options, answer, explanation, explanation_images) VALUES "
            f"({record['questionID']}, "
            f"'{sql_escape(record['question'])}', "
            f"'{sql_escape(record['questionImages'])}', "
            f"'{sql_escape(record['options'])}', "
            f"'{sql_escape(record['answer'])}', "
            f"'{sql_escape(record['Explanation'])}', "
            f"'{sql_escape(record['explanationImages'])}');"
        )

    lines.append("COMMIT;")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def discover_source_files(workspace: Path) -> list[Path]:
    source_files = [workspace / file_name for file_name in DEFAULT_SOURCE_FILES]
    return [path for path in source_files if path.is_file()]


def main() -> None:
    workspace = Path(__file__).resolve().parent
    sources = discover_source_files(workspace)
    csv_output = workspace / "questions_sqlite.csv"
    sql_output = workspace / "questions_sqlite.sql"
    duplicate_output = workspace / "questions_duplicates.csv"

    records, duplicates = merge_records(sources)
    write_csv(records, csv_output)
    write_sql(records, sql_output)
    write_duplicate_report(duplicates, duplicate_output)

    missing_answers = sum(1 for record in records if not record["answer"])
    missing_explanations = sum(
        1 for record in records if not record["Explanation"] and not json.loads(record["explanationImages"])
    )
    question_images = sum(1 for record in records if json.loads(record["questionImages"]))
    explanation_images = sum(1 for record in records if json.loads(record["explanationImages"]))

    print(f"Sources: {', '.join(source.name for source in sources)}")
    print(f"Extracted {len(records)} records")
    print(f"Duplicates skipped: {len(duplicates)}")
    print(f"Rows missing answers: {missing_answers}")
    print(f"Rows missing explanations: {missing_explanations}")
    print(f"Rows with question images: {question_images}")
    print(f"Rows with explanation images: {explanation_images}")
    print(f"CSV: {csv_output}")
    print(f"SQL: {sql_output}")
    print(f"Duplicates: {duplicate_output}")


if __name__ == "__main__":
    main()