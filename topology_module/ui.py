# topology_module/ui.py
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from backend import TopologyOptimizer

class TopologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KGP-Struct: Topology Optimizer (Iterative BESO)")
        self.root.geometry("1200x800")
        
        self.optimizer = TopologyOptimizer()
        self.is_running = False
        self.iteration = 0

        # --- Layout ---
        # 1. Engineering Inputs (Left Panel)
        input_frame = ttk.LabelFrame(root, text="Design Parameters", padding=10)
        input_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Geometry
        self.add_entry(input_frame, "Span (m):", "16", "ent_span")
        self.add_entry(input_frame, "Height (m):", "5", "ent_height")
        self.add_entry(input_frame, "Load (kN):", "800", "ent_load")

        # Material
        ttk.Separator(input_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(input_frame, text="Material (Steel)", font=("Arial", 10, "bold")).pack(anchor="w")
        self.add_entry(input_frame, "Young's Modulus (GPa):", "200", "ent_E")

        # Section (I-Beam)
        ttk.Separator(input_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(input_frame, text="I-Section Properties", font=("Arial", 10, "bold")).pack(anchor="w")
        self.add_entry(input_frame, "Flange Width (mm):", "150", "ent_B")
        self.add_entry(input_frame, "Total Depth (mm):", "300", "ent_D")
        self.add_entry(input_frame, "Web Thick (mm):", "8", "ent_tw")
        self.add_entry(input_frame, "Flange Thick (mm):", "12", "ent_tf")

        # Supports
        ttk.Separator(input_frame, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(input_frame, text="Support Conditions:", font=("Arial", 10)).pack(anchor="w")
        self.combo_support = ttk.Combobox(input_frame, values=["Pinned-Roller", "Fixed-Fixed", "Pinned-Pinned"])
        self.combo_support.current(0)
        self.combo_support.pack(fill="x", pady=5)

        # Controls
        ttk.Separator(input_frame, orient="horizontal").pack(fill="x", pady=20)
        self.btn_start = ttk.Button(input_frame, text="RUN OPTIMIZATION", command=self.start_optimization)
        self.btn_start.pack(fill="x", pady=5)
        
        self.btn_stop = ttk.Button(input_frame, text="STOP", command=self.stop_optimization)
        self.btn_stop.pack(fill="x", pady=5)

        self.lbl_status = ttk.Label(input_frame, text="Ready", foreground="grey")
        self.lbl_status.pack(pady=20)

        # 2. Visualization (Right Panel)
        vis_frame = ttk.LabelFrame(root, text="Evolutionary Process", padding=10)
        vis_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)

        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_aspect('equal')
        self.ax.axis('off')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=vis_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def add_entry(self, parent, label, default, var_name):
        ttk.Label(parent, text=label).pack(anchor="w", pady=(5, 0))
        entry = ttk.Entry(parent)
        entry.insert(0, default)
        entry.pack(fill="x", pady=(0, 5))
        setattr(self, var_name, entry)

    def start_optimization(self):
        try:
            # Gather Inputs
            span = float(self.ent_span.get())
            height = float(self.ent_height.get())
            load = float(self.ent_load.get()) * 1000 # Convert to N
            E = float(self.ent_E.get())
            
            # Section (Convert mm to m)
            B = float(self.ent_B.get()) / 1000
            D = float(self.ent_D.get()) / 1000
            tw = float(self.ent_tw.get()) / 1000
            tf = float(self.ent_tf.get()) / 1000
            
            support = self.combo_support.get()

            # Initialize
            self.lbl_status.config(text="Initializing Mesh...", foreground="orange")
            # self.root.update() # Removed to prevent potential race conditions/crashes
            
            section_params = {"B": B, "D": D, "tw": tw, "tf": tf}
            
            self.optimizer.initialize_structure(span, height, load, support, E, section_params)
            
            self.is_running = True
            self.iteration = 0
            self.run_loop()
            
        except ValueError:
            messagebox.showerror("Input Error", "Please ensure all fields are numeric.")

    def stop_optimization(self):
        self.is_running = False
        self.lbl_status.config(text="Stopped by User.", foreground="red")

    def run_loop(self):
        if not self.is_running: return

        self.iteration += 1
        
        try:
            # Run one BESO step
            # removal_ratio=0.02 means remove 2% of bars per frame (Slow and smooth)
            display_data, active_count = self.optimizer.run_iteration(self.iteration, removal_ratio=0.02)
            
            # Plot
            self.ax.clear()
            self.ax.axis('off')
            
            # Dynamic Zoom
            span = float(self.ent_span.get())
            height = float(self.ent_height.get())
            self.ax.set_xlim(-1, span + 1)
            self.ax.set_ylim(-1, height + 2)

            # Draw Bars
            for bar in display_data:
                p1 = bar['p1']
                p2 = bar['p2']
                
                if bar['active']:
                    # Active Bar: Blue, thickness based on force
                    force = bar['force']
                    max_f = bar['max_force'] if bar['max_force'] > 0 else 1
                    
                    intensity = force / max_f
                    alpha = 0.5 + 0.5 * intensity
                    lw = 1.0 + 3.0 * intensity
                    
                    self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 
                                 color='#0055ff', linewidth=lw, alpha=alpha, zorder=10)
                else:
                    # Ghost Bar: Faint Grey
                    self.ax.plot([p1[0], p2[0]], [p1[1], p2[1]], 
                                 color='#e0e0e0', linewidth=0.5, alpha=0.5, zorder=1)

            # Draw Supports
            self.ax.plot([0], [0], marker='^', markersize=12, color='black', zorder=20)
            self.ax.plot([span], [0], marker='o', markersize=12, color='black', zorder=20)
            
            # Draw Load
            self.ax.arrow(span/2, height + 1, 0, -0.8, 
                          head_width=0.4, fc='red', ec='red', zorder=20)
            
            self.canvas.draw()
            
            self.lbl_status.config(text=f"Iteration: {self.iteration} | Active Elements: {active_count}", foreground="green")
            
            # Termination Check
            if active_count < 25:
                self.is_running = False
                self.lbl_status.config(text="Optimization Converged.", foreground="blue")
            else:
                # Increase delay to 200ms to prevent UI freeze/crash on macOS
                self.root.after(200, self.run_loop) 

        except Exception as e:
            self.is_running = False
            self.lbl_status.config(text=f"Solver Error: {str(e)}", foreground="red")
            print(f"Error in loop: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TopologyApp(root)
    root.mainloop()