# schema_definition.py

import json
import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict

# 1. Import the schema generator class
# from pydantic.json_schema import GenerateJsonSchema


# 2. Define a custom schema generator that inlines all references
# class InlineSchemaGenerator(GenerateJsonSchema):
#     """
#     Custom schema generator that inlines all references ($ref)
#     by setting ref_mode = 'none'.
#     """

#     ref_mode = "none"


# --- Enums: Define all controlled vocabularies ---


class KeyEntityType(str, Enum):
    ORGANIZATION = "Organization"
    CLUB = "Club"
    PUBLICATION = "Publication"
    EVENT = "Event"
    OTHER = "Other"


class PersonCategory(str, Enum):
    FAMILY = "Family"
    FRIEND = "Friend"
    CLASSMATE = "Classmate"
    TEACHER = "Teacher"
    PUBLIC_FIGURE = "Public Figure"
    ACQUAINTANCE = "Acquaintance"
    ORGANIZATION_MEMBER = "Organization Member"
    UNKNOWN = "Unknown"


class Sentiment(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"
    MIXED = "Mixed"


class DateConfidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFERRED = "Inferred"


# --- Component Models ---


class DateInfo(BaseModel):
    original_text: str = Field(
        description="The date as it was originally written in the diary.",
        example="Sun. 1944",
    )
    iso_date: Optional[datetime.date] = Field(
        description="The normalized date in YYYY-MM-DD format. Null if it cannot be determined.",
        example="1944-01-02",
    )
    date_confidence: DateConfidence = Field(
        description="Confidence level in the accuracy of the normalized ISO date.",
        example=DateConfidence.HIGH,
    )


class Mention(BaseModel):
    metion_id: str = Field(
        description="A unique, internally generated ID for this metion (e.g., 'metion-001'). Useful for database linking.",
        example="metion-002",
    )
    name: str = Field(
        description="The name of the person as it appears in the text.", example="Flo"
    )
    context: str = Field(
        description="The specific phrase or sentence where the person was mentioned, providing context.",
        example="Flo came up for a few minutes.",
    )


class Annotation(BaseModel):
    term: str = Field(
        description="The specific term, phrase, or symbol being annotated.",
        example="wormy",
    )
    context: str = Field(
        description="The full sentence or phrase where the term appeared.",
        example="Frank Sinatra is still wormy.",
    )
    explanation: str = Field(
        description="An explanation of the term's meaning, cultural relevance, or translation.",
        example="A 1940s slang term expressing contempt, implying someone is pathetic or creepy. It was a common term of derision used by those who disliked Frank Sinatra during his rise to fame.",
    )


class KeyEntity(BaseModel):
    name: str = Field(example="Arcadettes")
    type: KeyEntityType = Field(example=KeyEntityType.CLUB)
    description: str = Field(
        example="A social club the author and her friends (like Lilly and Dody) are members of."
    )


class DateRange(BaseModel):
    start_date: Optional[datetime.date] = Field(
        description="The ISO 8601 date of the first entry.", example="1943-01-01"
    )
    end_date: Optional[datetime.date] = Field(
        description="The ISO 8601 date of the last entry.", example="1948-01-05"
    )


# --- Core Data Structure Models ---


class Person(BaseModel):
    person_id: str = Field(
        description="A unique, internally generated ID for this person (e.g., 'person-001'). Useful for database linking.",
        example="person-002",
    )
    name: str = Field(
        description="The full, standardized name of the person. Standardize where possible (e.g., 'Lilly K.' instead of 'Lilly').",
        example="Lilly K.",
    )
    # Corrected 'example_values' to 'examples'
    aliases: List[str] = Field(
        description="A list of other names, nicknames, or initials this person is referred to by in the text.",
        examples=[["Lilly"]],
    )
    is_primary_author: bool = Field(
        description="True if this person is the author of the diary.", example=False
    )
    category: PersonCategory = Field(
        description="The general category of the person's relationship to the author.",
        example=PersonCategory.FRIEND,
    )
    description: str = Field(
        description="A brief, AI-generated summary of this person based on all mentions in the diary.",
        example="A friend of the author, member of the Arcadettes club, who was absent from school to work on her 'career book'.",
    )
    mention_count: int = Field(
        description="The total number of diary entries this person is mentioned in.",
        example=4,
    )


class DiaryMetadata(BaseModel):
    archive_id: str = Field(
        description="The unique identifier for this diary in the archival system.",
        example="D-1943-SP-001",
    )
    title: str = Field(
        description="The title of the diary, if one is written on the cover (e.g., 'My European Tour'). Otherwise, a generated title.",
        example="TWO (FIVE) YEAR DIARY",
    )
    author: str = Field(
        description="The name of the person who wrote the diary. Can be 'Unknown'.",
        example="Shirley Pearl",
    )
    date_range: DateRange
    physical_description: str = Field(
        description="A description of the physical object (e.g., 'Small leather-bound book, brown cover with gold leaf, spine is damaged.')",
        example="Brown leather-bound diary, 5x7 inches, with significant water damage on the back cover. Pre-printed 'Five Year Diary' with 'FIVE' crossed out and 'TWO' written above. Pages are cream-colored with purple printed lines.",
    )
    provenance: str = Field(
        description="Information about the diary's origin and ownership history.",
        example="Donated by the estate of Eleanor Vance, granddaughter of the author.",
    )
    primary_language: str = Field(
        description="The dominant language used throughout the diary.",
        example="English",
    )
    # Corrected 'example_values' to 'examples'
    secondary_languages: List[str] = Field(
        description="A list of other languages that appear occasionally in the diary.",
        examples=[["French", "Yiddish"]],
    )
    # Corrected 'example_values' to 'examples'
    writing_systems: List[str] = Field(
        description="A list of scripts or writing systems used, including any identified shorthand.",
        examples=[["Cursive", "Gregg Shorthand"]],
    )
    language: str = Field(
        description="The primary language of the diary.", example="English"
    )
    key_entities: List[KeyEntity] = Field(
        description="A list of significant recurring organizations, groups, or concepts mentioned in the diary."
    )


class DiaryEntry(BaseModel):
    date_info: DateInfo
    page_number: int = Field(
        description="The page number where this entry begins.", example=3
    )
    full_text: str = Field(
        description="The complete, verbatim transcription of the diary entry.",
        example="Stayed home all day. Finished my career book. Flo came up for a few minutes. Mother & Father went downtown to see a Jewish show. Last day of vacation. Oh Foo. Did homework. (Can't fill my space which isn't unusual). Frank Sinatra is still wormy.",
    )
    summary: str = Field(
        description="A one or two-sentence summary of the entry's content.",
        example="The author spent the last day of vacation at home, finishing her career book and doing homework. Her friend Flo visited, her parents went to a show, and she reiterated her dislike for Frank Sinatra.",
    )
    mentioned_people: List[Mention] = Field(
        description="A list of people mentioned specifically in this entry."
    )
    # Corrected 'example_values' to 'examples'
    mentioned_locations: List[str] = Field(
        description="A list of specific places mentioned in this entry (e.g., 'Miller's Pond', 'Tremont Ave').",
        examples=[["downtown"]],
    )
    # Corrected 'example_values' to 'examples'
    key_events: List[str] = Field(
        description="A list of key events or topics discussed in the entry.",
        examples=[["End of vacation", "Working on 'career book'"]],
    )
    sentiment: Sentiment = Field(
        description="The inferred overall sentiment of the entry.",
        example=Sentiment.NEUTRAL,
    )
    annotations: List[Annotation] = Field(
        description="A list of noteworthy cultural references, slang, or ambiguous terms with explanations. Notes on slang, cultural references, foreign languages, or shorthand."
    )


class Diary(BaseModel):
    """
    Represents a single, complete diary document.
    """

    model_config = ConfigDict(
        title="Diary Archival Schema",
        description="A comprehensive, unified schema for extracting and structuring information from scanned diary pages, designed to be flexible for various diary formats and historical contexts.4",
        # 4. Use the custom generator for this model
        # json_schema_generator=InlineSchemaGenerator,
    )
    metadata: DiaryMetadata
    people_index: List[Person] = Field(
        description="A comprehensive index of all individuals mentioned in the diary."
    )
    entries: List[DiaryEntry] = Field(
        description="A chronological list of all the entries transcribed from the diary."
    )


if __name__ == "__main__":
    # Generate the JSON Schema from the top-level Pydantic model.
    # Because we configured the json_schema_generator in the model_config,
    # we don't need to pass it here again. Pydantic will use the one we set.
    schema = Diary.model_json_schema()

    # Alternatively, you can pass the generator directly here if you don't want
    # to set it in the model's config, like so:
    # schema = Diary.model_json_schema(schema_generator=InlineSchemaGenerator)

    # Print it to standard output with readable formatting
    print(json.dumps(schema, indent=2))
