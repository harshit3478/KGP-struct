# topology_module/backend.py
from anastruct import SystemElements
import itertools
import math

class TopologyOptimizer:
    def __init__(self):
        self.ss = None
        self.elements_metadata = [] # Stores {id, p1, p2, active, mirror_id}
        self.load_node_id = None
        
        # Default Material (Steel)
        self.E_active = 200e9   # 200 GPa (Active)
        self.E_passive = 1.0    # ~0 GPa (Deleted/Ghost)

    def calculate_i_section_properties(self, B, D, tw, tf):
        """
        Calculates Area (A) and Moment of Inertia (I) for a symmetrical I-section.
        All inputs in meters.
        """
        # Area
        area = (2 * B * tf) + ((D - 2 * tf) * tw)
        
        # Inertia (Ixx) - Standard Formula
        # Outer rectangle minus inner rectangles
        Ixx = (1/12) * (B * D**3) - (1/12) * ((B - tw) * (D - 2*tf)**3)
        
        return area, Ixx

    def initialize_structure(self, span, height, load_kn, support_type, 
                             E_GPa, section_params):
        """
        Sets up the Ground Structure with real physics properties.
        section_params: {B, D, tw, tf}
        """
        # 1. Calculate Properties
        A, I = self.calculate_i_section_properties(**section_params)
        self.E_active = E_GPa * 1e9 # Convert GPa to Pa
        
        # Initialize System (Using Frame Elements for stability)
        # We start with EA and EI based on active material
        EA = self.E_active * A
        EI = self.E_active * I
        
        self.ss = SystemElements(EA=EA, EI=EI)
        self.elements_metadata = []

        # 2. Generate Grid Nodes
        x_divs = 8  # Higher resolution for better symmetry
        y_divs = 3
        nodes = []
        dx = span / x_divs
        dy = height / y_divs

        for i in range(x_divs + 1):
            for j in range(y_divs + 1):
                nodes.append([round(i * dx, 3), round(j * dy, 3)])

        # 3. Connect Nodes (Ground Structure)
        max_dist = dx * 1.6
        
        # We add elements and store their geometric data
        # We use a set to avoid duplicate bars
        added_connections = set()
        
        for p1, p2 in itertools.combinations(nodes, 2):
            dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            
            # Check length constraint
            if 1e-3 < dist <= max_dist:
                
                # Add to anastruct
                # Frame element ID starts at 1
                self.ss.add_element(location=[p1, p2])
                el_id = len(self.ss.element_map)
                
                # Store Metadata
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2
                
                self.elements_metadata.append({
                    "id": el_id,
                    "p1": p1,
                    "p2": p2,
                    "mid_x": mid_x,
                    "mid_y": mid_y,
                    "length": dist,
                    "active": True,
                    "strain_energy": 0.0
                })

        # 4. Map Symmetry (The "Mirror" Logic)
        # We link every element on the Left to its twin on the Right
        center_line = span / 2
        
        for el in self.elements_metadata:
            if el["mid_x"] < center_line:
                # This is a left-side element. Find its right-side twin.
                # Twin active center should be at (Span - mid_x)
                target_x = span - el["mid_x"]
                target_y = el["mid_y"]
                
                # Search for twin
                best_twin = None
                min_error = float('inf')
                
                for potential in self.elements_metadata:
                    if potential["mid_x"] > center_line:
                        err = math.hypot(potential["mid_x"] - target_x, potential["mid_y"] - target_y)
                        if err < 0.1: # Tolerance
                            min_error = err
                            best_twin = potential["id"]
                            break
                
                el["mirror_id"] = best_twin
            else:
                el["mirror_id"] = None # Right side or center elements don't need to look

        # 5. Apply Supports
        # Find node IDs
        def get_nid(x, y):
            best = None
            md = float('inf')
            for nid, n in self.ss.node_map.items():
                d = math.hypot(n.vertex.x - x, n.vertex.y - y)
                if d < md:
                    md = d
                    best = nid
            return best

        id_L = get_nid(0, 0)
        id_R = get_nid(span, 0)

        if support_type == "Pinned-Roller":
            self.ss.add_support_hinged(node_id=id_L)
            self.ss.add_support_roll(node_id=id_R)
        elif support_type == "Fixed-Fixed":
            self.ss.add_support_fixed(node_id=id_L)
            self.ss.add_support_fixed(node_id=id_R)
        elif support_type == "Pinned-Pinned":
            self.ss.add_support_hinged(node_id=id_L)
            self.ss.add_support_hinged(node_id=id_R)

        # 6. Apply Load
        self.load_node_id = get_nid(span / 2, height)
        self.ss.point_load(node_id=self.load_node_id, Fy=-load_kn)

    def run_iteration(self, iteration_num, removal_ratio=0.02):
        """
        1. Solve.
        2. Calculate Strain Energy.
        3. Average Energy with Mirror.
        4. Soft Kill lowest energy pairs.
        """
        # A. Solve
        self.ss.solve()
        
        # B. Calculate Strain Energy for Active Elements
        # SE = (F^2 * L) / (2 * A * E)
        # Since A and E are constant for the active set, SE is proportional to (F^2 * L)
        # For simplicity in ranking, we use Energy_Factor = F^2 * L
        
        active_list = [el for el in self.elements_metadata if el["active"]]
        
        total_system_energy = 0.0
        max_force_iter = 0.0
        
        for el in active_list:
            res = self.ss.get_element_results(element_id=el["id"])
            
            # Get Force (Robust)
            raw_n = res.get('N', 0)
            
            if raw_n is None:
                # If N is None, it might be constant, check Nmin/Nmax
                n_min = res.get('Nmin', 0)
                n_max = res.get('Nmax', 0)
                if n_min is None: n_min = 0
                if n_max is None: n_max = 0
                force = max(abs(n_min), abs(n_max))
            elif isinstance(raw_n, list):
                # Frame elements return a list of forces along the beam.
                # We take the max absolute value to represent the element's stress.
                valid_forces = [abs(x) for x in raw_n if x is not None]
                force = max(valid_forces) if valid_forces else 0.0
            else:
                force = abs(raw_n)
            
            # Store Force for display
            el["force_val"] = force
            if force > max_force_iter: max_force_iter = force
            
            # Calculate Energy Factor
            energy = (force ** 2) * el["length"]
            el["strain_energy"] = energy
            total_system_energy += energy

        # C. Enforce Symmetry (Average Energies)
        for el in active_list:
            if el["mirror_id"] is not None:
                # Find the twin object
                twin = next((x for x in self.elements_metadata if x["id"] == el["mirror_id"]), None)
                if twin and twin["active"]:
                    avg_energy = (el["strain_energy"] + twin["strain_energy"]) / 2
                    el["strain_energy"] = avg_energy
                    twin["strain_energy"] = avg_energy

        # D. Identify Weakest
        # Sort by Energy (Low to High)
        active_list.sort(key=lambda x: x["strain_energy"])
        
        # Calculate how many to remove
        count_to_remove = int(len(active_list) * removal_ratio)
        
        # Fix: Ensure at least 1 element is removed if we are above the safety threshold
        # Otherwise, 2% of 48 is 0.96 -> 0, and optimization stalls.
        if count_to_remove < 1:
            count_to_remove = 1
        
        # Safety: Don't go below 10 elements
        if len(active_list) < 15:
            count_to_remove = 0

        # E. Soft Kill (Update Stiffness)
        # We need the Area/Inertia ratio to scale them down
        # We just access the current values and divide by large number
        
        for i in range(count_to_remove):
            target_el = active_list[i]
            target_el["active"] = False
            
            # Soft Kill in Anastruct
            # We actively modify the element map
            anastruct_el = self.ss.element_map[target_el["id"]]
            anastruct_el.EA = anastruct_el.EA * 1e-6 # Reduce by factor of million
            anastruct_el.EI = anastruct_el.EI * 1e-6

            # Kill Twin as well (redundant but safe)
            if target_el["mirror_id"]:
                twin = next((x for x in self.elements_metadata if x["id"] == target_el["mirror_id"]), None)
                if twin and twin["active"]:
                    twin["active"] = False
                    twin_el = self.ss.element_map[twin["id"]]
                    twin_el.EA = twin_el.EA * 1e-6
                    twin_el.EI = twin_el.EI * 1e-6

        # F. Return Data for Plotting
        display_data = []
        max_f_active = 0
        
        for el in self.elements_metadata:
            if el["active"]:
                 if el["force_val"] > max_f_active: max_f_active = el["force_val"]

        # LOGGING
        print(f"[Iter {iteration_num:03d}] Active: {len(active_list):03d} | Removed: {count_to_remove:02d} | Max Force: {max_force_iter/1000:.2f} kN | Total Energy: {total_system_energy:.2e}")

        for el in self.elements_metadata:
            display_data.append({
                "p1": el["p1"],
                "p2": el["p2"],
                "active": el["active"],
                "force": el.get("force_val", 0),
                "max_force": max_f_active
            })
            
        return display_data, len(active_list) - count_to_remove