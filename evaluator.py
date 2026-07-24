from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field, field_validator
from models import JSONResume, EvaluationData
from llm_utils import initialize_llm_provider, extract_json_from_response
import logging
import json
import re
import time

MAX_BONUS_POINTS = 20
MIN_FINAL_SCORE = -20
MAX_FINAL_SCORE = 120

from prompt import (
    DEFAULT_MODEL,
    MODEL_PARAMETERS,
    MODEL_PROVIDER_MAPPING,
    GEMINI_API_KEY,
)
from prompts.template_manager import TemplateManager
from config import settings

logger = logging.getLogger(__name__)


class ResumeEvaluator:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        model_params: dict = None,
        position_type: str = None,
        live_demo_data: str = None,
    ):
        if not model_name:
            raise ValueError("Model name cannot be empty")

        self.model_name = model_name
        self.model_params = model_params or MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.5, "top_p": 0.9}
        )
        self.position_type = position_type
        self.live_demo_data = live_demo_data
        self.template_manager = TemplateManager()
        self._initialize_llm_provider()

    def _initialize_llm_provider(self):
        self.provider = initialize_llm_provider(self.model_name)

    def _record_langfuse_trace(self, prompt: str, response_text: str, duration_ms: float) -> Optional[str]:
        host = settings.get("LANGFUSE_HOST")
        pk = settings.get("LANGFUSE_PUBLIC_KEY")
        sk = settings.get("LANGFUSE_SECRET_KEY")
        if not all([host, pk, sk]):
            return None
        try:
            from langfuse import Langfuse
            lf = Langfuse(host=host, public_key=pk, secret_key=sk)
            trace = lf.trace(
                name="resume_evaluation",
                input=prompt[:2000],
                output=response_text[:2000],
                metadata={
                    "model": self.model_name,
                    "duration_ms": duration_ms,
                    "position_type": self.position_type,
                },
            )
            return trace.id
        except Exception as e:
            logger.warning(f"LangFuse trace failed: {e}")
            return None

    def _load_evaluation_prompt(self, resume_text: str) -> str:
        criteria_template = self.template_manager.render_template(
            "resume_evaluation_criteria",
            text_content=resume_text,
            position_type=self.position_type,
            live_demo_data=self.live_demo_data,
        )
        if criteria_template is None:
            raise ValueError("Failed to load resume evaluation criteria template")
        return criteria_template

    def evaluate_resume(self, resume_text: str) -> EvaluationData:
        self._last_resume_text = resume_text
        full_prompt = self._load_evaluation_prompt(resume_text)
        # logger.info(f"🔤 Evaluation prompt being sent: {full_prompt}")
        try:
            system_message = self.template_manager.render_template(
                "resume_evaluation_system_message"
            )
            if system_message is None:
                raise ValueError(
                    "Failed to load resume evaluation system message template"
                )

            # Prepare chat parameters
            chat_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": full_prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": self.model_params.get("temperature", 0.5),
                    "top_p": self.model_params.get("top_p", 0.9),
                },
            }

            # Add format parameter for structured output
            kwargs = {"format": EvaluationData.model_json_schema()}
            # Use the appropriate provider to make the API call
            chat_start = time.time()
            response = self.provider.chat(**chat_params, **kwargs)
            duration_ms = (time.time() - chat_start) * 1000

            response_text = response["message"]["content"]
            response_text = extract_json_from_response(response_text)
            logger.error(f"🔤 Prompt response: {response_text}")

            evaluation_dict = json.loads(response_text)
            evaluation_data = EvaluationData(**evaluation_dict)

            self._record_langfuse_trace(full_prompt, response_text, duration_ms)

            return evaluation_data

        except Exception as e:
            logger.error(f"Error evaluating resume: {str(e)}")
            raise
