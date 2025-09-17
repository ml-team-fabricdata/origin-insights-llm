import time
import botocore
import botocore.errorfactory as botocore_errorfactory
from langchain_core.messages import AIMessage, HumanMessage, trim_messages

from src.core.agent import get_agent
from src.core.supervisor import get_events_last_message
from src.tools.common_utils import count_tokens


MAX_HISTORY = 8
RESET_TEXT = {
    "es": "The connection has been restored. I don’t have the most recent messages available. Tell me how I can help, and we’ll resume immediately.",
    "en": "The connection has been restored. I don’t have the most recent messages available. Tell me how I can help, and we’ll resume immediately.",
}

TRIM_WARNING = {
    "es": "Tu mensaje se recortó por exceder el límite permitido.",
    "en": "Your message was trimmed for exceeding the allowed limit.",
}

ValidationException = getattr(botocore_errorfactory, "ValidationException", botocore.exceptions.ClientError)


class ChatService:
    SQL_MAX_RESULTS = 20
    VERBOSE = True

    def __init__(self, model_api: str = "bedrock"):
        self._agent = get_agent(model_api=model_api)
        self._history: list = []

    def clear(self) -> None:
        self._history = []

    def answer(self, user_input: str, language: str = "es") -> tuple[str, float, bool]:
        if len(self._history) >= MAX_HISTORY:
            self.clear()
            return RESET_TEXT.get(language, RESET_TEXT["es"]), 0, True

        start = time.time()
        self._history = trim_messages(
            messages=self._history,
            strategy="last",
            start_on="human",
            include_system=True,
            max_tokens=500,
            token_counter=count_tokens,
        )
        self._history.append(HumanMessage(user_input))
        self._history = self._history[-MAX_HISTORY:]
        try:
            last_message = get_events_last_message(
                self._agent,
                {"messages": self._history},
                verbose=self.VERBOSE,
            )
        except ValidationException:
            warning = TRIM_WARNING.get(language, TRIM_WARNING["es"])
            self._history = trim_messages(
                messages=self._history,
                strategy="last",
                start_on="human",
                include_system=True,
                max_tokens=500,
                token_counter=count_tokens,
            )
            self._history = self._history[-MAX_HISTORY:]
            try:
                last_message = get_events_last_message(
                    self._agent,
                    {"messages": self._history},
                    verbose=self.VERBOSE,
                )
            except ValidationException:
                self._history.append(AIMessage(warning))
                self._history = self._history[-MAX_HISTORY:]
                return warning, time.time() - start, False
        self._history.append(AIMessage(last_message))
        self._history = self._history[-MAX_HISTORY:]
        return last_message, time.time() - start, False

