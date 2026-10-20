"""post-freeze, real data: local checks; no Groq calls."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import label


class BlindLabelChecks(unittest.TestCase):
    def test_only_question_and_raw_evidence_are_sent(self):
        question = json.loads((label.HERE / "questions.jsonl").read_text().splitlines()[0])
        request = label.payload(question)
        self.assertEqual(len(request["messages"]), 1)
        content = json.loads(request["messages"][0]["content"])
        self.assertEqual(set(content), {"question", "evidence_files"})
        self.assertEqual(content["question"], question["question"])
        for path, text in content["evidence_files"].items():
            self.assertEqual(text, (label.ROOT / path).read_text())
        response = {"choices": [{"finish_reason": "stop", "message": {"content":
            json.dumps({"answer": "test", "short_reason": "test",
                        "evidence_paths": ["outside/raw"]})}}]}
        with self.assertRaises(ValueError):
            label.label(response, question)

    def test_429_stops_and_saves_partial(self):
        questions = (label.HERE / "questions.jsonl").read_text()
        with tempfile.TemporaryDirectory() as directory:
            here = Path(directory)
            (here / "questions.jsonl").write_text(questions)
            with patch.object(label, "HERE", here), \
                 patch.dict(label.os.environ, {"GROQ_API_KEY": "mock-only"}, clear=True), \
                 patch("sys.argv", ["label.py"]), \
                 patch.object(label.urllib.request, "urlopen", side_effect=
                              HTTPError("mock", 429, "rate limit", {}, None)) as call, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(label.main(), 1)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(json.loads((here / "usage.json").read_text())["status"],
                             "rate_limited_429")
            self.assertEqual(len((here / "gold_blind.jsonl").read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
