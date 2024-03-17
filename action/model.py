from typing import List, Optional
from sqlalchemy.orm import (
    DeclarativeBase,
    mapped_column,
    Mapped,
    sessionmaker
)
from sqlalchemy import (
    ForeignKey,
    create_engine,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class App(Base):
    __tablename__ = 'app'

    id: Mapped[str] = mapped_column(primary_key=True)

    name: Mapped[str]
    description: Mapped[str]
    profile_list: Mapped[str]

    tasks: Mapped[Optional[List["Task"]]] = relationship(
        back_populates="app", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"App(id={self.id!r}, name={self.name!r}, description={self.description!r}, profile_list={self.profile_list!r}, \ntasks={[t.__repr__ for t in self.tasks]})"
    
    def to_dict(self) -> dict:
        return dict(
            id = self.id,
            name = self.name,
            description = self.description,
            tasks = [t.to_dict() for t in self.tasks],
            profile_list = str_to_list(self.profile_list)
        )

class Task(Base):
    __tablename__ = 'task'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    app_id: Mapped[int] = mapped_column(ForeignKey("app.id"))
    task_id: Mapped[int]
    description: Mapped[str]
    type: Mapped[str]
    address: Mapped[str]
    args: Mapped[Optional[List["Arg"]]] = relationship(
        back_populates="task", cascade="all, delete-orphan")

    app: Mapped["App"] = relationship(
        back_populates="tasks", cascade="all"
    )

    def __repr__(self) -> str:
        return f"Task(app_id={self.app_id!r}, id={self.id!r}, task_id={self.task_id!r}, description={self.description!r}, type={self.type!r}, address={self.address!r}, \nargs={[a.__repr__() for a in self.args]})"

    def to_dict(self) -> dict:
        return dict(
            id = self.id,
            description = self.description,
            task_id = self.task_id,
            address = self.address,
            args = [a.to_dict() for a in self.args]
        )
    
class Arg(Base):
    __tablename__ = 'task_arg'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task.id"))

    name: Mapped[str]
    description: Mapped[str]
    type: Mapped[str]
    value: Mapped[Optional[str]]

    task: Mapped["Task"] = relationship(
        back_populates="args", cascade="all"
    )

    def __repr__(self) -> str:
        return f"<Arg(name={self.name!r}, description={self.description}, value={self.value})>"
    
    def to_dict(self) -> dict:
        return dict(
            name = self.name,
            type = self.type,
            value = self.value,
            description = self.description
        )
    
def str_to_list(s:str) -> list[int]:
    if s == "[]":
        return []
    dep_list = s.strip('[]').split(',')
    dep_list = [int(num.strip()) for num in dep_list if num.strip()]
    return dep_list

def list_to_str(l: list[int]) -> str:
    if l == []:
        return "[]"
    dep_str = ','.join(map(str, l))
    return f"[{dep_str}]"

engine = create_engine(
    "sqlite:///./action/app.db"
)

Base.metadata.create_all(engine)

session_factory = sessionmaker(engine, expire_on_commit=False)