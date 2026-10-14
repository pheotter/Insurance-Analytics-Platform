import pandas as pd
import numpy as np
import chainladder as cl

# print("pandas: " + pd.__version__)
# print("numpy: " + np.__version__)
# print("chainladder: " + cl.__version__)

raa_df = pd.read_csv(
    "https://raw.githubusercontent.com/casact/chainladder-python/master/chainladder/utils/data/raa.csv"
)
raa = cl.Triangle(
    raa_df,
    origin="origin",
    development="development",
    columns="values",
    cumulative=True,
)
# print(raa_df.head(30))
# print(raa)
# print(raa.link_ratio)
# print(raa.latest_diagonal)
# print("Origin grain:", raa.origin_grain)
# print("Development grain:", raa.development_grain)

clrd_df = pd.read_csv(
    "https://raw.githubusercontent.com/casact/chainladder-python/master/chainladder/utils/data/clrd.csv"
)
clrd = cl.Triangle(
    clrd_df,
    origin="AccidentYear",
    development="DevelopmentYear",
    columns=[
        "IncurLoss",
        "CumPaidLoss",
        "BulkLoss",
        "EarnedPremDIR",
        "EarnedPremCeded",
        "EarnedPremNet",
    ],
    index=["GRNAME", "LOB"],
    cumulative=True,
)
print(clrd[clrd.origin == clrd.origin.max()])
