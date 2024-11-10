import pandas as pd
import os
import json

class CSVHandler:
    def __init__(self):
        self.data_file = None
        self.data_df = None

    def load_data_from_csv(self):
        
        if self.data_file and os.path.exists(self.data_file):
            # Create backup with date
            from datetime import datetime
            backup_file = f"{self.data_file}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
            import shutil
            shutil.copy2(self.data_file, backup_file)
            
            self.data_df = pd.read_csv(self.data_file, index_col="trace_path")
            if "deleted" not in self.data_df.columns:
                self.data_df['deleted'] = False

            df_dtypes = self.data_df.dtypes
            if "p_wave_frame" in df_dtypes and df_dtypes["p_wave_frame"] == "float64":
                # Convert existing float values to JSON strings
                self.data_df["p_wave_frame"] = self.data_df["p_wave_frame"].apply(
                    lambda x: json.dumps([x]) if pd.notnull(x) else x
                )
        else:
            self.data_df = pd.DataFrame(
                columns=["trace_path", "p_wave_frame", "needs_review", "deleted"]
            )
            self.data_df.set_index("trace_path", inplace=True)
        return self.data_df

    def save_data_to_csv(self):
        if self.data_file:
            self.data_df.to_csv(self.data_file)
            print("saving csv")
            print(self.data_df)
        else:
            print("Error: data_file path not set")

    def set_data_file(self, folder):
        self.data_file = os.path.join(folder, "data.csv")
        return self.load_data_from_csv()

    def update_p_wave_time(self, group_key, p_wave_frame):
        p_json = json.dumps(p_wave_frame) 
        self.data_df.loc[group_key, "p_wave_frame"] = p_json 
        self.save_data_to_csv()

    def toggle_review_status(self, group_key):
        current_status = self.data_df.loc[group_key, "needs_review"]
        self.data_df.loc[group_key, "needs_review"] = not current_status
        self.save_data_to_csv()
        return not current_status

    def mark_as_deleted(self, group_key):
        self.data_df.loc[group_key, "deleted"] = True
        self.save_data_to_csv() 