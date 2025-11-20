from mesa.discrete_space import CellAgent, FixedAgent
import heapq

class CleanerAgent(CellAgent):
    """
    Cleaning agent with battery management.
    Attributes:
        unique_id: Agent's ID
        battery: Current battery level (0-100)
        moves: Number of moves made
        cleaned_cells: Number of cells cleaned
    """
    def __init__(self, model, cell, initial_station=None):
        """
        Creates a new cleaning agent.
        Args:
            model: Model reference for the agent
            cell: Reference to its position within the grid
            initial_station: Reference to initial charging station (for multi-agent) // (multi-agent == True: initial_station is declared as [1,1])
        """
        super().__init__(model)
        self.cell = cell
        self.battery = 100  # Start with full battery
        self.moves = 0
        self.cleaned_cells = 0
        self.returning_to_charge = False
        self.initial_station = initial_station  # Store initial station reference
        self.path_to_station = []  # Cache the path to charging station
        self.visited_cells = set()  # Track visited cells
        self.visited_cells.add(cell)  # Mark starting cell as visited

    def dijkstra_path(self, target_cell):
        """
        Find shortest path to target using Dijkstra's algorithm.
        Returns list of cells from current position to target (excluding current cell).
        """
        # Priority queue: (cost, counter, cell) - counter breaks ties
        counter = 0
        pq = [(0, counter, self.cell)]
        visited = set()
        came_from = {}
        cost_so_far = {self.cell: 0}
        
        def can_move_to(cell):
            """
            Check if cell is traversable
            """
            if cell.is_empty:
                return True
            # Can move through charging stations and dirty cells
            for agent in cell.agents:
                if isinstance(agent, (ChargingStationAgent, DirtyCellAgent)):
                    return True
                if isinstance(agent, CleanerAgent) and agent != self:
                    return True  # Can share cells with other cleaners
            return False
        
        while pq:
            current_cost, _, current_cell = heapq.heappop(pq)
            
            if current_cell in visited:
                continue
            
            visited.add(current_cell)
            
            # Found the target
            if current_cell == target_cell:
                # Reconstruct path
                path = []
                cell = target_cell
                while cell in came_from:
                    path.append(cell)
                    cell = came_from[cell]
                path.reverse()
                return path
            
            # Explore neighbors
            for neighbor in current_cell.neighborhood.cells:
                if neighbor in visited:
                    continue
                
                if not can_move_to(neighbor):
                    continue
                
                new_cost = current_cost + 1
                
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    came_from[neighbor] = current_cell
                    counter += 1
                    heapq.heappush(pq, (new_cost, counter, neighbor))
        
        # No path found
        return []

    def find_charging_station(self):
        """
        Finds the path to the nearest charging station.
        In multi-agent mode, agents only know their initial station initially,
        but can charge at any station they discover.
        """
        # Find all charging stations
        charging_stations = [agent for agent in self.model.agents 
                           if isinstance(agent, ChargingStationAgent)]
        
        if not charging_stations:
            return None
        
        # In multi-agent mode, prefer initial station if known
        # but can use any station (simulating discovery)
        if self.model.multi_agent_mode and self.initial_station:
            # Check if initial station is accessible, otherwise find nearest
            if self.initial_station in charging_stations:
                return self.initial_station
        
        # Get the nearest charging station (any station)
        min_distance = float('inf')
        nearest_station = None
        
        for station in charging_stations:
            dx = abs(self.cell.coordinate[0] - station.cell.coordinate[0])
            dy = abs(self.cell.coordinate[1] - station.cell.coordinate[1])
            distance = dx + dy
            
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
        
        return nearest_station

    def move_towards_station(self, target_cell):
        """
        Move one step towards the target cell using cached Dijkstra path.
        """
        # If we don't have a path or we've deviated from it, recalculate
        if not self.path_to_station or (self.path_to_station and self.path_to_station[0] != self.cell.neighborhood.select(lambda c: c == self.path_to_station[0]).cells):
            self.path_to_station = self.dijkstra_path(target_cell)
        
        # If we have a valid path, take the first step
        if self.path_to_station:
            next_cell = self.path_to_station.pop(0)
            
            # Verify the cell is still accessible
            def can_move_to(cell):
                if cell.is_empty:
                    return True
                for agent in cell.agents:
                    if isinstance(agent, (ChargingStationAgent, DirtyCellAgent)):
                        return True
                    if isinstance(agent, CleanerAgent) and agent != self:
                        return True
                return False
            
            if can_move_to(next_cell):
                self.cell = next_cell
                self.visited_cells.add(next_cell)  # Mark as visited
                self.battery -= 1
                self.moves += 1
            else:
                # Path blocked, recalculate next time
                self.path_to_station = []

    def clean_current_cell(self):
        """
        Clean the current cell if it's dirty
        """
        # Check if current cell has a dirty cell agent
        for agent in self.cell.agents:
            if isinstance(agent, DirtyCellAgent) and agent.is_dirty:
                agent.is_dirty = False
                self.battery -= 1
                self.cleaned_cells += 1
                self.model.dirty_cells -= 1
                return True
        return False

    def move(self):
        """
        Determines the next cell and moves to it.
        Prioritizes: 1) Dirty cells, 2) Unvisited cells, 3) Random cell
        """
        # Check which grid cells are empty or have charging station/dirty cell
        def can_move_to(cell):
            if cell.is_empty:
                return True
            # Check if cell has charging station or dirty cell
            for agent in cell.agents:
                if isinstance(agent, (ChargingStationAgent, DirtyCellAgent)):
                    return True
            return False
        
        next_moves = self.cell.neighborhood.select(can_move_to)
        
        if next_moves.cells:
            # Priority 1: Prioritize dirty cells
            dirty_cells = []
            for cell in next_moves.cells:
                for agent in cell.agents:
                    if isinstance(agent, DirtyCellAgent) and agent.is_dirty:
                        dirty_cells.append(cell)
                        break
            
            if dirty_cells:
                # Move to a dirty cell (prefer unvisited if available)
                unvisited_dirty = [c for c in dirty_cells if c not in self.visited_cells]
                if unvisited_dirty:
                    chosen_cell = self.random.choice(unvisited_dirty)
                else:
                    chosen_cell = self.random.choice(dirty_cells)
                self.cell = chosen_cell
            else:
                # Priority 2: Move to unvisited cells if available
                unvisited_cells = [c for c in next_moves.cells if c not in self.visited_cells]
                if unvisited_cells:
                    self.cell = self.random.choice(unvisited_cells)
                else:
                    # Priority 3: All cells visited, move randomly
                    self.cell = next_moves.select_random_cell()
            
            # Mark new cell as visited
            self.visited_cells.add(self.cell)
            self.battery -= 1
            self.moves += 1

    def step(self):
        """
        Agent's behavior in each step
        """
        # Check if at charging station
        at_charging_station = any(isinstance(agent, ChargingStationAgent) 
                                 for agent in self.cell.agents)
        
        if at_charging_station:
            if self.battery < 100:
                # Charge battery - stay here until fully charged
                self.battery = min(100, self.battery + 5)
                self.returning_to_charge = True  # Keep flag until fully charged
                return  # Don't do anything else, just charge
            else:
                # Fully charged, can now continue cleaning
                self.returning_to_charge = False
        
        # Check battery level
        if self.battery <= 20 and not at_charging_station:
            # Need to return to charging station
            self.returning_to_charge = True
            station = self.find_charging_station()
            if station:
                self.move_towards_station(station.cell)
            return
        
        if self.battery <= 0:
            # No battery, can't do anything
            return
        
        # Try to clean current cell
        cleaned = self.clean_current_cell()
        
        if not cleaned and self.battery > 0:
            # Move to next cell
            self.move()


class ObstacleAgent(FixedAgent):
    """
    Obstacle agent. Just to add obstacles to the grid.
    """
    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell

    def step(self):
        pass


class DirtyCellAgent(FixedAgent):
    """
    Represents a cell that can be dirty or clean.
    """
    def __init__(self, model, cell, is_dirty=False):
        super().__init__(model)
        self.cell = cell
        self.is_dirty = is_dirty

    def step(self):
        pass


class ChargingStationAgent(FixedAgent):
    """
    Charging station for cleaning agents.
    """
    def __init__(self, model, cell):
        super().__init__(model)
        self.cell = cell

    def step(self):
        pass