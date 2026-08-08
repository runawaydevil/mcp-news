from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

_CATEGORY_DESC = (
    "Optional category to filter by: 'tech', 'programming', 'security', "
    "'science', 'linux', 'windows' or 'news'. Omit for all categories."
)


class LatestInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    category: Optional[str] = Field(default=None, description=_CATEGORY_DESC)
    source_id: Optional[str] = Field(
        default=None,
        description="Optional feed id to filter by (e.g. 'tecnoblog'). Omit for all feeds.",
    )
    limit: int = Field(default=10, ge=1, le=50,
                       description="Max number of articles to return.")


class SearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    keyword: str = Field(..., min_length=2, max_length=100,
                         description="Keyword to search for in titles and summaries.")
    category: Optional[str] = Field(default=None, description=_CATEGORY_DESC)
    limit: int = Field(default=10, ge=1, le=50,
                       description="Max number of articles to return.")
