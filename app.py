import os
import uuid
import threading
from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    send_file,
    after_this_request,
)
from werkzeug.utils import secure_filename
from transliterator import CSVTransliterator

# ─── Config ───────────────────────────────────────────────────────────────────
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB limit

# ─── Global state (simple in-memory progress tracker) ─────────────────────────
jobs: dict[str, dict] = {}  # job_id → {status, progress, total, output_path, error}

# ─── Lazy-load the engine once at startup ────────────────────────────────────
transliterator: CSVTransliterator | None = None
engine_lock = threading.Lock()


def get_transliterator() -> CSVTransliterator:
    global transliterator
    if transliterator is None:
        with engine_lock:
            if transliterator is None:
                transliterator = CSVTransliterator(beam_width=5)
    return transliterator


# ─── Helpers ──────────────────────────────────────────────────────────────────
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_transliteration(job_id: str, input_path: str, output_path: str, column: str):
    """Background worker for a single transliteration job."""

    def progress_callback(done: int, total: int):
        jobs[job_id]["progress"] = done
        jobs[job_id]["total"] = total

    try:
        jobs[job_id]["status"] = "running"
        engine = get_transliterator()
        engine.transliterate_csv(
            input_csv=input_path,
            output_csv=output_path,
            source_column=column,
            progress_callback=progress_callback,
        )
        jobs[job_id]["status"] = "done"
        jobs[job_id]["output_path"] = output_path
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
    finally:
        # Clean up the uploaded input file
        if os.path.exists(input_path):
            os.remove(input_path)


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    """Accept CSV + column name, kick off background job, return job_id."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    column = request.form.get("column", "").strip()

    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed."}), 400

    if not column:
        return jsonify({"error": "Column name is required."}), 400

    job_id = uuid.uuid4().hex
    safe_name = secure_filename(file.filename)
    input_path = os.path.join(UPLOAD_FOLDER, f"{job_id}_{safe_name}")
    output_path = os.path.join(OUTPUT_FOLDER, f"{job_id}_hindi_{safe_name}")

    file.save(input_path)

    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "total": 0,
        "output_path": None,
        "error": None,
    }

    thread = threading.Thread(
        target=run_transliteration,
        args=(job_id, input_path, output_path, column),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id}), 202


@app.route("/status/<job_id>")
def status(job_id: str):
    """Poll job status + progress."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    return jsonify(
        {
            "status": job["status"],
            "progress": job["progress"],
            "total": job["total"],
            "error": job["error"],
        }
    )


@app.route("/download/<job_id>")
def download(job_id: str):
    """Stream the finished CSV to the browser and clean up."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found."}), 404
    if job["status"] != "done":
        return jsonify({"error": "Job not finished yet."}), 400

    output_path = job["output_path"]
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Output file missing."}), 500

    @after_this_request
    def cleanup(response):
        try:
            os.remove(output_path)
            del jobs[job_id]
        except Exception:
            pass
        return response

    return send_file(
        output_path,
        as_attachment=True,
        download_name="hindi_transliteration.csv",
        mimetype="text/csv",
    )


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
