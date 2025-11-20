from mesa import Model
from mesa.discrete_space import OrthogonalMooreGrid
from mesa.datacollection import DataCollector

from .agent import CleanerAgent, ObstacleAgent, DirtyCellAgent, ChargingStationAgent

class CleaningModel(Model):
    """
    Creates a new model with cleaning agents.
    Args:
        num_agents: Number of cleaning agents in the simulation
        width, height: The size of the grid to model
        dirty_percentage: Percentage of cells that are initially dirty (0-100)
        obstacle_percentage: Percentage of cells that are obstacles (0-100)
        max_time: Maximum time steps for the simulation
        multi_agent_mode: If True, agents start at random positions with their own stations
    """
    def __init__(self, num_agents=10, width=20, height=20, dirty_percentage=30, 
                 obstacle_percentage=10, max_time=1000, multi_agent_mode=True, seed=42):

        super().__init__(seed=seed)
        self.num_agents = num_agents 
        self.seed = seed
        self.width = width
        self.height = height
        self.dirty_percentage = dirty_percentage
        self.obstacle_percentage = obstacle_percentage
        self.max_time = max_time
        self.multi_agent_mode = multi_agent_mode #Choose whether it's a single or multi agent model [For single models num_agents needs to be adjusted to 1]
        self.current_step = 0
        self.cleaning_completed_at = None  # Track when cleaning is completed

        self.grid = OrthogonalMooreGrid([width, height], torus=False)

        # Calculate number of dirty and obstacle cells
        total_cells = width * height
        num_dirty = int((dirty_percentage / 100) * total_cells)
        num_obstacles = int((obstacle_percentage / 100) * total_cells)

        # Get all cells except borders (we'll use borders for walls or keep them free)
        available_cells = [cell for cell in self.grid if 
                          cell.coordinate[0] not in [0, width-1] and 
                          cell.coordinate[1] not in [0, height-1]]

        # Identify the coordinates of the border of the grid
        border = [(x, y)
                  for y in range(height)
                  for x in range(width)
                  if y in [0, height-1] or x in [0, width - 1]]

        # Create the border cells as obstacles
        for _, cell in enumerate(self.grid):
            if cell.coordinate in border:
                ObstacleAgent(self, cell=cell)

        # Remove border cells from available cells
        available_cells = [cell for cell in available_cells]

        # Setup based on mode
        if self.multi_agent_mode:
            # Multi-agent mode: Random positions with charging stations
            # Select random cells for agents and their charging stations
            if self.num_agents <= len(available_cells):
                agent_start_cells = self.random.sample(available_cells, self.num_agents)
                charging_stations = []
                
                for cell in agent_start_cells:
                    station = ChargingStationAgent(self, cell=cell)
                    charging_stations.append(station)
                    available_cells.remove(cell)
            else:
                raise ValueError("Not enough available cells for all agents")
        else:
            # Single agent mode: Start at [1,1] with charging station there
            charging_station_cell = self.grid[(1, 1)]
            single_station = ChargingStationAgent(self, cell=charging_station_cell)
            charging_stations = [single_station]
            available_cells.remove(charging_station_cell)

        # Randomly select cells for obstacles
        if num_obstacles > 0 and num_obstacles <= len(available_cells):
            obstacle_cells = self.random.sample(available_cells, num_obstacles)
            for cell in obstacle_cells:
                ObstacleAgent(self, cell=cell)
                available_cells.remove(cell)

        # Create all cells as DirtyCellAgent (clean by default)
        for cell in self.grid:
            # Skip cells that already have obstacles or charging station
            if not any(isinstance(agent, (ObstacleAgent, ChargingStationAgent)) 
                      for agent in cell.agents):
                DirtyCellAgent(self, cell=cell, is_dirty=False)

        # Randomly select cells to be dirty
        if num_dirty > 0 and num_dirty <= len(available_cells):
            dirty_cells = self.random.sample(available_cells, num_dirty)
            for cell in dirty_cells:
                # Find the DirtyCellAgent in this cell and make it dirty
                for agent in cell.agents:
                    if isinstance(agent, DirtyCellAgent):
                        agent.is_dirty = True
                        break

        # Count initial dirty cells
        self.dirty_cells = num_dirty
        self.initial_dirty_cells = num_dirty

        # Create cleaning agents
        if self.multi_agent_mode:
            # Create agents at their respective charging stations
            for i, station in enumerate(charging_stations):
                CleanerAgent(self, cell=station.cell, initial_station=station)
        else:
            # Create all agents at the single charging station
            for i in range(self.num_agents):
                CleanerAgent(self, cell=charging_stations[0].cell, initial_station=charging_stations[0])

        # Data collector
        self.datacollector = DataCollector(
            model_reporters={
                "Step": lambda m: m.current_step,
                "Dirty Cells": lambda m: m.dirty_cells,
                "Clean Percentage": lambda m: ((m.initial_dirty_cells - m.dirty_cells) / m.initial_dirty_cells * 100) if m.initial_dirty_cells > 0 else 100,
                "Total Moves": lambda m: sum(a.moves for a in m.agents if isinstance(a, CleanerAgent)),
                "Total Cleaned": lambda m: sum(a.cleaned_cells for a in m.agents if isinstance(a, CleanerAgent)),
            },
            agent_reporters={
                "Battery": lambda a: a.battery if isinstance(a, CleanerAgent) else None,
                "Moves": lambda a: a.moves if isinstance(a, CleanerAgent) else None,
                "Cleaned": lambda a: a.cleaned_cells if isinstance(a, CleanerAgent) else None,
                "X": lambda a: a.cell.coordinate[0] if isinstance(a, CleanerAgent) else None,
                "Y": lambda a: a.cell.coordinate[1] if isinstance(a, CleanerAgent) else None,
            }
        )

        self.running = True

    def step(self):
        '''Advance the model by one step.'''
        self.current_step += 1
        
        # Move agents
        self.agents.shuffle_do("step")
        
        # Collect data after agents move
        self.datacollector.collect(self)
        
        # Check if just completed cleaning
        if self.dirty_cells <= 0 and self.cleaning_completed_at is None:
            self.cleaning_completed_at = self.current_step
        
        # Check stopping conditions
        if self.current_step >= self.max_time:
            self.running = False
            self._print_final_metrics()
        
        if self.dirty_cells <= 0:
            self.running = False
            self._print_final_metrics()
        
        # Check if all agents have no battery and are not at charging station
        all_agents_dead = True
        for agent in self.agents:
            if isinstance(agent, CleanerAgent):
                at_station = any(isinstance(a, ChargingStationAgent) 
                               for a in agent.cell.agents)
                if agent.battery > 0 or at_station:
                    all_agents_dead = False
                    break
        
        if all_agents_dead:
            self.running = False
            self._print_final_metrics()

    def _print_final_metrics(self):
        """Print the 3 required metrics when simulation ends"""
        stats = self.get_statistics()
        print("\n" + "="*70)
        print("📊 MÉTRICAS FINALES REQUERIDAS")
        print("="*70)
        print(f"\n1. ⏱️  Tiempo necesario hasta que todas las celdas estén limpias:")
        print(f"   {stats['completion_time']} pasos")
        print(f"\n2. ✨ Porcentaje de celdas limpias después del término:")
        print(f"   {stats['clean_percentage']:.2f}%")
        print(f"\n3. 🚶 Número de movimientos realizados por los agentes:")
        print(f"   Total: {stats['total_moves']} movimientos")
        print(f"\n   Movimientos por agente:")
        for agent_stat in stats['agent_statistics']:
            print(f"   - Agente {agent_stat['agent_id']}: {agent_stat['moves']} movimientos")
        print(f"\n{'='*70}\n")

    def get_statistics(self):
        """Returns statistics about the simulation"""

        ##Total moves of all agents
        total_moves = sum(agent.moves for agent in self.agents 
                         if isinstance(agent, CleanerAgent))
        
        ##Total cleaned cells
        total_cleaned = sum(agent.cleaned_cells for agent in self.agents 
                           if isinstance(agent, CleanerAgent))
        
        ##Clean percentage
        clean_percentage = ((self.initial_dirty_cells - self.dirty_cells) / 
                          self.initial_dirty_cells * 100) if self.initial_dirty_cells > 0 else 100
        
        # Get individual agent statistics
        agent_stats = []
        for agent in self.agents:
            if isinstance(agent, CleanerAgent):
                agent_stats.append({
                    "agent_id": agent.unique_id,
                    "moves": agent.moves,
                    "cleaned_cells": agent.cleaned_cells,
                    "battery": agent.battery,
                })
        
        return {
            "mode": "Multi-Agent" if self.multi_agent_mode else "Single Agent",
            "num_agents": self.num_agents,
            "steps": self.current_step,
            "completion_time": self.cleaning_completed_at if self.cleaning_completed_at else self.current_step,
            "dirty_cells_remaining": self.dirty_cells,
            "initial_dirty_cells": self.initial_dirty_cells,
            "total_moves": total_moves,
            "total_cleaned": total_cleaned,
            "clean_percentage": clean_percentage,
            "agent_statistics": agent_stats,
        }