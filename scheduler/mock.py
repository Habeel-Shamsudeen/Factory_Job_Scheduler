from core.models import Model, Assignment
from typing import List

assignments = [
    # ==========================================
    # RESOURCE: Fill-1
    # ==========================================
    Assignment(product="P-102", step_index=1, capability="fill", resource="Fill-1", start=0,  end=25),  # standard
    # CHANGEOVER: 25 to 45
    Assignment(product="P-103", step_index=1, capability="fill", resource="Fill-1", start=45, end=75),  # premium

    # ==========================================
    # RESOURCE: Fill-2
    # ==========================================
    Assignment(product="P-100", step_index=1, capability="fill", resource="Fill-2", start=0,  end=30),  # standard
    # CHANGEOVER: 30 to 50
    Assignment(product="P-101", step_index=1, capability="fill", resource="Fill-2", start=50, end=85),  # premium

    # ==========================================
    # RESOURCE: Label-1
    # ==========================================
    Assignment(product="P-100", step_index=2, capability="label", resource="Label-1", start=30,  end=50),  # standard
    Assignment(product="P-102", step_index=2, capability="label", resource="Label-1", start=50,  end=70),  # standard
    # CHANGEOVER: 70 to 90
    Assignment(product="P-103", step_index=2, capability="label", resource="Label-1", start=90,  end=110), # premium
    Assignment(product="P-101", step_index=2, capability="label", resource="Label-1", start=110, end=135), # premium

    # ==========================================
    # RESOURCE: Pack-1
    # ==========================================
    Assignment(product="P-100", step_index=3, capability="pack", resource="Pack-1", start=50,  end=65),  # standard
    # Idle/Changeover wait: 65 to 110 (Waiting for Label-1 to finish P-103)
    Assignment(product="P-103", step_index=3, capability="pack", resource="Pack-1", start=110, end=125), # premium
    # Idle wait: 125 to 135 (Waiting for Label-1 to finish P-101)
    Assignment(product="P-101", step_index=3, capability="pack", resource="Pack-1", start=135, end=150), # premium
]

def schedule_mock(model: Model) -> List[Assignment]:
    return assignments