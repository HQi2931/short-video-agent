"""Strict boundaries for user input, model actions, trusted fixtures and tools."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class UserInput(StrictModel):
    topic: Text | None = None
    audience: Text | None = None
    platform: Text | None = None
    duration_seconds: float | None = Field(default=None, gt=0, le=3600)
    style: Text | None = None

    def missing_fields(self) -> list[str]:
        return [name for name in type(self).model_fields if getattr(self, name) is None]


class Fact(StrictModel):
    fact_id: Text
    text: Text


class Asset(StrictModel):
    asset_id: Text
    name: Text
    keywords: list[Text] = Field(min_length=1)
    facts: list[Fact] = Field(min_length=1)
    source_text: Text

    @model_validator(mode="after")
    def evidence_is_in_source(self):
        ids = [f.fact_id for f in self.facts]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate fact IDs within asset")
        if any(f.text not in self.source_text for f in self.facts):
            raise ValueError("Every fact must occur verbatim in source_text")
        return self


class Timing(StrictModel):
    chinese_chars_per_second: float = Field(default=4.5, gt=0)
    english_words_per_second: float = Field(default=2.5, gt=0)
    number_groups_per_second: float = Field(default=2.0, gt=0)
    punctuation_pause_seconds: float = Field(default=0.18, ge=0)
    minimum_scene_seconds: float = Field(default=2.0, gt=0)
    transition_seconds: float = Field(default=0.35, ge=0)


class BrandRules(StrictModel):
    brand: Text
    banned_phrases: list[Text]
    approved_nonfactual_copy: list[Text]
    timing: Timing = Field(default_factory=Timing)


class FactRef(StrictModel):
    asset_id: Text
    fact_id: Text
    evidence_text: Text
    claim_text: Text


class Scene(StrictModel):
    scene_id: Text
    visual: Text
    narration: str = Field(default="", max_length=12000)
    subtitle: str = Field(default="", max_length=12000)
    source_ids: list[Text] = Field(default_factory=list)
    fact_refs: list[FactRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def readable(self):
        if not self.narration.strip() and not self.subtitle.strip():
            raise ValueError("Scene requires narration or subtitles")
        if len(self.source_ids) != len(set(self.source_ids)):
            raise ValueError("Duplicate source IDs")
        return self


class Script(StrictModel):
    title: Text
    storyboard: list[Scene] = Field(min_length=1, max_length=30)
    risk_flags: list[Text] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_scenes(self):
        ids = [s.scene_id for s in self.storyboard]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate scene IDs")
        return self


class SearchArgs(StrictModel):
    query: Text
    keywords: list[Text] = Field(default_factory=list, max_length=20)
    asset_ids: list[Text] | None = None


class DraftArgs(StrictModel):
    script: Script


class EmptyArgs(StrictModel):
    pass


class RequestInfoArgs(StrictModel):
    fields: list[Text] = Field(min_length=1)
    question: Text


class StopArgs(StrictModel):
    reason: Text


ACTION_ARGUMENTS = {
    "search_assets": SearchArgs,
    "draft_script": DraftArgs,
    "estimate_duration": EmptyArgs,
    "check_brand_rules": EmptyArgs,
    "request_info": RequestInfoArgs,
    "finish": EmptyArgs,
    "stop": StopArgs,
}


class Action(StrictModel):
    action: Literal[
        "search_assets", "draft_script", "estimate_duration", "check_brand_rules",
        "request_info", "finish", "stop",
    ]
    arguments: dict
    reason_summary: Annotated[str, StringConstraints(min_length=1, max_length=500)]


def action_catalog() -> dict:
    return {name: schema.model_json_schema() for name, schema in ACTION_ARGUMENTS.items()}
