import re
import os
import time

import numpy as np
import pandas as pd
import geopandas as gpd

from glob import glob
from pathlib import Path

anchor = Path(__file__).parent

OUTPUT_DIR = anchor / Path("export")
MAP_DATA_PATH = anchor / Path("geo/ne_110m_admin_0_countries/ne_110m_admin_0_countries.dbf")
CRYPTO_DATA_PATH = anchor / Path("../data/countries")
USE_DUMMY_DATA = False

# initialize output dir
os.makedirs(OUTPUT_DIR, exist_ok=True)

timestamp = time.strftime("%Y%m%d")

# load world map data

gdf = gpd.read_file(MAP_DATA_PATH)

gdf = gdf[["NAME_EN", "ISO_A2_EH", "geometry"]]
gdf = gdf.set_index(gdf["ISO_A2_EH"].values, drop=False)

# delete countries without alpha 2 ISO code
gdf.drop(gdf[gdf["ISO_A2_EH"] == "-99"].index, inplace=True)

gdf["crypto_export"] = "unknown"
gdf["crypto_import"] = "unknown"

def valid_token(string):
    return string in {"unknown", "relaxed", "medium", "strict"}


def parse_crypto_md(filename):
    with open(filename) as f:
        block = False
        alpha2, export_reg, import_reg = None, None, None
        for line in f:
            line = line.strip().lower()

            if block:
                if line.startswith("alpha2"):
                    alpha2 = line.split(":")[-1].strip().upper()

                if line.startswith("export"):
                    export_reg = line.split(":")[-1].strip().lower()

                if line.startswith("import"):
                    import_reg = line.split(":")[-1].strip().lower()
                    
                if line.startswith("#"):
                    block = False

            if re.match(r"^#+\s+summary", line):
                block = True

        export_reg = export_reg if valid_token(export_reg) else "unknown"
        import_reg = import_reg if valid_token(import_reg) else "unknown"

        if alpha2:
            return alpha2, export_reg, import_reg


if USE_DUMMY_DATA:
    gdf[["crypto_export", "crypto_import"]] = np.random.choice(
        ["unknown", "relaxed", "medium", "strict"], 
        size=(gdf.shape[0], 2)
    )

else:
    for filename in glob(str(CRYPTO_DATA_PATH / "*.md")):
        filename = Path(filename)

        try:
            alpha2, export_reg, import_reg = parse_crypto_md(filename)
            gdf.loc[alpha2, "crypto_export"] = export_reg
            gdf.loc[alpha2, "crypto_import"] = import_reg

        except TypeError:
            print(f"could not extract tags from {filename.resolve()}")

        except KeyError:
            print(f"could not identify Alpha2 code in {filename.resolve()}")
        
with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    print(gdf[["NAME_EN", "crypto_export", "crypto_import"]])

no_geometry: pd.DataFrame
no_geometry = gdf[["NAME_EN", "crypto_export", "crypto_import"]]

csv_path = OUTPUT_DIR / "crypto_data.csv"

if csv_path.exists():
    old = pd.read_csv(OUTPUT_DIR / "crypto_data.csv", index_col=0)

else:
    old = None

if USE_DUMMY_DATA or (old is None) or (old.values != no_geometry.values).any():

    if not USE_DUMMY_DATA:
        print("crypto information changed, updating the map...")
        no_geometry.to_csv(OUTPUT_DIR / "crypto_data.csv")

    else:
        print("generating map with random data...")

    for inex in ["Export", "Import"]:

        # generate interactive leaflet map
        m = gdf.explore("crypto_export" if inex == "Export" else "crypto_import",
            cmap="OrRd",
            #cmap=["white", "green", "yellow", "red"],
            categorical=True,
            tiles=None,
            categories=["unknown", "relaxed", "medium", "strict"],
            legend_kwds={
                "caption": f"Crypto {inex} Regulations"
            }, style_kwds={
                "stroke": True,
                "color": "black",
                "weight": 1,
                "fillOpacity": 0.7
            }, tooltip_kwds={
                "aliases": ["Country", "Alpha2 ISO Code", "Crypto Export Regulations", "Crypto Import Regulations"]
            }
        )

        if USE_DUMMY_DATA:
            m.save(OUTPUT_DIR / "dummy.html")

        else:
            # rename old map with timestamp
            filename = OUTPUT_DIR / f"{inex.lower()}.html"

            if filename.exists():
                os.rename(filename, OUTPUT_DIR / f"{inex.lower()}_statusuntil_{timestamp}.html")
            
            m.save(filename)

    print("done.")

else:
    print("crypto information unchanged, skipping updating the map")