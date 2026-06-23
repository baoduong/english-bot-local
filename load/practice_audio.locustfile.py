"""Locust load test for /practice/audio endpoint.

Run with mocked engines: EB_MOCK_WHISPER=1 EB_MOCK_OLLAMA=1 EB_MOCK_AZURE=1
Target: P95 < 2000ms for 10 concurrent users over 5 minutes.
"""
import os
import random
import string

from locust import HttpUser, task, between, events

AUDIO_FIXTURE = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "audio", "fix_correct.wav")


class PracticeUser(HttpUser):
    wait_time = between(1, 3)
    host = os.getenv("LOCUST_HOST", "http://localhost:8765")

    def on_start(self):
        """Seed a user with an active practice session."""
        self.user_id = f"loadtest-{''.join(random.choices(string.ascii_lowercase, k=8))}"
        # Start onboarding + confirm (minimal flow to get a session)
        self.client.post("/onboarding/start", json={"user_id": self.user_id, "resume_if_exists": False})
        # Skip full onboarding — directly start practice if possible
        self.client.post("/practice/session/start", json={"user_id": self.user_id, "resume_if_exists": False})

    @task(10)
    def score_audio(self):
        """Main task: submit audio for scoring."""
        with open(AUDIO_FIXTURE, "rb") as f:
            self.client.post(
                "/practice/audio",
                data={"user_id": self.user_id},
                files={"audio_file": ("audio.wav", f, "audio/wav")},
                name="/practice/audio",
            )

    @task(2)
    def poll_coaching(self):
        """Poll for pending coaching."""
        self.client.get(
            f"/practice/coaching/pending?user_id={self.user_id}",
            name="/practice/coaching/pending",
        )

    @task(1)
    def get_state(self):
        """Check session state."""
        self.client.get(
            f"/practice/session/state?user_id={self.user_id}",
            name="/practice/session/state",
        )


@events.quitting.add_listener
def check_p95(environment, **kwargs):
    """Fail if P95 for /practice/audio exceeds 2000ms."""
    stats = environment.runner.stats
    audio_stats = stats.get("/practice/audio", "POST")
    if audio_stats and audio_stats.get_response_time_percentile(0.95) > 2000:
        environment.process_exit_code = 1
        print(f"❌ LOAD TEST FAILED: /practice/audio P95 = {audio_stats.get_response_time_percentile(0.95):.0f}ms > 2000ms")
    else:
        p95 = audio_stats.get_response_time_percentile(0.95) if audio_stats else 0
        print(f"✅ LOAD TEST PASSED: /practice/audio P95 = {p95:.0f}ms < 2000ms")
