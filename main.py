from ui.main_window import MainApplication
from models.simulation import Simulation  # Chỉ import class, không import instance

def main():
    # Tạo instance mới của Simulation
    simulation = Simulation()
    
    # Truyền simulation vào MainApplication
    app = MainApplication(simulation)
    app.mainloop()

if __name__ == "__main__":
    main()