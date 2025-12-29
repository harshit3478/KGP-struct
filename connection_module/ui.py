# connection_module/ui.py
import tkinter as tk
from tkinter import ttk, messagebox
from backend import BoltDesigner  # Importing your logic

class ConnectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KGP-Struct: Steel Connection Designer (IS 800)")
        self.root.geometry("900x600")
        
        # Initialize Backend Logic
        self.designer = BoltDesigner()

        # --- Layout ---
        # Left Frame: Inputs
        self.input_frame = ttk.LabelFrame(root, text="Design Inputs", padding=20)
        self.input_frame.pack(side="left", fill="y", padx=10, pady=10)

        # Right Frame: Visualization (The "CAD" view)
        self.vis_frame = ttk.LabelFrame(root, text="Generated Blueprint", padding=10)
        self.vis_frame.pack(side="right", expand=True, fill="both", padx=10, pady=10)
        
        self.canvas = tk.Canvas(self.vis_frame, bg="white")
        self.canvas.pack(fill="both", expand=True)

        self.create_inputs()

    def create_inputs(self):
        # 1. Factored Load
        ttk.Label(self.input_frame, text="Factored Load (kN):").pack(anchor="w", pady=(10, 0))
        self.entry_load = ttk.Entry(self.input_frame)
        self.entry_load.insert(0, "100") # Default value
        self.entry_load.pack(fill="x", pady=5)

        # 2. Bolt Diameter (Dropdown)
        ttk.Label(self.input_frame, text="Bolt Diameter (mm):").pack(anchor="w", pady=(10, 0))
        self.combo_dia = ttk.Combobox(self.input_frame, values=["12", "16", "20", "24", "30"])
        self.combo_dia.current(2) # Select 20mm by default
        self.combo_dia.pack(fill="x", pady=5)

        # 3. Plate Thickness
        ttk.Label(self.input_frame, text="Plate Thickness (mm):").pack(anchor="w", pady=(10, 0))
        self.entry_thick = ttk.Entry(self.input_frame)
        self.entry_thick.insert(0, "10")
        self.entry_thick.pack(fill="x", pady=5)

        # Calculate Button
        self.btn_calc = ttk.Button(self.input_frame, text="Design Connection", command=self.run_design)
        self.btn_calc.pack(fill="x", pady=20)

        # Result Labels
        self.lbl_result = ttk.Label(self.input_frame, text="Status: Waiting...", font=("Arial", 10))
        self.lbl_result.pack(anchor="w", pady=10)
        
        self.lbl_details = ttk.Label(self.input_frame, text="", foreground="blue")
        self.lbl_details.pack(anchor="w")

    def run_design(self):
        try:
            # Get Inputs
            load = float(self.entry_load.get())
            dia = int(self.combo_dia.get())
            thick = float(self.entry_thick.get())

            # Call Backend
            result = self.designer.design_connection(load, dia, thick)

            # Update Text UI
            self.lbl_result.config(text=f"Required Bolts: {result['bolts_required']}")
            details = (
                f"Shear Cap: {result['shear_capacity_kn']} kN\n"
                f"Bearing Cap: {result['bearing_capacity_kn']} kN\n"
                f"Pitch: {result['min_pitch_mm']} mm\n"
                f"End Dist: {result['min_end_dist_mm']} mm"
            )
            self.lbl_details.config(text=details)

            # Update Visualization
            self.draw_blueprint(result)

        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers.")

    def draw_blueprint(self, data):
        """
        This function acts as a 'Mini-CAD' engine.
        It draws the plate and bolts dynamically based on the math.
        """
        self.canvas.delete("all") # Clear previous drawing
        
        # Extract Geometry
        n_bolts = data['bolts_required']
        pitch = data['min_pitch_mm']
        end_dist = data['min_end_dist_mm']
        edge_dist = 40 # Standard side edge distance
        dia = data['bolt_diameter']

        # Calculate Plate Dimensions
        # Height = (n-1)*pitch + 2*end_dist
        plate_height = ((n_bolts - 1) * pitch) + (2 * end_dist)
        plate_width = 150 # Fixed width for visual simplicity

        # --- Auto-Zoom Logic ---
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        # Fallback if canvas isn't rendered yet
        if canvas_w < 50: canvas_w = 400
        if canvas_h < 50: canvas_h = 500
        
        # Padding
        padding = 40
        avail_w = canvas_w - (2 * padding)
        avail_h = canvas_h - (2 * padding)
        
        # Calculate Scale to fit
        scale_w = avail_w / plate_width
        scale_h = avail_h / plate_height
        scale = min(scale_w, scale_h)
        
        # Center the drawing
        draw_w = plate_width * scale
        draw_h = plate_height * scale
        
        start_x = (canvas_w - draw_w) / 2
        start_y = (canvas_h - draw_h) / 2

        # Draw Plate (Rectangle)
        # Using grey color to look like steel
        self.canvas.create_rectangle(
            start_x, start_y, 
            start_x + (plate_width * scale), start_y + (plate_height * scale),
            fill="#d3d3d3", outline="black", width=2
        )

        # Draw Bolts (Circles) along the center line
        center_x = start_x + (plate_width / 2) * scale
        
        current_y_mm = end_dist # First bolt is at end_dist
        
        for i in range(n_bolts):
            # Convert mm to pixels
            cy = start_y + (current_y_mm * scale)
            
            # Bolt Radius in pixels
            r = (dia / 2) * scale
            
            # Draw Bolt
            self.canvas.create_oval(
                center_x - r, cy - r,
                center_x + r, cy + r,
                fill="#4a4a4a", outline="black"
            )
            
            # Add Pitch Text (Dimension line logic)
            if i < n_bolts - 1:
                mid_y = cy + (pitch/2)*scale
                self.canvas.create_text(
                    center_x + 50, mid_y, 
                    text=f"{pitch} mm", fill="red", font=("Arial", 8, "bold")
                )
                # Draw little dimension line
                self.canvas.create_line(
                    center_x, cy, center_x + 40, cy, fill="red", dash=(2,2)
                )

            current_y_mm += pitch # Move down by pitch

        # Add Titles
        self.canvas.create_text(start_x, start_y - 20, text="TOP VIEW (Schematic)", anchor="w", font=("Arial", 12, "bold"))
        self.canvas.create_text(start_x, start_y + (plate_height * scale) + 20, 
                                text=f"Total Height: {plate_height} mm", anchor="w", fill="blue")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConnectionApp(root)
    root.mainloop()