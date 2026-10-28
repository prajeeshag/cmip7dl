from intake_esgf import ESGFCatalog
from intake_esgf import conf
from intake_esgf.exceptions import NoSearchResults, DatasetLoadError
from typer import Typer
from pathlib import Path
import pandas as pd


CACHE_DIR = Path.home() / "CMIP7_DATA"

AVAILABLE_DATA_FILE = CACHE_DIR / "available_data.csv"

NEW_DATA_FILE = CACHE_DIR / "new_data.csv"

conf.set(local_cache=[str(CACHE_DIR)])


app = Typer()

VARIABLES = ("pr", "tas", "gpp", "npp")
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
def main(exclude_sources: list[str] = [], list_sources: bool = False):
    cat = ESGFCatalog()

    if AVAILABLE_DATA_FILE.exists():
        available_df = pd.read_csv(AVAILABLE_DATA_FILE)
    else:
        available_df = pd.DataFrame()

    res = cat.search(project="CMIP7", experiment_id="historical", variable_id="tas")
    source_ids = res.df["source_id"].unique().tolist()

    if list_sources:
        print("Available source IDs:")
        for source_id in source_ids:
            print(source_id)
        return

    project = "CMIP7"
    frequency = "mon"
    region = "glb"

    data_list = []
    for var in VARIABLES:
        for exp in EXPERIMENTS:
            for source_id in source_ids:
                if source_id in exclude_sources:
                    print(f"Skipping {source_id}")
                    continue

                try:
                    result = cat.search(
                        project=project,
                        frequency=frequency,
                        region=region,
                        variable_id=var,
                        experiment_id=exp,
                        source_id=source_id,
                    )

                    print(result)

                    try:
                        path_dict = result.to_path_dict(quiet=True)
                    except DatasetLoadError as e:
                        print(f"Failed to get paths for {var} {exp}: {e}")
                        continue

                    for branding, paths in path_dict.items():
                        directory, filenames = organize_paths(paths)
                        print(directory, filenames)
                        filenames_str = ",".join(filenames)
                        data_list.append(
                            {
                                "project": project,
                                "frequency": frequency,
                                "region": region,
                                "variable_id": var,
                                "experiment_id": exp,
                                "source_id": source_id,
                                "branding_suffix": branding,
                                "directory": directory,
                                "filenames": filenames_str,
                            }
                        )

                except NoSearchResults:
                    print(f"No results found for {var} {exp}")
                    continue

    for f in Path(CACHE_DIR).rglob("*"):
        if f.is_file() and ".nc" in f.name and not f.name.endswith(".nc"):
            print(f"Deleting: {f}")
            f.unlink()

    current_df = pd.DataFrame(data_list)
    available_df, new_df = merge_data(current_df, available_df)
    available_df.to_csv(AVAILABLE_DATA_FILE, index=False)
    new_df.to_csv(NEW_DATA_FILE, index=False)
    print(f"New records/files: {len(new_df)}")


def organize_paths(paths):
    directory = None
    filenames = []
    for path in sorted(Path(p).relative_to(CACHE_DIR) for p in paths):
        if directory is None:
            directory = str(path.parent)
        elif directory != str(path.parent):
            raise ValueError("Paths are not in the same directory")
        filenames.append(path.name)
    filenames = sorted(filenames)
    return directory, filenames


def merge_data(current_df, available_df):
    keys = [
        "project",
        "frequency",
        "region",
        "variable_id",
        "experiment_id",
        "source_id",
        "branding_suffix",
        "directory",
    ]

    if available_df.empty:
        return current_df.copy(), current_df.copy()

    available_df = available_df.copy()
    new_rows = []

    for _, row in current_df.iterrows():
        mask = pd.Series(True, index=available_df.index)

        for key in keys:
            mask &= available_df[key] == row[key]

        if mask.any():
            idx = available_df.index[mask][0]

            old_files = set(available_df.at[idx, "filenames"].split(","))
            current_files = set(row["filenames"].split(","))

            added_files = sorted(current_files - old_files)

            if added_files:
                available_df.at[idx, "filenames"] = ",".join(
                    sorted(old_files | current_files)
                )

                new_row = row.copy()
                new_row["filenames"] = ",".join(added_files)
                new_rows.append(new_row)

        else:
            available_df = pd.concat(
                [available_df, row.to_frame().T],
                ignore_index=True,
            )
            new_rows.append(row)

    new_df = pd.DataFrame(new_rows, columns=current_df.columns)

    return available_df, new_df


if __name__ == "__main__":
    app()
