
import pandas as pd
import os

data_dir = "c:\\POC\\COA_Agent_Platform_Ref\\data_lake"

def check():
    mapping_path = os.path.join(data_dir, "방책유형_위협유형_관련성.xlsx")
    df = pd.read_excel(mapping_path)
    print("Mapping Table Columns:", df.columns.tolist())
    print("\nSample Data:")
    print(df.head(2))

if __name__ == "__main__":
    check()
