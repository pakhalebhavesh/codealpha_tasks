from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Final, Sequence


# =====================================================================
# Domain Constants & Visuals
# =====================================================================

class GameState(Enum):
    IN_PROGRESS = auto()
    WON = auto()
    LOST = auto()


class TerminalColor:
    """ANSI color escape sequences for enhanced CLI readability."""
    RESET: Final[str] = "\033[0m"
    BOLD: Final[str] = "\033[1m"
    GREEN: Final[str] = "\033[92m"
    RED: Final[str] = "\033[91m"
    YELLOW: Final[str] = "\033[93m"
    CYAN: Final[str] = "\033[96m"


HANGMAN_STAGES: Final[tuple[str, ...]] = (
    """
       +---+
       |   |
           |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
           |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
       |   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|   |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
           |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      /    |
           |
    =========
    """,
    """
       +---+
       |   |
       O   |
      /|\\  |
      / \\  |
           |
    =========
    """,
)


# =====================================================================
# Custom Exceptions
# =====================================================================

class HangmanException(Exception):
    """Base domain exception."""


class InvalidInputError(HangmanException):
    """Raised when input fails sanitization (non-alphabetic or multi-char)."""


class DuplicateGuessError(HangmanException):
    """Raised when user repeats an already guessed letter."""


# =====================================================================
# Core Game Engine
# =====================================================================

@dataclass
class HangmanSession:
    """Encapsulates the state and business logic of a Hangman session."""
    target_word: str
    max_mistakes: int = 6
    guesses: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.target_word = self.target_word.lower().strip()
        self._target_charset: set[str] = set(self.target_word)

    @property
    def mistakes(self) -> int:
        """Calculate count of incorrect guesses dynamically."""
        return len(self.guesses - self._target_charset)

    @property
    def remaining_attempts(self) -> int:
        return max(0, self.max_mistakes - self.mistakes)

    @property
    def masked_word(self) -> str:
        """Returns the revealed and masked letters (e.g., 'p y _ h o n')."""
        return " ".join(char if char in self.guesses else "_" for char in self.target_word)

    @property
    def state(self) -> GameState:
        if self._target_charset.issubset(self.guesses):
            return GameState.WON
        if self.mistakes >= self.max_mistakes:
            return GameState.LOST
        return GameState.IN_PROGRESS

    def register_guess(self, raw_input: str) -> bool:
        """
        Validates and registers a player's guess.
        Returns True if guess was correct, False otherwise.
        """
        sanitized = raw_input.strip().lower()

        if len(sanitized) != 1 or not sanitized.isalpha():
            raise InvalidInputError("Please provide a single valid alphabetical character.")
        if sanitized in self.guesses:
            raise DuplicateGuessError(f"Letter '{sanitized}' has already been evaluated.")

        self.guesses.add(sanitized)
        return sanitized in self._target_charset


# =====================================================================
# CLI Presentation Layer
# =====================================================================

class HangmanCLI:
    """Manages CLI rendering, user interaction, and lifecycle orchestration."""

    DEFAULT_WORD_BANK: Final[Sequence[str]] = (
        "python", "intern", "github", "source", "script",
        "concurrency", "asynchronous", "polymorphism"
    )

    def __init__(self, word_bank: Sequence[str] | None = None) -> None:
        self._word_bank = word_bank or self.DEFAULT_WORD_BANK

    def _render_dashboard(self, session: HangmanSession) -> None:
        """Renders ASCII state and current guessing status to stdout."""
        gallows = HANGMAN_STAGES[session.mistakes]
        wrong_guesses = sorted(list(session.guesses - set(session.target_word)))
        
        print(f"{TerminalColor.YELLOW}{gallows}{TerminalColor.RESET}")
        print(f"{TerminalColor.BOLD}Word: {TerminalColor.CYAN}{session.masked_word}{TerminalColor.RESET}")
        print(f"Attempts Left: {TerminalColor.RED}{session.remaining_attempts}{TerminalColor.RESET} / {session.max_mistakes}")
        print(f"Wrong Guesses: {', '.join(wrong_guesses) if wrong_guesses else 'None'}\n")

    def run(self) -> None:
        selected_word = random.choice(self._word_bank)
        session = HangmanSession(target_word=selected_word)

        print(f"\n{TerminalColor.BOLD}{TerminalColor.CYAN}=== CodeAlpha Enterprise Hangman ==={TerminalColor.RESET}\n")

        while session.state == GameState.IN_PROGRESS:
            self._render_dashboard(session)

            try:
                user_input = input(f"{TerminalColor.BOLD}Enter guess: {TerminalColor.RESET}")
                is_hit = session.register_guess(user_input)

                if is_hit:
                    print(f"{TerminalColor.GREEN}✓ Hit! Letter matched.{TerminalColor.RESET}")
                else:
                    print(f"{TerminalColor.RED}✗ Miss! Letter not in target.{TerminalColor.RESET}")

            except HangmanException as exc:
                print(f"{TerminalColor.YELLOW}[! Warning] {exc}{TerminalColor.RESET}")
            except (KeyboardInterrupt, EOFError):
                print(f"\n{TerminalColor.RED}Session terminated by user.{TerminalColor.RESET}")
                sys.exit(0)

        self._render_terminal_state(session)

    def _render_terminal_state(self, session: HangmanSession) -> None:
        print(f"\n{HANGMAN_STAGES[session.mistakes]}")
        if session.state == GameState.WON:
            print(f"{TerminalColor.GREEN}{TerminalColor.BOLD}★ VICTORY! Solved word: '{session.target_word}' ★{TerminalColor.RESET}\n")
        else:
            print(f"{TerminalColor.RED}{TerminalColor.BOLD}☠ DEFEAT! Target word was: '{session.target_word}' ☠{TerminalColor.RESET}\n")


if __name__ == "__main__":
    app = HangmanCLI()
    app.run()