"""Base action class for the command pattern implementation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from enum import Enum

from ..game.game_state import GameState


class ActionResult(Enum):
    """Result types for action execution."""
    SUCCESS = "success"
    FAILURE = "failure" 
    INVALID = "invalid"
    PARTIAL = "partial"


@dataclass
class ActionOutcome:
    """Result of executing an action."""
    result: ActionResult
    message: str
    data: Optional[Dict[str, Any]] = None
    follow_up_actions: Optional[List["BaseAction"]] = None


class BaseAction(ABC):
    """Base class for all game actions using Command pattern."""
    
    def __init__(self, player_id: int, action_type: str):
        self.player_id = player_id
        self.action_type = action_type
        self.executed = False
        self.outcome: Optional[ActionOutcome] = None
    
    @abstractmethod
    def validate(self, game_state: GameState) -> bool:
        """Check if this action can be executed in the current game state."""
        pass
    
    @abstractmethod
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute the action and return the outcome."""
        pass
    
    def can_undo(self) -> bool:
        """Check if this action can be undone (for scenario analysis)."""
        return False
    
    def undo(self, game_state: GameState) -> ActionOutcome:
        """Undo the action (for scenario rollback)."""
        return ActionOutcome(
            ActionResult.FAILURE,
            f"Action {self.action_type} cannot be undone"
        )
    
    def get_action_data(self) -> Dict[str, Any]:
        """Get serializable data about this action."""
        return {
            "player_id": self.player_id,
            "action_type": self.action_type,
            "executed": self.executed,
            "outcome": self.outcome.result.value if self.outcome else None
        }
    
    def log_execution(self, game_state: GameState, outcome: ActionOutcome):
        """Log this action's execution."""
        action_data = self.get_action_data()
        action_data.update({
            "outcome_message": outcome.message,
            "outcome_data": outcome.data
        })
        
        game_state._log_action(self.action_type, action_data)


class CompoundAction(BaseAction):
    """Action that consists of multiple sub-actions."""
    
    def __init__(self, player_id: int, action_type: str, sub_actions: List[BaseAction]):
        super().__init__(player_id, action_type)
        self.sub_actions = sub_actions
    
    def validate(self, game_state: GameState) -> bool:
        """All sub-actions must be valid."""
        return all(action.validate(game_state) for action in self.sub_actions)
    
    def execute(self, game_state: GameState) -> ActionOutcome:
        """Execute all sub-actions in sequence."""
        if not self.validate(game_state):
            return ActionOutcome(ActionResult.INVALID, "Compound action validation failed")
        
        results = []
        failed_actions = []
        
        for action in self.sub_actions:
            outcome = action.execute(game_state)
            results.append(outcome)
            
            if outcome.result == ActionResult.FAILURE:
                failed_actions.append(action.action_type)
        
        if failed_actions:
            result = ActionResult.PARTIAL if len(failed_actions) < len(self.sub_actions) else ActionResult.FAILURE
            message = f"Failed sub-actions: {', '.join(failed_actions)}"
        else:
            result = ActionResult.SUCCESS
            message = f"All {len(self.sub_actions)} sub-actions completed successfully"
        
        self.executed = True
        self.outcome = ActionOutcome(result, message, {"sub_results": results})
        self.log_execution(game_state, self.outcome)
        
        return self.outcome