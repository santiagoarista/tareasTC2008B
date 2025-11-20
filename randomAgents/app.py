from random_agents.agent import CleanerAgent, ObstacleAgent, DirtyCellAgent, ChargingStationAgent
from random_agents.model import CleaningModel

from mesa.visualization import (
    Slider,
    SolaraViz,
    make_space_component,
    make_plot_component,
)

from mesa.visualization.components import AgentPortrayalStyle

##Rendering for agents
def agent_portrayal(agent):
    if agent is None:
        return
    
    ##Cleaner agents
    if isinstance(agent, CleanerAgent):
        # Color based on battery level
        if agent.battery > 50: ##If the battery is bigger than 50 the Cleaner Agent will be green
            color = "green"
        elif agent.battery > 20: ##If the battery is bigger than 20 the Cleaner Agent will be yellow
            color = "yellow"
        else: ##Lower will be orange
            color = "orange"
        
        return AgentPortrayalStyle(
            color=color,
            marker="o",  # Circle marker -- Asked Claude for marker parameter.
            size=80,
            zorder=3,  # Draw on top
        )
    
    ##Obstacle Agents
    elif isinstance(agent, ObstacleAgent):
        return AgentPortrayalStyle(
            color="gray",
            marker="s",
            size=100,
            zorder=1,
        )
        
    ##Dirty/Clean Agents
    elif isinstance(agent, DirtyCellAgent):
        if agent.is_dirty: ##If dirty color will be brown
            return AgentPortrayalStyle(
                color="brown",
                marker="s",
                size=100,
                zorder=0,
            )
        else:
            # Clean cells - lightblue
            return AgentPortrayalStyle(
                color="lightblue",
                marker="s",
                size=100,
                alpha=0.2,
                zorder=0,
            )
            
    elif isinstance(agent, ChargingStationAgent):
        return AgentPortrayalStyle(
            color="blue",
            marker="s",
            size=100,
            zorder=2,
        )

#Graphic
def post_process_space(ax):
    ax.set_aspect("equal")

def post_process_lines(ax):
    ax.legend(loc="center left", bbox_to_anchor=(1, 0.9))


##Some adjustable params for the model
model_params = {
    "seed": {
        "type": "InputText",
        "value": 42,
        "label": "Random Seed",
    },
    "multi_agent_mode": {
        "type": "Select",
        "values": [False, True],
        "value": False,
        "label": "Multi-Agent Mode (True = Random positions, False = Single station at [1,1])",
    },
    "num_agents": Slider("Number of cleaning agents", 5, 1, 20),
    "width": Slider("Grid width", 20, 10, 50),
    "height": Slider("Grid height", 20, 10, 50),
    "dirty_percentage": Slider("Dirty cells percentage", 30, 0, 80),
    "obstacle_percentage": Slider("Obstacle percentage", 10, 0, 30),
    "max_time": Slider("Max simulation time", 1000, 100, 5000, step=100),
}

# Create the model using the initial parameters from the settings
model = CleaningModel(
    num_agents=model_params["num_agents"].value,
    width=model_params["width"].value,
    height=model_params["height"].value,
    dirty_percentage=model_params["dirty_percentage"].value,
    obstacle_percentage=model_params["obstacle_percentage"].value,
    max_time=model_params["max_time"].value,
    multi_agent_mode=model_params["multi_agent_mode"]["value"],
    seed=model_params["seed"]["value"]
)

space_component = make_space_component(
    agent_portrayal,
    draw_grid=True,
    post_process=post_process_space
)

# Line plot showing cleaning progress and metrics
lineplot_component = make_plot_component(
    {
        "Clean Percentage": "green",
        "Dirty Cells": "red",
        "Total Moves": "blue",
    },
    post_process=post_process_lines,
)

page = SolaraViz(
    model,
    components=[space_component, lineplot_component],
    model_params=model_params,
    name="Cleaning Agents Simulation",
)
