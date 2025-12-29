import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from backend import PlasticAnalyzer

class PlasticHingeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KGP-Struct: Plastic Hinge Simulator")
        self.root.geometry("1000x700")
        
        self.analyzer = PlasticAnalyzer()
        self.simulation_data = []
        self.current_step = 0
        self.is_running = False

        # --- Layout ---
        # Top Control Bar
        control_frame = ttk.Frame(root, padding=10)
        control_frame.pack(side="top", fill="x")
        
        ttk.Label(control_frame, text="Max Load (kN):").pack(side="left")
        self.entry_load = ttk.Entry(control_frame, width=10)
        self.entry_load.insert(0, "300")
        self.entry_load.pack(side="left", padx=5)
        
        self.btn_run = ttk.Button(control_frame, text="Run Simulation", command=self.start_simulation)
        self.btn_run.pack(side="left", padx=20)
        
        self.lbl_status = ttk.Label(control_frame, text="Status: Ready", font=("Arial", 12, "bold"))
        self.lbl_status.pack(side="left", padx=20)

        # Graph Area
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(-2, 2)
        self.ax.set_xlim(-1, 11)
        self.ax.set_title("Beam Deformation & Hinge Formation")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def start_simulation(self):
        max_load = float(self.entry_load.get())
        # Run backend calculation first
        self.simulation_data = self.analyzer.run_simulation(max_load=max_load)
        
        # Calculate Dynamic Limits
        # Find max deflection magnitude
        max_def = 0
        for step in self.simulation_data:
            if abs(step['deflection']) > max_def:
                max_def = abs(step['deflection'])
        
        # Scale factor used in drawing is 50
        scaled_max_def = max_def * 50 
        
        # Set limits: Top is fixed at 2 (beam starts at 0), Bottom needs to accommodate deflection
        # Add 20% padding
        bottom_limit = -(scaled_max_def * 1.2)
        # Ensure it's at least -2 so we don't zoom in too much on small deflections
        if bottom_limit > -2: bottom_limit = -2
        
        self.y_limits = (bottom_limit, 2)

        self.current_step = 0
        self.is_running = True
        self.animate()

    def animate(self):
        if not self.is_running or self.current_step >= len(self.simulation_data):
            self.is_running = False
            return

        data = self.simulation_data[self.current_step]
        
        # CLEAR CHART
        self.ax.clear()
        
        # Apply Dynamic Limits
        if hasattr(self, 'y_limits'):
            self.ax.set_ylim(self.y_limits[0], self.y_limits[1])
        else:
            self.ax.set_ylim(-5, 2)
            
        self.ax.set_xlim(-1, 11)
        self.ax.set_xlabel("Span (m)")
        self.ax.set_ylabel("Deflection (scaled)")
        
        # DRAW BEAM (Deformed Shape)
        # Simple quadratic curve for visualization
        x = np.linspace(0, 10, 50)
        # y = max_deflection * shape_function
        # shape function for fixed beam is roughly sin^2
        deflection_scale = data['deflection'] * 50 # Exaggerate for visibility
        y = -deflection_scale * (np.sin(x * np.pi / 10)**2)
        
        self.ax.plot(x, y, color='blue', linewidth=3, label='Beam')
        self.ax.axhline(0, color='black', linestyle='--', alpha=0.3) # Neutral axis

        # DRAW SUPPORTS
        self.ax.plot([0], [0], marker='s', markersize=10, color='black') # Left Fixed
        self.ax.plot([10], [0], marker='s', markersize=10, color='black') # Right Fixed

        # DRAW HINGES (If any)
        # Hinges appear as Red Circles
        if data['status'] == "COLLAPSE (Mechanism Formed)":
            # Draw hinges at ends and center
            self.ax.plot([0], [0], marker='o', markersize=15, color='red', label='Plastic Hinge')
            self.ax.plot([10], [0], marker='o', markersize=15, color='red')
            # Center hinge follows deflection
            center_y = y[25] 
            self.ax.plot([5], [center_y], marker='o', markersize=15, color='red')
            
            self.lbl_status.config(text=f"Load: {data['load']:.1f} kN | COLLAPSE!", foreground="red")
        else:
            self.lbl_status.config(text=f"Load: {data['load']:.1f} kN | Elastic", foreground="green")

        self.ax.legend()
        self.canvas.draw()
        
        # Loop
        self.current_step += 1
        self.root.after(100, self.animate) # 100ms delay between frames

if __name__ == "__main__":
    root = tk.Tk()
    app = PlasticHingeApp(root)
    root.mainloop()