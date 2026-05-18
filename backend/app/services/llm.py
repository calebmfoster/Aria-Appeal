import json
import os
import uuid
import re
from typing import List, Optional
from app.schemas.script import ScriptSentence
from app.core.system_config import config_manager

SYSTEM_PROMPT_TEMPLATE = """You are an expert copywriter for non-profit organizations, specializing in donor-centric storytelling.
Your goal is to write a compelling audio advertisement script.

### CAMPAIGN BRIEF:
- **Organization**: {organization_name}
- **Core Cause**: {cause}
- **Target Audience**: {target_audience}
- **Script Length**: {script_length_label} (approximately {word_target} words)
- **Tone / Messaging**: {messaging_strategy}
{story_hook_line}
{ask_line}

### FRAMEWORK:
Use the Problem-Agitation-Solution (PAS) structure:
1. **Problem**: State a clear, relatable problem tied to the cause.
2. **Agitation**: Make it visceral — describe what it *looks*, *sounds*, or *feels* like. If a story hook is provided, anchor the agitation to that specific detail.
3. **Solution**: Present the donation as the resolution. If an ask amount is provided, write a specific CTA ("Your $50 today...").

### FORMATTING INSTRUCTIONS:
- Output EXCLUSIVELY a JSON array of sentence objects.
- Each object has three fields:
  - "text" (string): the spoken sentence
  - "duration_estimate" (float, seconds): estimated read time
  - "emotion" (string): a short TTS delivery direction for this specific sentence (e.g. "speak softly with quiet dread", "speak with rising urgency", "speak warmly and with conviction"). Tailor each direction to the sentence's moment in the PAS arc.
- Target exactly {word_target} total words across all sentences.
- STRICTLY RETURN ONLY THE JSON ARRAY. NO MARKDOWN. NO EXPLANATIONS.

### OUTPUT FORMAT:
[
  {{"text": "Imagine the silence of an empty playfield.", "duration_estimate": 2.5, "emotion": "speak softly, with quiet dread"}},
  {{"text": "No laughter, just the rustle of wind through broken fences.", "duration_estimate": 3.0, "emotion": "speak with low intensity and sorrow"}}
]
"""

_WORD_TARGETS = {"30s": "70-80", "60s": "140-155", "90s": "210-230"}
_LENGTH_LABELS = {"30s": "30 seconds", "60s": "60 seconds", "90s": "90 seconds"}


def _build_prompt_content(
    target_audience: str,
    cause: str,
    primary_emotion: str,
    organization_name: Optional[str],
    story_hook: Optional[str],
    script_length: str,
    messaging_strategy: Optional[str],
    ask_amount: Optional[str],
) -> str:
    org_name = organization_name or "our organization"
    tone = messaging_strategy or primary_emotion
    story_hook_line = f"- **Story Hook**: {story_hook}" if story_hook else ""
    ask_line = f"- **Donation Ask**: {ask_amount}" if ask_amount else ""
    return SYSTEM_PROMPT_TEMPLATE.format(
        organization_name=org_name,
        cause=cause,
        target_audience=target_audience,
        script_length_label=_LENGTH_LABELS.get(script_length, "30 seconds"),
        word_target=_WORD_TARGETS.get(script_length, "70-80"),
        messaging_strategy=tone,
        story_hook_line=story_hook_line,
        ask_line=ask_line,
    )


def _parse_sentences(content: str) -> List[ScriptSentence]:
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]

    json_match = re.search(r'\[.*\]', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)

    data = json.loads(content)

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                data = value
                break
        else:
            raise ValueError("Could not find a list in the JSON response.")

    sentences = []
    for item in data:
        sentences.append(
            ScriptSentence(
                id=uuid.uuid4(),
                text=item.get("text", ""),
                duration_estimate=item.get("duration_estimate", 3.0),
                emotion=item.get("emotion") or None,
            )
        )
    return sentences


def _generate_with_claude(system_content: str, settings) -> List[ScriptSentence]:
    import anthropic

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "Anthropic API key is not configured. Set it in the launcher Settings panel "
            "or via the ANTHROPIC_API_KEY environment variable."
        )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        system=system_content,
        messages=[{"role": "user", "content": "Generate the script now."}],
    )
    content = response.content[0].text
    print(f"DEBUG: Claude API response: {content[:200]}...")
    return _parse_sentences(content)


class LLMService:
    _pipeline = None

    @classmethod
    def _get_pipeline(cls):
        if cls._pipeline is None:
            import torch
            from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

            if not torch.cuda.is_available():
                raise RuntimeError(
                    "CUDA is required for local LLM inference. "
                    "No CUDA device detected — switch to Claude API in the launcher Settings."
                )

            model_id = config_manager.get_settings().llm_model_id
            print(f"Loading {model_id} in NF4 4-bit for copywriting... (this may take a moment on first load)")

            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )

            tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto",
                quantization_config=quantization_config,
                trust_remote_code=True,
            )
            cls._pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
            )
            print(f"LLM ready: {model_id}")
        return cls._pipeline

    @staticmethod
    def generate_script(
        target_audience: str,
        cause: str,
        primary_emotion: str,
        organization_name: Optional[str] = None,
        story_hook: Optional[str] = None,
        script_length: str = "30s",
        messaging_strategy: Optional[str] = None,
        ask_amount: Optional[str] = None,
    ) -> List[ScriptSentence]:
        settings = config_manager.get_settings()
        system_content = _build_prompt_content(
            target_audience=target_audience,
            cause=cause,
            primary_emotion=primary_emotion,
            organization_name=organization_name,
            story_hook=story_hook,
            script_length=script_length,
            messaging_strategy=messaging_strategy,
            ask_amount=ask_amount,
        )

        if settings.llm_provider == "claude":
            return _generate_with_claude(system_content, settings)

        # Local HuggingFace path
        generator = LLMService._get_pipeline()
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "Generate the script now."},
        ]

        try:
            prompt = generator.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            outputs = generator(
                prompt,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True,
            )
            content = outputs[0]["generated_text"].split("<|im_start|>assistant\n")[-1].strip()
            print(f"DEBUG: Raw LLM response: {content}")
            return _parse_sentences(content)

        except json.JSONDecodeError as e:
            print(f"Error logging: Failed to decode JSON from LLM: {e}")
            raise ValueError("Local LLM did not return valid JSON.")
        except Exception as e:
            print(f"Error generating script locally: {e}")
            raise e
