from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

ALIASES = {'js': 'javascript', 'postgres': 'postgresql', 'py': 'python', 'ts': 'typescript',
           'bangalore':'bengaluru','gurgaon':'gurugram'}

def normalize(value: str) -> str:
    value = value.strip().casefold()
    return ALIASES.get(value, value)

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Profile(StrictModel):
    skills: list[str] = Field(default_factory=list, max_length=40)
    interests: str = Field(default='', max_length=1000)
    graduation_year: int = Field(default=2028, ge=2020, le=2040)
    remote_only: bool = False
    preferred_locations: list[str] = Field(default_factory=list, max_length=15)
    allow_unknown_graduation: bool = False

    @field_validator('skills', 'preferred_locations')
    @classmethod
    def clean_list(cls, values):
        if any(len(v) > 100 for v in values):
            raise ValueError('Each entry must be at most 100 characters')
        return sorted({normalize(v) for v in values if v.strip()})

class SearchArgs(StrictModel):
    query: str = Field(max_length=1000)

class ResumeExtraction(StrictModel):
    is_resume: bool
    skills: list[str] = Field(max_length=40)
    interests: str = Field(max_length=1000)
    graduation_year: int | None = Field(default=None,ge=2020,le=2040)

    @field_validator('skills')
    @classmethod
    def clean_skills(cls,values):
        return Profile.clean_list(values)

class PreferenceArgs(StrictModel):
    remote_only: bool | None = None
    preferred_locations: list[str] | None = Field(default=None, max_length=15)
    add_skills: list[str] = Field(default_factory=list,max_length=40)
    remove_skills: list[str] = Field(default_factory=list,max_length=40)

    @field_validator('add_skills','remove_skills')
    @classmethod
    def clean_skills(cls,values):
        return Profile.clean_list(values)

    @model_validator(mode='after')
    def reject_conflicting_skills(self):
        if set(self.add_skills) & set(self.remove_skills):
            raise ValueError('A skill cannot be added and removed in the same change.')
        return self

    @field_validator('preferred_locations')
    @classmethod
    def clean_locations(cls, values):
        if values is None:
            return None
        return Profile.clean_list(values)

def preference_skills(current,args):
    """Apply explicit deltas to the latest skills; enforce the profile's limit."""
    return Profile(skills=sorted((set(current)-set(args.remove_skills)) | set(args.add_skills))).skills

class Job(BaseModel):
    model_config = ConfigDict(extra='forbid')
    source_url: HttpUrl
    title: str = Field(min_length=3, max_length=180)
    company: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=10, max_length=1600)
    required_skills: list[str] | None = None
    work_mode: Literal['remote', 'hybrid', 'onsite'] | None = None
    location: str | None = None
    eligible_graduation_years: list[int] | None = None
    last_checked_at: date
    is_active: bool
    # Exact allowed places, including country for remote listings. Unknown stays null.
    compatible_locations: list[str] | None = None

    @field_validator('required_skills', 'compatible_locations')
    @classmethod
    def normalize_lists(cls, value):
        return sorted({normalize(v) for v in value}) if value else None

    @field_validator('eligible_graduation_years')
    @classmethod
    def valid_years(cls, value):
        if value is not None and (not value or any(y < 2020 or y > 2040 for y in value)):
            raise ValueError('Eligibility must contain explicit years from 2020 to 2040')
        return value

    @field_validator('last_checked_at')
    @classmethod
    def not_future(cls, value):
        if value > date.today():
            raise ValueError('Review date cannot be in the future')
        return value
