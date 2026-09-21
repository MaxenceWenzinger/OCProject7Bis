import datetime
import io
import os

import pandas
import requests

#api doc: https://help.opendatasoft.com/apis/ods-explore-v2/#tag/Catalog/operation/exportDatasets
#hidden limit on exports/csv of 128700 rows per request

if __name__ == "__main__":
    url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/evenements-publics-openagenda/exports/csv?quote_all=true"
    not_first_iteration = True
    date_start = datetime.date(2016, 1, 1)
    date_chunk_end = date_start + datetime.timedelta(days=90)
    date_end = datetime.date(2028, 1, 1)
    all_df = []
    filepath = os.path.join("data", "raw", "evenements-publics-openagenda.csv")
    if os.path.exists(filepath):
        os.remove(filepath)

    while date_start < date_end:
        params = {"where": f'firstdate_begin >= "{date_start.isoformat()}" AND firstdate_begin < "{date_chunk_end.isoformat()}"'}
        print(f"Downloading data chunk from {date_start} to {date_chunk_end}...")
        response = requests.get(url, params=params)
        if response.status_code == 200:
            all_df.append(pandas.read_csv(io.StringIO(response.text), sep=";", quotechar='"', encoding="utf-8", dtype=str))
            print(f"Downloaded {len(all_df[-1])} rows. Total rows so far: {sum(len(df) for df in all_df)}")
        else:
            print(f"Failed to download data chunk. Status code: {response.status_code}")
            print(f"Response content: {response.content}")
            break
        date_start = date_chunk_end
        date_chunk_end = date_start + datetime.timedelta(days=90)

    concatenated_df = pandas.concat(all_df, ignore_index=True)
    with open(filepath, "w", encoding="utf-8") as f:
        concatenated_df.to_csv(f, index=False)

    