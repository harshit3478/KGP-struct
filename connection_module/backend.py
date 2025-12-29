# connection_module/backend.py
import math

class BoltDesigner:
    """
    This class encapsulates the logic for IS 800:2007 Bolted Connection Design.
    Focus: Bearing Type Bolts (Standard Black Hex Bolts).
    """

    def __init__(self, grade=4.6):
        # Bolt Grade 4.6 means:
        # Ultimate Tensile Strength (fub) = 4 * 100 = 400 MPa
        # Yield Strength (fyb) = 0.6 * 400 = 240 MPa
        self.fub = 400  # MPa (N/mm^2) - Standard for most buildings
        self.gamma_mb = 1.25  # Partial Safety Factor for material (IS 800 Table 5)

    def get_shear_capacity(self, diameter):
        """
        Calculates Shear Capacity of ONE bolt (Vdsb).
        Concept: The bolt gets sliced.
        Formula: Vdsb = (fub / sqrt(3)) * (nn * Anb + ns * Asb) / Gamma_mb
        """
        # Anb = Net Area (threaded part) approx 0.78 of gross area
        Anb = 0.78 * (math.pi * diameter**2 / 4)
        
        # Nominal Shear Capacity (Vnsb)
        # We assume single shear plane (one slice) passes through threads (conservative)
        f_u = self.fub
        Vnsb = (f_u / math.sqrt(3)) * Anb 
        
        # Design Capacity (divide by safety factor)
        Vdsb = Vnsb / self.gamma_mb
        return Vdsb / 1000  # Convert Newton to kN

    def get_bearing_capacity(self, diameter, thickness_plate, end_distance, pitch_distance):
        """
        Calculates Bearing Capacity of ONE bolt (Vdpb).
        Concept: The bolt tears the plate.
        Formula: Vdpb = 2.5 * kb * d * t * fu / Gamma_mb
        """
        d0 = diameter + 2  # Hole diameter (Standard clearance is +2mm for M16-M24)
        fu_plate = 410     # Standard Structural Steel (Fe410) Ultimate Strength
        
        # kb is a coefficient that checks different failure modes (tearing vs shearing)
        # kb is smallest of:
        # 1. e / (3 * d0)        <-- Checking if hole is too close to edge
        # 2. p / (3 * d0) - 0.25 <-- Checking if holes are too close to each other
        # 3. fub / fu            <-- Bolt strength vs Plate strength
        # 4. 1.0
        
        kb_1 = end_distance / (3.0 * d0)
        kb_2 = (pitch_distance / (3.0 * d0)) - 0.25
        kb_3 = self.fub / fu_plate
        kb_4 = 1.0

        kb = min(kb_1, kb_2, kb_3, kb_4)

        # Nominal Bearing Capacity
        Vnpb = 2.5 * kb * diameter * thickness_plate * fu_plate
        
        # Design Capacity
        Vdpb = Vnpb / self.gamma_mb
        return Vdpb / 1000 # Convert to kN

    def design_connection(self, load_kn, diameter, plate_thickness):
        """
        The Main Logic:
        1. Calculate capacities.
        2. Determine number of bolts.
        3. Check IS code spacing rules.
        """
        # IS 800 Minimum Spacing Rules
        min_pitch = 2.5 * diameter
        min_end_dist = 1.5 * (diameter + 2) # 1.5 * hole_diameter for rolled edge
        
        # Let's assume we use minimum safe distances for optimal design
        # In a real app, user might input these, but auto-calculating is "Smart"
        pitch = math.ceil(min_pitch / 5) * 5       # Round up to nearest 5mm
        end_dist = math.ceil(min_end_dist / 5) * 5 # Round up to nearest 5mm

        # 1. Get Bolt Strength
        shear_cap = self.get_shear_capacity(diameter)
        bearing_cap = self.get_bearing_capacity(diameter, plate_thickness, end_dist, pitch)
        
        # The bolt is only as strong as its weakest link
        bolt_value = min(shear_cap, bearing_cap)

        # 2. Calculate Number of Bolts
        num_bolts = math.ceil(load_kn / bolt_value)

        return {
            "status": "Success",
            "bolt_diameter": diameter,
            "shear_capacity_kn": round(shear_cap, 2),
            "bearing_capacity_kn": round(bearing_cap, 2),
            "bolt_value_kn": round(bolt_value, 2),
            "bolts_required": num_bolts,
            "min_pitch_mm": pitch,
            "min_end_dist_mm": end_dist,
            "critical_failure": "Shear" if shear_cap < bearing_cap else "Bearing"
        }

# --- Quick Test Block (To verify logic) ---
if __name__ == "__main__":
    designer = BoltDesigner()
    # Scenario: 100kN load, M20 bolts, 10mm thick plate
    result = designer.design_connection(load_kn=100, diameter=20, plate_thickness=10)
    print(result)