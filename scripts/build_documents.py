import os
import sys

import pandas

if __name__ == "__main__":
    input_filepath = os.path.join("data", "filtered", "evenements-publics-openagenda.csv")
    output_filepath = os.path.join("data", "documents", "evenements-publics-openagenda.json")

    if not os.path.exists(input_filepath):
        print(f"Input file {input_filepath} does not exist. Please run filter_data.py first.")
        sys.exit(1)

    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as output_file:
        output_file.write("{\n")

        df = pandas.read_csv(input_filepath)
        for index, row in df.iterrows():
            address = f", {row['location_address']}" if pandas.notnull(row["location_address"]) else ""
            city = f", {row['location_city']}" if pandas.notnull(row["location_city"]) else ""
            department = f", {row['location_department']}" if pandas.notnull(row["location_department"]) else ""
            region = f", {row['location_region']}" if pandas.notnull(row["location_region"]) else ""

            mots_clefs = f"\n{row['keywords_fr']}" if pandas.notnull(row["keywords_fr"]) else ""
            lieu = f"\n{row['location_name']}{address}{city}{department}{region}"
            longdescription = f"\n{row['longdescription_fr']}" if pandas.notnull(row["longdescription_fr"]) else ""

            content = f"{row['title_fr']}{mots_clefs}{lieu}\n{row['description_fr']}{longdescription}"
            content = content.replace('"', '\\"').replace("\n", "\\n")
            output_file.write(f'"{row["uid"]}": "{content}"{",\n" if index < len(df) - 1 else "\n"}')

        output_file.write("\n}")