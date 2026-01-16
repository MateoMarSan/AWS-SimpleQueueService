import json
import os
import time
import urllib.parse
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
textract = boto3.client("textract")

OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]
OUTPUT_PREFIX = os.environ.get("OUTPUT_PREFIX", "outputs/").strip()
if OUTPUT_PREFIX and not OUTPUT_PREFIX.endswith("/"):
    OUTPUT_PREFIX += "/"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
PDF_EXTS = {".pdf"}
TEXT_EXTS = {".txt"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_ext(key: str) -> str:
    key_l = key.lower()
    dot = key_l.rfind(".")
    return key_l[dot:] if dot != -1 else ""


def _read_txt_from_s3(bucket: str, key: str) -> str:
    resp = s3.get_object(Bucket=bucket, Key=key)
    content = resp["Body"].read()
    return content.decode("utf-8", errors="replace").strip()


def _textract_sync_image(bucket: str, key: str) -> str:
    resp = textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )
    lines = []
    for block in resp.get("Blocks", []):
        if block.get("BlockType") == "LINE" and "Text" in block:
            lines.append(block["Text"])
    return "\n".join(lines).strip()


def _textract_async_pdf(bucket: str, key: str, timeout_s: int = 90) -> str:
    start = textract.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}}
    )
    job_id = start["JobId"]

    deadline = time.time() + timeout_s
    status = "IN_PROGRESS"
    while time.time() < deadline:
        time.sleep(2)
        r = textract.get_document_text_detection(JobId=job_id, MaxResults=1000)
        status = r.get("JobStatus", "IN_PROGRESS")
        if status in ("SUCCEEDED", "FAILED", "PARTIAL_SUCCESS"):
            break

    if status not in ("SUCCEEDED", "PARTIAL_SUCCESS"):
        raise RuntimeError(f"Textract job not finished. JobStatus={status}, JobId={job_id}")

    lines = []
    next_token = None
    while True:
        kwargs = {"JobId": job_id, "MaxResults": 1000}
        if next_token:
            kwargs["NextToken"] = next_token
        r = textract.get_document_text_detection(**kwargs)

        for block in r.get("Blocks", []):
            if block.get("BlockType") == "LINE" and "Text" in block:
                lines.append(block["Text"])

        next_token = r.get("NextToken")
        if not next_token:
            break

    return "\n".join(lines).strip()


def _write_output(text: str, source_key: str) -> str:
    normalized_key = source_key.replace("\\", "/")
    out_key = f"{OUTPUT_PREFIX}{normalized_key}.txt"

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=out_key,
        Body=text.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
        Metadata={"generated_at": _now_iso(), "source_key": normalized_key},
    )
    return out_key


def _extract_s3_info_from_sqs_record(record: dict) -> tuple[str, str]:
    body = json.loads(record["body"])
    s3_event = body["Records"][0]
    src_bucket = s3_event["s3"]["bucket"]["name"]
    src_key = urllib.parse.unquote_plus(s3_event["s3"]["object"]["key"])
    return src_bucket, src_key


def lambda_handler(event, context):
    records = event.get("Records", [])
    processed = 0

    for record in records:
        src_bucket, src_key = _extract_s3_info_from_sqs_record(record)
        ext = _get_ext(src_key)

        print(f"[INFO] Processing s3://{src_bucket}/{src_key} ext={ext}")

        if ext in TEXT_EXTS:
            text = _read_txt_from_s3(src_bucket, src_key)
            method = "S3_READ_TEXT"
        elif ext in IMAGE_EXTS:
            text = _textract_sync_image(src_bucket, src_key)
            method = "TEXTRACT_SYNC_IMAGE"
        elif ext in PDF_EXTS:
            text = _textract_async_pdf(src_bucket, src_key)
            method = "TEXTRACT_ASYNC_PDF"
        else:
            raise ValueError(f"Unsupported file extension: {ext} (key={src_key})")

        out_key = _write_output(text, src_key)
        print(f"[OK] method={method} wrote s3://{OUTPUT_BUCKET}/{out_key}")
        processed += 1

    return {"processed": processed}
