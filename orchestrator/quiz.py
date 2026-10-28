"""End-of-lesson quiz generation and schema.

Contract safe: does not alter LessonPlan schema.
Generates 3 grounded questions from lesson content.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from pydantic import BaseModel, Field

from orchestrator.schema import LessonPlan

logger = logging.getLogger(__name__)


class Question(BaseModel):
    question: str
    options: list[str] = Field(..., min_length=3, max_length=3)
    answer: int = Field(..., ge=0, le=2)
    explanation: str


class Quiz(BaseModel):
    questions: list[Question] = Field(..., min_length=3, max_length=3)


QUIZ_SYSTEM = (
    "You are an expert educator creating a 3-question multiple-choice quiz based ONLY on the provided lesson plan. "
    "Every question must be strictly answerable from the lesson narration and visual steps. "
    "Do not invent external facts. Each question must have exactly 3 plausible options, with answer as index 0, 1, or 2, "
    "and a concise 1-sentence explanation."
)


def generate_quiz(lesson_plan: LessonPlan, lang: str = "en") -> Quiz:
    """Generate a 3-question quiz for a lesson plan, translated if non-English."""
    lesson_text = f"Title: {lesson_plan.title}\n"
    for i, s in enumerate(lesson_plan.scenes, 1):
        lesson_text += f"Scene {i}: {s.narration}\n"
        if s.visual and s.visual.params:
            if s.visual.params.steps:
                lesson_text += f"Steps: {'; '.join(s.visual.params.steps)}\n"
            if s.visual.params.labels:
                lesson_text += f"Labels: {'; '.join(s.visual.params.labels)}\n"

    model = os.environ.get("PLANNER_MODEL") or "qwen2.5:3b"
    quiz = None
    try:
        import ollama
        resp = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": QUIZ_SYSTEM},
                {"role": "user", "content": f"Generate a 3-question quiz for this lesson:\n\n{lesson_text}"},
            ],
            format=Quiz.model_json_schema(),
            keep_alive=-1,
            options={"temperature": 0.2, "num_predict": 600},
        )
        content = resp.message.content or "{}"
        quiz = Quiz.model_validate_json(content)
    except Exception as exc:
        logger.warning(f"Ollama quiz generation fallback: {exc}")
        quiz = _fallback_quiz(lesson_plan)

    if lang != "en" and quiz:
        try:
            quiz = _translate_quiz(quiz, lang)
        except Exception as exc:
            logger.warning(f"Quiz translation failed for {lang}: {exc}")

    return quiz or _fallback_quiz(lesson_plan)


def _fallback_quiz(plan: LessonPlan) -> Quiz:
    questions = []
    scenes = plan.scenes[:3] if len(plan.scenes) >= 3 else plan.scenes
    for i, s in enumerate(scenes):
        labels = s.visual.params.labels if (s.visual and s.visual.params and s.visual.params.labels) else []
        main_term = labels[0] if labels else f"Key concept {i + 1}"
        questions.append(
            Question(
                question=f"What is the key focus in part {i + 1} of {plan.title}?",
                options=[
                    main_term,
                    f"Secondary aspect {i + 1}",
                    f"Opposite dynamic {i + 1}",
                ],
                answer=0,
                explanation=s.narration[:120] if s.narration else f"Explained in scene {i + 1}.",
            )
        )
    while len(questions) < 3:
        questions.append(
            Question(
                question=f"Which core principle governs {plan.title}?",
                options=[plan.title, "Unrelated phenomenon", "Random fluctuation"],
                answer=0,
                explanation=f"Based on the core topic {plan.title}.",
            )
        )
    return Quiz(questions=questions[:3])


def _translate_quiz(quiz: Quiz, lang: str) -> Quiz:
    try:
        from localization.translator import OfflineIndicTranslator
        translator = OfflineIndicTranslator()
    except Exception:
        return quiz

    texts_to_trans = []
    for q in quiz.questions:
        texts_to_trans.append(q.question)
        texts_to_trans.extend(q.options)
        texts_to_trans.append(q.explanation)

    translated = translator.translate_texts(texts_to_trans, lang)
    idx = 0
    new_questions = []
    for q in quiz.questions:
        t_q = translated[idx]
        t_opts = translated[idx + 1 : idx + 4]
        t_exp = translated[idx + 4]
        idx += 5
        new_questions.append(
            Question(
                question=t_q,
                options=t_opts,
                answer=q.answer,
                explanation=t_exp,
            )
        )
    return Quiz(questions=new_questions)
