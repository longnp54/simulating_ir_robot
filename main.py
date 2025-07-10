from ui.main_window import MainApplication
from models.simulation import Simulation  

def main():
    # Create new instance of Simulation
    simulation = Simulation()
    
    # Pass simulation to MainApplication
    app = MainApplication(simulation)
    app.mainloop()

if __name__ == "__main__":
    main()