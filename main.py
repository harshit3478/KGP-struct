import tkinter as tk
from tkinter import ttk
import os
import sys
import subprocess

class KGPStructLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("KGP-Struct: Integrated Design Suite (BTP 2025)")
        # give it dark blue color
        # self.root.configure(bg="#2c3e50")
        self.root.geometry("600x400")
        
        # Header
        lbl_title = tk.Label(root, text="KGP-Struct", font=("Helvetica", 24, "bold"), fg="#4b9ef2")
        lbl_title.pack(pady=(30, 10))
        
        lbl_subtitle = tk.Label(root, text="Advanced Structural Analysis & Design Toolkit", font=("Helvetica", 12))
        lbl_subtitle.pack(pady=(0, 30))

        # Buttons Frame
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        # Module 1
        btn_1 = ttk.Button(btn_frame, text="1. Steel Connection Automator (IS 800)", command=self.launch_mod_1, width=40)
        btn_1.pack(pady=10, ipady=5)

        # Module 2
        btn_2 = ttk.Button(btn_frame, text="2. Plastic Hinge Simulator (Non-Linear)", command=self.launch_mod_2, width=40)
        btn_2.pack(pady=10, ipady=5)
        
        # Module 3
        btn_3 = ttk.Button(btn_frame, text="3. Topology Optimizer (Research)", command=self.launch_mod_3, width=40)
        btn_3.pack(pady=10, ipady=5)

        # Footer
        tk.Label(root, text="Developed by Harshit Agarwal | Dept. of Civil Engineering, IIT Kharagpur", 
                 font=("Arial", 9), fg="gray").pack(side="bottom", pady=20)

    def launch_mod_1(self):
        self.run_script("connection_module/ui.py")

    def launch_mod_2(self):
        self.run_script("plastic_hinge_module/ui.py")

    def launch_mod_3(self):
        self.run_script("topology_module/ui.py")

    def run_script(self, relative_path):
        # Logic to find the script path relative to this main.py
        base_path = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_path, relative_path)
        
        # Launch as separate process
        subprocess.Popen([sys.executable, script_path])

if __name__ == "__main__":
    root = tk.Tk()
    app = KGPStructLauncher(root)
    root.mainloop()