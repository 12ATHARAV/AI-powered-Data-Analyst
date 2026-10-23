import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    """User profile response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clerk_user_id: str
    email: str | None = None


class ColumnProfile(BaseModel):
    """Profile of a single column."""
    name: str
    dtype: str
    role: str
    null_count: int
    null_pct: float
    unique: int
    min: str | None = None
    max: str | None = None
    examples: list[str] = Field(default_factory=list)


class TableProfile(BaseModel):
    """Full table profile."""
    columns: list[ColumnProfile]


class FileOut(BaseModel):
    """File metadata output."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_name: str
    table_name: str
    rows: int
    cols: int
    size_bytes: int
    warnings: list[str] = Field(default_factory=list, validation_alias="warnings_json")
    created_at: datetime
    profile: dict[str, Any] = Field(default_factory=dict, validation_alias="profile_json")
    quality_score: int = 100


class FileDetail(FileOut):
    """Detailed file response including preview."""
    preview: dict[str, Any]  # {columns: list[str], rows: list[list[Any]]}


class FileUploadError(BaseModel):
    """Per-file error during multipart upload."""
    filename: str
    detail: str


class FilesUploadResponse(BaseModel):
    """Batch file upload response."""
    files: list[FileOut]
    errors: list[FileUploadError] = Field(default_factory=list)


class Join(BaseModel):
    """Suggested relationship between two tables."""
    left_table: str
    left_column: str
    right_table: str
    right_column: str
    overlap: float


class FilesListResponse(BaseModel):
    """List of files with suggested joins."""
    files: list[FileOut]
    joins: list[Join] = Field(default_factory=list)


class QualityIssue(BaseModel):
    """Identified data quality problem."""
    table: str
    column: str | None = None
    check: str
    severity: Literal["high", "medium", "low"]
    count: int
    detail: str
    impact: str


class QualityReport(BaseModel):
    """Comprehensive data quality report."""
    score: int
    issues: list[QualityIssue]
    by_table: dict[str, dict[str, Any]]


class SearchQuery(BaseModel):
    """Semantic catalog search query."""
    query: str
    top_k: int = 8


class SearchResult(BaseModel):
    """Single semantic search result item."""
    kind: Literal["column", "value"]
    table: str
    column: str
    value: str | None = None
    score: float


class SearchResponse(BaseModel):
    """Semantic search response."""
    results: list[SearchResult]


class ConversationCreate(BaseModel):
    """Payload to create a conversation."""
    title: str | None = None


class ConversationOut(BaseModel):
    """Conversation thread metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None = None
    created_at: datetime


class ConversationsListResponse(BaseModel):
    """List of conversations."""
    conversations: list[ConversationOut]


class ChartFigure(BaseModel):
    """Plotly figure JSON structure."""
    data: list[dict[str, Any]]
    layout: dict[str, Any]


class ChartArtifact(BaseModel):
    """Chart artifact."""
    kind: Literal["chart"] = "chart"
    title: str
    figure: dict[str, Any]
    sql: str | None = None


class TableArtifact(BaseModel):
    """Data table artifact."""
    kind: Literal["table"] = "table"
    title: str
    columns: list[str]
    rows: list[list[Any]]
    truncated: bool = False


class SqlArtifact(BaseModel):
    """Executed SQL or Python script artifact."""
    kind: Literal["sql"] = "sql"
    language: Literal["sql", "python"] = "sql"
    code: str
    purpose: str


class TraceStep(BaseModel):
    """Single step in agent reasoning trace."""
    kind: Literal["tool_call", "tool_result", "retry", "cache", "verify", "fallback"]
    name: str
    detail: dict[str, Any]
    elapsed_ms: int


class TokenUsage(BaseModel):
    """LLM token usage."""
    prompt: int = 0
    completion: int = 0


class Trace(BaseModel):
    """Agent execution trace."""
    provider: str
    model: str
    fell_back: bool = False
    steps: list[TraceStep] = Field(default_factory=list)
    tokens: TokenUsage = Field(default_factory=TokenUsage)


class Verification(BaseModel):
    """Answer number verification summary."""
    checked: int
    unverified: list[float] = Field(default_factory=list)
    ok: bool


class MessageOut(BaseModel):
    """Chat message output with artifacts and trace."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list, validation_alias="artifacts_json")
    trace: Trace | None = Field(default=None, validation_alias="trace_json")
    verification: Verification | None = Field(default=None, validation_alias="verification_json")
    created_at: datetime


class MessagesListResponse(BaseModel):
    """List of messages in a thread."""
    messages: list[MessageOut]


class ChatRequest(BaseModel):
    """User prompt to the agent."""
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Agent reply with message and cache indicator."""
    message: MessageOut
    cached: bool = False


class Kpi(BaseModel):
    """Key performance indicator summary card."""
    label: str
    value: int | float | str
    format: Literal["number", "currency", "percent", "text"]
    hint: str | None = None


class PinCreate(BaseModel):
    """Create dashboard pin payload."""
    title: str
    figure: dict[str, Any]
    sql: str | None = None


class PinOut(BaseModel):
    """Saved dashboard pin."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    figure: dict[str, Any] = Field(validation_alias="figure_json")
    sql: str | None = Field(default=None, validation_alias="sql_text")
    created_at: datetime


class DashboardResponse(BaseModel):
    """Dashboard view response."""
    kpis: list[Kpi]
    charts: list[ChartArtifact]
    pins: list[PinOut]
