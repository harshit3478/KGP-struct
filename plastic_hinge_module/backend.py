# plastic_hinge_module/backend.py
from anastruct import SystemElements
import copy

class PlasticAnalyzer:
    def __init__(self, span_length=10, yield_moment=150):
        """
        span_length: Length of the beam in meters
        yield_moment (Mp): The max moment the beam can take before yielding (kNm)
        """
        self.L = span_length
        self.Mp = yield_moment
        
    def run_simulation(self, max_load=200, steps=20):
        results = []
        load_increment = max_load / steps
        
        for step in range(steps + 1):
            current_load = step * load_increment
            
            # --- FIX STARTS HERE ---
            # If load is 0, simply record zero results and skip the solver
            if current_load == 0:
                results.append({
                    "load": 0.0,
                    "max_moment": 0.0,
                    "deflection": 0.0,
                    "hinges": [],
                    "status": "Elastic"
                })
                continue
            # --- FIX ENDS HERE ---

            # 1. Build the Structure fresh every time
            ss = SystemElements(EA=15000, EI=5000) 
            mid_L = self.L / 2
            
            # Split beam into two elements so we have a center node (Node 2)
            ss.add_element(location=[[0, 0], [mid_L, 0]])      
            ss.add_element(location=[[mid_L, 0], [self.L, 0]]) 
            
            ss.add_support_fixed(node_id=1) 
            ss.add_support_fixed(node_id=3) 
            
            # Apply Load at Center (Node 2)
            ss.point_load(node_id=2, Fy=-current_load)
            
            # Solve
            ss.solve()
            
            # 2. Check for Plastic Hinges (Theoretical Validation)
            hinges = []
            m_theoretical = (current_load * self.L) / 8
            
            if m_theoretical >= self.Mp:
                hinges.append((0,0))       # Left Support
                hinges.append((self.L, 0)) # Right Support
                hinges.append((mid_L, 0))  # Center
            
            # 3. Store Data
            status = "Elastic"
            if m_theoretical >= self.Mp:
                status = "COLLAPSE (Mechanism Formed)"
            elif m_theoretical >= self.Mp * 0.6:
                status = "Yielding"
                
            results.append({
                "load": current_load,
                "max_moment": m_theoretical,
                # Theoretical deflection for fixed beam: PL^3 / 192EI
                "deflection": (current_load * self.L**3) / (192 * 5000), 
                "hinges": hinges,
                "status": status
            })
            
        return results

if __name__ == "__main__":
    analyzer = PlasticAnalyzer()
    data = analyzer.run_simulation()
    print(f"Simulation Steps: {len(data)}")
    print(f"Final State: {data[-1]['status']}")