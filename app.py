from flask import Flask, request, jsonify
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
import os
import tempfile

app = Flask(__name__)

mapping = {
    "ألف": "ا", "الف": "ا", "ألفا": "ا", "الفا": "ا",
    "باء": "ب", "با": "ب", "بي": "ب", "بيه": "ب",
    "تاء": "ت", "تا": "ت",
    "ثاء": "ث", "ثا": "ث",
    "جيم": "ج",
    "حاء": "ح", "حا": "ح",
    "خاء": "خ", "خا": "خ",
    "دال": "د", "دا": "د",
    "ذال": "ذ", "ذا": "ذ",
    "راء": "ر", "را": "ر",
    "زاي": "ز", "زي": "ز",
    "سين": "س", "سي": "س",
    "شين": "ش", "شي": "ش",
    "صاد": "ص", "صا": "ص",
    "ضاد": "ض", "ضا": "ض",
    "طاء": "ط", "طا": "ط",
    "ظاء": "ظ", "ظا": "ظ",
    "عين": "ع", "عا": "ع",
    "غين": "غ", "غا": "غ",
    "فاء": "ف", "فا": "ف",
    "قاف": "ق", "قا": "ق",
    "كاف": "ك", "كا": "ك",
    "لام": "ل", "لا": "ل",
    "ميم": "م", "ما": "م",
    "نون": "ن", "نا": "ن",
    "هاء": "ه", "ها": "ه",
    "واو": "و", "وا": "و",
    "ياء": "ي", "يا": "ي",
    "صفر": "0", "زيرو": "0",
    "واحد": "1",
    "اثنين": "2", "اتنين": "2",
    "ثلاثة": "3", "تلاتة": "3",
    "أربعة": "4", "اربعة": "4",
    "خمسة": "5",
    "ستة": "6",
    "سبعة": "7",
    "ثمانية": "8", "تمانية": "8",
    "تسعة": "9",
}


def convert_to_characters(text):
    words = text.split()
    output = []
    number_buffer = []

    for word in words:
        if word in mapping:
            value = mapping[word]

            if value.isdigit():
                number_buffer.append(value)
            else:
                if number_buffer:
                    output.append("".join(number_buffer))
                    number_buffer = []
                output.append(value)
        else:
            for char in word:
                val = mapping.get(char, char)
                if val.isdigit():
                    number_buffer.append(val)
                else:
                    if number_buffer:
                        output.append("".join(number_buffer))
                        number_buffer = []
                    output.append(val)

    if number_buffer:
        output.append("".join(number_buffer))

    return " ".join(output)


@app.route("/recognize", methods=["POST"])
def recognize():
    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "input_audio.ogg")
    audio_file.save(temp_path)

    try:
        sound = AudioSegment.from_file(temp_path)
        chunks = make_chunks(sound, 30000)
        recognizer = sr.Recognizer()

        full_text = ""
        total_confidence = 0
        valid_chunks = 0

        for i, chunk in enumerate(chunks):
            temp_wav = os.path.join(temp_dir, f"chunk_{i}.wav")
            chunk.export(temp_wav, format="wav")

            with sr.AudioFile(temp_wav) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)

                try:
                    result = recognizer.recognize_google(
                        audio_data, language="ar-EG", show_all=True
                    )

                    if result and "alternative" in result:
                        best_result = result["alternative"][0]
                        transcript = best_result["transcript"]
                        confidence = best_result.get("confidence", 0)

                        full_text += " " + transcript
                        total_confidence += confidence
                        valid_chunks += 1
                except Exception:
                    pass

            os.remove(temp_wav)

        os.remove(temp_path)
        os.rmdir(temp_dir)

        if valid_chunks > 0:
            accuracy = round((total_confidence / valid_chunks) * 100, 2)
            result_text = convert_to_characters(full_text.strip())
            return jsonify({
                "text": result_text,
                "raw": full_text.strip(),
                "accuracy": accuracy,
                "chunks_processed": valid_chunks,
            })
        else:
            return jsonify({"error": "No speech detected in audio"}), 422

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
        return jsonify({"error": str(e)}), 500


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "message": "Send POST to /recognize with audio file"})
