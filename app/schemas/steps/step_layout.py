from typing import Literal, Union, Annotated
from pydantic import BaseModel, Field
from .step_blocks import StepBlock

class VerticalStepContent(BaseModel):
    version: Literal[1]
    layout: Literal["vertical"]
    blocks: list[StepBlock] = Field(default_factory=list)


class TwoColumnsStepContent(BaseModel):
    version: Literal[1]
    layout: Literal["two_columns"]
    left: list[StepBlock] = Field(default_factory=list)
    right: list[StepBlock] = Field(default_factory=list)
    
    
StepContent = Annotated[
    Union[VerticalStepContent, TwoColumnsStepContent],
    Field(discriminator="layout")
]