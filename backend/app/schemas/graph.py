from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    kind: str
    risk_score: float = Field(ge=0, le=100)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    confidence: float = Field(ge=0, le=1)
    weight: float = Field(ge=0)


class GraphSliceResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    freshness_status: str
    max_depth: int
    max_nodes: int


class AttackPathResponse(BaseModel):
    path: list[str]
    risk_score: float = Field(ge=0, le=100)
    critical_nodes: list[str]
    confidence: float = Field(ge=0, le=1)
    message: str


class GraphProjectionJobResponse(BaseModel):
    task_id: str
    status: str
    message: str

