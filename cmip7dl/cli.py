from intake_esgf import ESGFCatalog
from intake_esgf.exceptions import NoSearchResults

from typer import Typer

app = Typer()

VARIABLES = ("tas", "tasmin", "tasmax", "pr", "gpp", "npp")
EXPERIMENTS = (
    "historical",
    "esm-hist",
    "scen7-h",
    "scen7-hl",
    "scen7-m",
    "scen7-ml",
    "scen7-l",
    "scen7-vl",
    "esm-scen7-h",
    "esm-scen7-hl",
    "esm-scen7-m",
    "esm-scen7-ml",
    "esm-scen7-l",
    "esm-scen7-vl",
)


@app.command()
def main():
    cat = ESGFCatalog()

    res = cat.search(project="CMIP7", experiment_id="historical", variable_id="tas")
    source_ids = res.df["source_id"].unique().tolist()

    for var in VARIABLES:
        for exp in EXPERIMENTS:
            try:
                result = cat.search(
                    project="CMIP7",
                    frequency="mon",
                    variable_id=var,
                    experiment_id=exp,
                )
                print(result)
                raise SystemExit()
            except NoSearchResults:
                print(f"No results found for {var} {exp}")
                continue


if __name__ == "__main__":
    app()
