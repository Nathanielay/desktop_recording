import json
import os
from typing import Dict, Any, Optional


class LlmService:
    def __init__(self) -> None:
        self._base_url = os.environ.get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self._api_key = os.environ.get("ARK_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
        self._model = os.environ.get("LLM_MODEL", "doubao-seed-1-6-lite-251015")
        self._timeout = float(os.environ.get("LLM_TIMEOUT", "60"))
        self._reasoning_effort = os.environ.get("LLM_REASONING_EFFORT", "")
        self._client = self._init_client()

    def _init_client(self) -> Optional["OpenAI"]:
        try:
            from openai import OpenAI
        except Exception:
            return None
        return OpenAI(base_url=self._base_url, api_key=self._api_key, timeout=self._timeout)

    def enrich(self, text: str, entry_type: str) -> Dict[str, Any]:
        if not self._api_key:
            fallback = self._apply_defaults({}, entry_type)
            fallback["raw_llm"] = ""
            return fallback

        if entry_type == "word":
            schema = (
                "translation, part_of_speech, ipa, phonetic_us, phonetic_uk, "
                "word_roots (array), tense_form (array), common_meanings (array), "
                "related_terms (array), definition"
            )
        else:
            schema = (
                "translation, structure_breakdown (array of {span, role}), "
                "grammar_notes, key_terms (array of {term, definition})"
            )
        prompt = (
            "You are a bilingual dictionary assistant. "
            "Return valid JSON only. "
            "The 'translation' field must include part-of-speech grouped Chinese meanings. "
            "Format must be multi-line: "
            "v. ...\\n"
            "n. ...\\n"
            "adj. ... "
            "Include only the POS that apply. "
            "The 'ipa' field must be formatted as: "
            "'UK: /.../; US: /.../' if IPA is available. "
            "The 'tense_form' field must be an array of Chinese-labeled forms, e.g. "
            "['复数: ...', '第三人称单数: ...', '现在分词: ...', '过去式: ...', '过去分词: ...']. "
            f"Return JSON with keys: {schema}. "
            f"Entry type: {entry_type}. Text: {text}"
        )
        if not self._client:
            fallback = self._apply_defaults({}, entry_type)
            fallback["raw_llm"] = "error: openai sdk not installed"
            return fallback

        return self._enrich_via_sdk(prompt, entry_type)

    def _enrich_via_sdk(self, prompt: str, entry_type: str) -> Dict[str, Any]:
        try:
            payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}],
                    }
                ],
                "temperature": 0.2,
            }
            if self._reasoning_effort:
                payload["reasoning_effort"] = self._reasoning_effort
            completion = self._client.chat.completions.create(**payload)
            content = completion.choices[0].message.content or ""
            parsed = json.loads(content)
            parsed = self._apply_defaults(parsed, entry_type)
            parsed["raw_llm"] = content
            return parsed
        except Exception as exc:
            fallback = self._apply_defaults({}, entry_type)
            fallback["raw_llm"] = f"error: {exc}"
            return fallback

    def _apply_defaults(self, data: Dict[str, Any], entry_type: str) -> Dict[str, Any]:
        if entry_type == "word":
            return {
                "translation": data.get("translation", ""),
                "part_of_speech": data.get("part_of_speech", ""),
                "ipa": data.get("ipa", ""),
                "phonetic_us": data.get("phonetic_us", ""),
                "phonetic_uk": data.get("phonetic_uk", ""),
                "word_roots": data.get("word_roots", []),
                "tense_form": data.get("tense_form", ""),
                "common_meanings": data.get("common_meanings", []),
                "related_terms": data.get("related_terms", []),
                "definition": data.get("definition", ""),
            }
        return {
            "translation": data.get("translation", ""),
            "structure_breakdown": data.get("structure_breakdown", []),
            "grammar_notes": data.get("grammar_notes", ""),
            "key_terms": data.get("key_terms", []),
        }
