import re
import random
from typing import Dict, List, Optional, Pattern
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Intent:
    name: str
    patterns: List[Pattern]
    responses: List[str]
    context_setter: Optional[str] = None


class ConversationalBot:
    """
    Advanced rule-based chatbot featuring regex boundary matching,
    intent classification, session history, and contextual fallback handling.
    """

    def __init__(self, bot_name: str = "CodeAlpha Assistant"):
        self.bot_name = bot_name
        self.conversation_history: List[Dict[str, str]] = []
        self.current_context: Optional[str] = None
        self.intents: List[Intent] = self._compile_intents()

    def _compile_intents(self) -> List[Intent]:
        """Compiles raw regex patterns using word boundaries (\b) to avoid false positives."""
        raw_intent_data = [
            {
                "name": "greeting",
                "patterns": [
                    r"\b(hi|hello|hey|greetings|howdy)\b",
                    r"\bgood\s+(morning|afternoon|evening)\b",
                ],
                "responses": [
                    f"Greetings! I'm {self.bot_name}. How may I assist you today?",
                    "Hello! What can I help you explore or resolve today?",
                    "Hi there! How can I make your day easier?",
                ],
            },
            {
                "name": "status_inquiry",
                "patterns": [
                    r"\bhow\s+are\s+you\b",
                    r"\bhow('s|\s+is)\s+it\s+going\b",
                    r"\bare\s+you\s+well\b",
                ],
                "responses": [
                    "Operating at peak efficiency! Thank you for asking. How are you doing?",
                    "All systems are running smoothly. What's on your mind?",
                ],
            },
            {
                "name": "identity",
                "patterns": [
                    r"\bwho\s+are\s+you\b",
                    r"\bwhat('s|\s+is)\s+your\s+name\b",
                    r"\btell\s+me\s+about\s+yourself\b",
                ],
                "responses": [
                    f"I am {self.bot_name}, a rule-based AI built in Python.",
                    f"My name is {self.bot_name}. I process your questions using pattern matching and structured rules.",
                ],
            },
            {
                "name": "capabilities",
                "patterns": [
                    r"\bwhat\s+can\s+you\s+do\b",
                    r"\b(help|support|features)\b",
                    r"\bhow\s+do\s+you\s+work\b",
                ],
                "responses": [
                    "I can discuss my architecture, check the current system time, chat about general topics, or answer basic queries.",
                    "My core capabilities include pattern detection, rule execution, and session logging. Feel free to ask what I can do!",
                ],
            },
            {
                "name": "time_inquiry",
                "patterns": [
                    r"\b(current\s+)?time\b",
                    r"\bwhat\s+time\s+is\s+it\b",
                    r"\bwhat\s+is\s+today'?s\s+date\b",
                ],
                "responses": [
                    "TIME_HOOK"  # Flag for dynamic evaluation
                ],
            },
            {
                "name": "farewell",
                "patterns": [
                    r"\b(bye|goodbye|see\s+you|exit|quit|later)\b",
                    r"\bhave\s+a\s+good\s+day\b",
                ],
                "responses": [
                    "Goodbye! Do not hesitate to reach out if you have more questions.",
                    "Have a productive day ahead! Terminating session.",
                    "Farewell! Take care.",
                ],
            },
        ]

        compiled_intents = []
        for item in raw_intent_data:
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in item["patterns"]]
            compiled_intents.append(
                Intent(
                    name=item["name"],
                    patterns=compiled_patterns,
                    responses=item["responses"],
                )
            )
        return compiled_intents

    def normalize_input(self, text: str) -> str:
        """Strips excess whitespace, punctuation anomalies, and normalizes casing."""
        cleaned = re.sub(r"[^\w\s\']", " ", text)
        return " ".join(cleaned.lower().split())

    def match_intent(self, text: str) -> Optional[Intent]:
        """Matches normalized input against regex patterns."""
        for intent in self.intents:
            for pattern in intent.patterns:
                if pattern.search(text):
                    return intent
        return None

    def generate_response(self, user_input: str) -> tuple[str, bool]:
        """Processes input and returns (response_string, should_exit)."""
        normalized = self.normalize_input(user_input)

        if not normalized:
            return "You haven't typed anything. Feel free to ask a question.", False

        intent = self.match_intent(normalized)

        if not intent:
            fallbacks = [
                "I couldn't quite map that to a recognized intent. Could you rephrase your question?",
                "That falls outside my current rule boundaries. Try asking about my capabilities or features.",
                "I'm not sure how to respond to that yet. Ask 'what can you do' to see available commands.",
            ]
            reply = random.choice(fallbacks)
            self._log_exchange(user_input, reply)
            return reply, False

        if intent.name == "farewell":
            reply = random.choice(intent.responses)
            self._log_exchange(user_input, reply)
            return reply, True

        # Dynamic parameter handling
        if "TIME_HOOK" in intent.responses:
            now = datetime.now()
            reply = f"The current system time is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        else:
            reply = random.choice(intent.responses)

        self._log_exchange(user_input, reply)
        return reply, False

    def _log_exchange(self, user_query: str, bot_response: str) -> None:
        """Maintains an audit trail of dialogue turns."""
        self.conversation_history.append(
            {"timestamp": datetime.now().isoformat(), "user": user_query, "bot": bot_response}
        )

    def start_session(self) -> None:
        """Starts the interactive CLI dialogue loop."""
        print("=" * 55)
        print(f" {self.bot_name} - Online")
        print(" Type 'help' for guidance or 'bye'/'exit' to finish.")
        print("=" * 55)

        while True:
            try:
                raw_input = input("\nYou: ").strip()
                if not raw_input:
                    continue

                bot_reply, should_terminate = self.generate_response(raw_input)
                print(f"{self.bot_name}: {bot_reply}")

                if should_terminate:
                    break

            except (KeyboardInterrupt, EOFError):
                print(f"\n{self.bot_name}: Session interrupted. Goodbye!")
                break


if __name__ == "__main__":
    bot = ConversationalBot()
    bot.start_session()