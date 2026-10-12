import json
import os
import sys

import pandas

from database import Session
from models import Event, Timing

if __name__ == "__main__":
    input_file = os.path.join("data", "filtered", "evenements-publics-openagenda.csv")

    if not os.path.exists(input_file):
        print(f"Input file {input_file} does not exist. Please run filter_data.py first.")
        sys.exit(1)

    df = pandas.read_csv(input_file, low_memory=False)
    df = df.astype(object).where(df.notna(), None)

    with Session.begin() as session:
        for _, row in df.iterrows():
            event = Event(
                uid=row["uid"],
                canonicalurl=row["canonicalurl"],
                title_fr=row["title_fr"],
                description_fr=row["description_fr"],
                longdescription_fr=row["longdescription_fr"],
                keywords_fr=row["keywords_fr"],
                conditions_fr=row["conditions_fr"],
                location_name=row["location_name"],
                location_address=row["location_address"],
                location_city=row["location_city"],
                location_department=row["location_department"],
                location_region=row["location_region"],
                location_coordinates=row["location_coordinates"],
                age_min=row.get("age_min"),
                age_max=row.get("age_max"),
                accessibility=row.get("accessibility"),
                attendancemode=row.get("attendancemode")
            )
            session.add(event)

            timings_list = json.loads(row["timings"])
            for timing in timings_list:
                timing_entry = Timing(
                    event_uid=row["uid"],
                    begin=timing["begin"],
                    end=timing["end"]
                )
                session.add(timing_entry)

