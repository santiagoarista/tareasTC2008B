# FixedAgent: Immobile agents permanently fixed to cells
from mesa.discrete_space import FixedAgent

class Cell(FixedAgent):
    """Represents a single ALIVE or DEAD cell in the simulation."""

    DEAD = 0
    ALIVE = 1

    @property
    def x(self):
        return self.cell.coordinate[0]

    @property
    def y(self):
        return self.cell.coordinate[1]

    @property
    def is_alive(self):
        return self.state == self.ALIVE

    @property
    def neighbors(self):
        return self.cell.neighborhood.agents
    
    def __init__(self, model, cell, init_state=DEAD):
        """Create a cell, in the given state, at the given x, y position."""
        super().__init__(model)
        self.cell = cell
        self.pos = cell.coordinate
        self.state = init_state
        self._next_state = None

    def determine_state(self, row):
        """Compute if the cell will be dead or alive at the next tick.  This is
        based on the number of alive or dead neighbors.  The state is not
        changed here, but is just computed and stored in self._nextState,
        because our current state may still be necessary for our neighbors
        to calculate their next state.
        """
        # Get the neighbors and apply the rules on whether to be alive or dead
        # at the next tick.
        neighbor_info = [(n.state) for n in self.neighbors]
        # Assume nextState is unchanged, unless changed below.
        self._next_state = self.state

        neighborStates ={
            '111' : 0,
            '110' : 1,
            '101' : 0,
            '100' : 1,
            '011' : 1,
            '010' : 0,
            '001' : 1,
            '000' : 0
        }

        # Update only if the row matches the y position of the cell based on the key based on the top neighbors
        if self.pos[1] == row:
            key = f"{neighbor_info[2]}{neighbor_info[4]}{neighbor_info[7]}"
            self._next_state = neighborStates[key]
 

    def assume_state(self):
        """Set the state to the new computed state -- computed in step()."""
        self.state = self._next_state