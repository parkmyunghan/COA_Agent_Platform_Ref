import pandas as pd
import os

# Define the data for the COA Library
data = [
    # Defense
    {
        "COA_ID": "COA_DEF_001",
        "명칭": "Main Defense",
        "방책유형": "Defense",
        "설명": "Establish a strong defensive perimeter to repel enemy attacks.",
        "키워드": "defense, perimeter, repel, main",
        "사용조건": "High threat level, sufficient resources"
    },
    {
        "COA_ID": "COA_DEF_002",
        "명칭": "Mobile Defense",
        "방책유형": "Defense",
        "설명": "Utilize mobile forces to counter-attack and disrupt enemy advances.",
        "키워드": "defense, mobile, counter-attack, disrupt",
        "사용조건": "Moderate threat level, high mobility assets"
    },
    # Offensive
    {
        "COA_ID": "COA_OFF_001",
        "명칭": "Main Offensive",
        "방책유형": "Offensive",
        "설명": "Launch a full-scale attack on enemy main forces.",
        "키워드": "offensive, attack, full-scale, main",
        "사용조건": "Superior force ratio, clear intelligence"
    },
    {
        "COA_ID": "COA_OFF_002",
        "명칭": "Limited Offensive",
        "방책유형": "Offensive",
        "설명": "Conduct limited attacks to seize key terrain or disrupt enemy preparations.",
        "키워드": "offensive, limited, seize, disrupt",
        "사용조건": "Limited objectives, specific targets"
    },
    # Counter-attack
    {
        "COA_ID": "COA_CTR_001",
        "명칭": "Counter Attack Alpha",
        "방책유형": "Counter_Attack",
        "설명": "Launch a counter-attack immediately after repelling an enemy assault.",
        "키워드": "counter-attack, immediate, repel",
        "사용조건": "Enemy attack stalled, reserve forces available"
    },
    # Preemptive
    {
        "COA_ID": "COA_PRE_001",
        "명칭": "Preemptive Strike",
        "방책유형": "Preemptive",
        "설명": "Strike enemy forces before they can launch an attack.",
        "키워드": "preemptive, strike, before attack",
        "사용조건": "Imminent threat, actionable intelligence"
    },
    # Deterrence
    {
        "COA_ID": "COA_DET_001",
        "명칭": "Show of Force",
        "방책유형": "Deterrence",
        "설명": "Demonstrate military capability to deter enemy aggression.",
        "키워드": "deterrence, show of force, demonstrate",
        "사용조건": "Rising tension, desire to avoid conflict"
    },
    # Maneuver
    {
        "COA_ID": "COA_MAN_001",
        "명칭": "Flanking Maneuver",
        "방책유형": "Maneuver",
        "설명": "Maneuver forces to the enemy's flank to gain a tactical advantage.",
        "키워드": "maneuver, flank, tactical advantage",
        "사용조건": "Open terrain, mobile forces"
    },
    # Information Ops
    {
        "COA_ID": "COA_INF_001",
        "명칭": "Cyber Disruption",
        "방책유형": "Information_Ops",
        "설명": "Disrupt enemy command and control systems via cyber operations.",
        "키워드": "information ops, cyber, disruption, c2",
        "사용조건": "Cyber capabilities available, vulnerable enemy systems"
    }
]

# Create DataFrame
df = pd.DataFrame(data)

# Define path
output_path = "c:/POC/(NEW)Defense_Intelligent_Agent_Platform/data_lake/COA_Library.xlsx"

# Ensure directory exists
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Save to Excel
try:
    df.to_excel(output_path, index=False)
    print(f"Successfully created {output_path}")
    print(df)
except Exception as e:
    print(f"Error creating file: {e}")
