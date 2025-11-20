"""
Type definitions for FAF (Foundational AI-context Format)

These mirror the TypeScript definitions in faf-cli for cross-language compatibility.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProjectInfo:
    """Core project metadata"""
    name: str
    goal: Optional[str] = None
    main_language: Optional[str] = None
    approach: Optional[str] = None
    version: Optional[str] = None
    license: Optional[str] = None


@dataclass
class StackInfo:
    """Technical stack breakdown"""
    frontend: Optional[str] = None
    backend: Optional[str] = None
    database: Optional[str] = None
    infrastructure: Optional[str] = None
    build_tool: Optional[str] = None
    testing: Optional[str] = None
    cicd: Optional[str] = None


@dataclass
class InstantContext:
    """Quick context for AI understanding"""
    what_building: Optional[str] = None
    tech_stack: Optional[str] = None
    deployment: Optional[str] = None
    key_files: List[str] = field(default_factory=list)
    commands: Dict[str, str] = field(default_factory=dict)


@dataclass
class ContextQuality:
    """Quality metrics for the FAF file"""
    slots_filled: Optional[str] = None
    confidence: Optional[str] = None
    handoff_ready: bool = False
    missing_context: List[str] = field(default_factory=list)


@dataclass
class HumanContext:
    """The 6 W's - human-readable context"""
    who: Optional[str] = None  # Target users
    what: Optional[str] = None  # Core problem
    why: Optional[str] = None   # Mission/purpose
    how: Optional[str] = None   # Approach
    where: Optional[str] = None # Deployment
    when: Optional[str] = None  # Timeline


@dataclass
class AIScoring:
    """AI-readiness scoring system"""
    score: Optional[int] = None  # 0-100
    confidence: Optional[str] = None  # LOW, MEDIUM, HIGH
    version: Optional[str] = None


@dataclass
class AIInstructions:
    """Instructions for AI assistants"""
    working_style: Optional[str] = None
    quality_bar: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    focus_areas: List[str] = field(default_factory=list)


@dataclass
class Preferences:
    """Development preferences"""
    quality_bar: Optional[str] = None
    testing: Optional[str] = None
    documentation: Optional[str] = None
    code_style: Optional[str] = None


@dataclass
class State:
    """Project state tracking"""
    phase: Optional[str] = None
    version: Optional[str] = None
    focus: Optional[str] = None
    milestones: List[str] = field(default_factory=list)


@dataclass
class FafData:
    """
    Complete FAF file structure

    Represents the full parsed content of a .faf file.
    All fields are optional except faf_version and project.
    """
    faf_version: str
    project: ProjectInfo

    # Optional sections
    ai_score: Optional[int] = None
    ai_confidence: Optional[str] = None
    ai_tldr: Optional[Dict[str, str]] = None
    instant_context: Optional[InstantContext] = None
    context_quality: Optional[ContextQuality] = None
    stack: Optional[StackInfo] = None
    human_context: Optional[HumanContext] = None
    ai_instructions: Optional[AIInstructions] = None
    preferences: Optional[Preferences] = None
    state: Optional[State] = None
    tags: List[str] = field(default_factory=list)

    # Raw data for unrecognized fields
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FafData":
        """Create FafData from parsed YAML dictionary"""
        project_data = data.get("project", {})
        if isinstance(project_data, str):
            project_data = {"name": project_data}

        project = ProjectInfo(
            name=project_data.get("name", "unknown"),
            goal=project_data.get("goal"),
            main_language=project_data.get("main_language"),
            approach=project_data.get("approach"),
            version=project_data.get("version"),
            license=project_data.get("license")
        )

        # Parse instant_context
        instant_ctx = None
        if "instant_context" in data:
            ic = data["instant_context"]
            instant_ctx = InstantContext(
                what_building=ic.get("what_building"),
                tech_stack=ic.get("tech_stack"),
                deployment=ic.get("deployment"),
                key_files=ic.get("key_files", []),
                commands=ic.get("commands", {})
            )

        # Parse stack
        stack = None
        if "stack" in data:
            s = data["stack"]
            stack = StackInfo(
                frontend=s.get("frontend"),
                backend=s.get("backend"),
                database=s.get("database"),
                infrastructure=s.get("infrastructure"),
                build_tool=s.get("build_tool"),
                testing=s.get("testing"),
                cicd=s.get("cicd")
            )

        # Parse context_quality
        ctx_quality = None
        if "context_quality" in data:
            cq = data["context_quality"]
            ctx_quality = ContextQuality(
                slots_filled=cq.get("slots_filled"),
                confidence=cq.get("confidence"),
                handoff_ready=cq.get("handoff_ready", False),
                missing_context=cq.get("missing_context", [])
            )

        # Parse human_context
        human_ctx = None
        if "human_context" in data:
            hc = data["human_context"]
            human_ctx = HumanContext(
                who=hc.get("who"),
                what=hc.get("what"),
                why=hc.get("why"),
                how=hc.get("how"),
                where=hc.get("where"),
                when=hc.get("when")
            )

        # Parse AI score
        ai_score = data.get("ai_score")
        if isinstance(ai_score, str) and ai_score.endswith("%"):
            ai_score = int(ai_score.rstrip("%"))

        return cls(
            faf_version=data.get("faf_version", "2.5.0"),
            project=project,
            ai_score=ai_score,
            ai_confidence=data.get("ai_confidence"),
            ai_tldr=data.get("ai_tldr"),
            instant_context=instant_ctx,
            context_quality=ctx_quality,
            stack=stack,
            human_context=human_ctx,
            preferences=None,  # Add parsing if needed
            state=None,  # Add parsing if needed
            tags=data.get("tags", []),
            raw=data
        )
