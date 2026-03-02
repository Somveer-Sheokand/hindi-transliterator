import os
import uuid
import threading
import logging
import traceback
from flask import (
    Flask, request, render_template, jsonify, send_file, after_this_request,
)
from werkzeug.utils import secure_filename

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# ─── Global state ─────────────────────────────────────────────────────────────
jobs = {}
_transliterator = None
_engine_lock = threading.Lock()


def get_transliterator():
    global _transliterator
    if _transliterator is None:
        with _engine_lock:
            if _transliterator is None:
                log.info("Loading AI4Bharat XlitEngine (first request)…")
                from transliterator import CSVTransliterator
                _transliterator = CSVTransliterator(beam_width=5)
                log.info("XlitEngine ready.")
    return _transliterator


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_job(job_id, input_path, output_path, column):
    def on_progress(done, total):
        jobs[job_id]["progress"] = done
        jobs[job_id]["total"] = total

    try:
        log.info("[%s] Job started — column=%r", job_id, column)
        jobs[job_id]["status"] = "running"
        engine = get_transliterator()
        engine.transliterate_csv(
            input_csv=input_path,
            output_csv=output_path,
            source_column=column,
            progress_callback=on_progress,
        )
        jobs[job_id]["status"] = "done"
        jobs[job_id]["output_path"] = output_path
        log.info("[%s] Job done.", job_id)
    except Exception as exc:
        log.error("[%s] Job failed:\n%s", job_id, traceback.format_exc())
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)


# ─── Global error handlers ────────────────────────────────────────────────────
@app.errorhandler(Exception)
def handle_any(e):
    log.error("Unhandled exception:\n%s", traceback.format_exc())
    return jsonify({"error": str(e)}), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File exceeds 50 MB limit."}), 413


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in request."}), 400

        file = request.files["file"]
        column = request.form.get("column", "").strip()

        if not file or not file.filename:
            return jsonify({"error": "No file selected."}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Only .csv files are accepted."}), 400

        if not column:
            return jsonify({"error": "Column name is required."}), 400

        job_id = uuid.uuid4().hex
        safe = secure_filename(file.filename)
        input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe}")
        output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}_hindi_{safe}")

        file.save(input_path)
        log.info("[%s] Saved upload → %s", job_id, input_path)

        jobs[job_id] = {
            "status": "queued",
            "progress": 0,
            "total": 0,
            "output_path": None,
            "error": None,
        }

        t = threading.Thread(
            target=run_job,
            args=(job_id, input_path, output_path, column),
            daemon=True,
        )
        t.start()

        return jsonify({"job_id": job_id}), 202

    except Exception as exc:
        log.error("Upload error:\n%s", traceback.format_exc())
        return jsonify({"error": str(exc)}), 500


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify({
        "status":   job["status"],
        "progress": job["progress"],
        "total":    job["total"],
        "error":    job["error"],
    })


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    if job["status"] != "done":
        return jsonify({"error": "Job not finished yet."}), 400

    output_path = job.get("output_path")
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Output file missing."}), 500

    @after_this_request
    def cleanup(response):
        try:
            os.remove(output_path)
            jobs.pop(job_id, None)
        except Exception:
            pass
        return response

    return send_file(
        output_path,
        as_attachment=True,
        download_name="hindi_transliteration.csv",
        mimetype="text/csv",
    )


# ─── Dev server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Starting Hindi Transliterator on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
