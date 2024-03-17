from sqlalchemy.orm import (
    DeclarativeBase,
    mapped_column,
    Mapped,
)
from sqlalchemy import (
    create_engine,
)

class Base(DeclarativeBase):
    pass

class MethedologyInfo(Base):
    __tablename__ = "methodology"

    id: Mapped[str] = mapped_column(primary_key=True)
    scenario_description: Mapped[str]
    process_steps: Mapped[str]
    decision_points: Mapped[str]
    rules: Mapped[str]
    exception_handling: Mapped[str]
    suggestions: Mapped[str]
    reference_materails: Mapped[str]

    def __repr__(self) -> str:
        return f"""
        [ScenarioDescription]\n{self.scenario_description}\n\n
        [ProcessSteps]\n{self.process_steps}\n\n
        [DecisionPoints]\n{self.decision_points}\n\n
        [Rules]\n{self.rules}\n\n
        [ExceptionHandling]\n{self.exception_handling}\n\n
        [Suggestions]\n{self.suggestions}\n\n
        [ReferenceMaterials]\n{self.reference_materails}\n\n
        """

    def to_list_of_str(self) -> list[str]:
        return [self.id,
                self.scenario_description,
                self.process_steps,
                self.decision_points,
                self.rules,
                self.exception_handling,
                self.suggestions,
                self.reference_materails]

engine = create_engine(
    "sqlite:///./methodology/database/methodology.db"
)

Base.metadata.create_all(engine)
