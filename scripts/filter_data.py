import datetime
import json
import os
import sys

import bs4
import pandas


def check_timings_order(timings_str):
    try:
        timings_list = json.loads(timings_str)
        return timings_list and all(datetime.datetime.fromisoformat(timings_dict["begin"]) <= datetime.datetime.fromisoformat(timings_dict["end"]) for timings_dict in timings_list)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return False

def simplify_attendance_mode(attendance_mode):
    try:
        attendance_mode_dict = json.loads(attendance_mode)
        if "id" in attendance_mode_dict:
            return attendance_mode_dict["id"]
        else:
            return 1
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return 1

if __name__ == "__main__":
    input_filepath = os.path.join("data", "raw", "evenements-publics-openagenda.csv")
    output_filepath = os.path.join("data", "filtered", "evenements-publics-openagenda.csv")

    if not os.path.exists(input_filepath):
        print(f"Input file {input_filepath} does not exist. Please run download_data.py first.")
        sys.exit(1)

    df = pandas.read_csv(input_filepath, low_memory=False)

    df = df[df["country_fr"] == "France (Métropole)"]
    df = df[df["description_fr"].notnull()]
    df = df[df["title_fr"].notnull()]
    #clean long_description_fr column by removing HTML tags
    df["longdescription_fr"] = df["longdescription_fr"].apply(lambda x: bs4.BeautifulSoup(x, "html.parser").get_text() if pandas.notnull(x) else "")
    df = df.drop_duplicates(subset=["title_fr", "firstdate_begin", "location_name", "description_fr", "longdescription_fr"])
    df = df[df["timings"].apply(lambda x: check_timings_order(x))]
    df["attendancemode"] = df["attendancemode"].apply(lambda x: simplify_attendance_mode(x))

    columns_to_keep = [
        "uid",
        "canonicalurl",
        "title_fr",
        "description_fr",
        "longdescription_fr",
        "keywords_fr",
        "conditions_fr",
        "timings",
        "location_name",
        "location_address",
        "location_city",
        "location_department",
        "location_region",
        "location_coordinates",
        "age_min",
        "age_max",
        "accessibility",
        "attendancemode"
    ]

    df = df[columns_to_keep]

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False)