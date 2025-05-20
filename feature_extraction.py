import os
import mne
import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis
from mne.time_frequency import psd_array_welch

# Frequency bands
freq_bands = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta': (13, 30),
    'gamma': (30, 50)
}

# Function to extract features from one .set file
def extract_features_from_file(file_path):
    try:
        raw = mne.io.read_raw_eeglab(file_path, preload=True)
        raw.filter(0.5, 50., fir_design='firwin')
        raw.set_eeg_reference('average', projection=True)

        events = mne.make_fixed_length_events(raw, duration=2.0, overlap=1.0)
        epochs = mne.Epochs(raw, events, tmin=0, tmax=2.0, baseline=None, preload=True)

        all_features = []
        for epoch in epochs:
            data = epoch  # shape: (n_channels, n_times)

            stats = {
                'mean': np.mean(data, axis=1),
                'std': np.std(data, axis=1),
                'skew': skew(data, axis=1),
                'kurtosis': kurtosis(data, axis=1)
            }

            psd, freqs = psd_array_welch(data, sfreq=raw.info['sfreq'], fmin=0.5, fmax=50.0)
            for band, (fmin, fmax) in freq_bands.items():
                band_power = psd[:, (freqs >= fmin) & (freqs <= fmax)].mean(axis=1)
                stats[band] = band_power

            flat = np.concatenate([stats[k] for k in ['mean', 'std', 'skew', 'kurtosis', 'delta', 'theta', 'alpha', 'beta', 'gamma']])
            all_features.append(flat)

        # Build DataFrame
        df = pd.DataFrame(all_features)
        df['subject'] = file_path.split("sub-")[1][:3]
        df['session'] = file_path.split("ses-")[1][:2]
        return df
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return pd.DataFrame()

# Directory where .set files are stored
set_folder = "C:/Users/naran/Downloads/set files" 

# Output CSV path
output_csv = "eeg_features_all.csv"

# Collect all .set files
all_set_files = [os.path.join(set_folder, f) for f in os.listdir(set_folder) if f.endswith(".set")]

# Process each file
full_df = pd.DataFrame()
for file_path in all_set_files:
    print(f"Processing {file_path}")
    df = extract_features_from_file(file_path)
    if not df.empty:
        full_df = pd.concat([full_df, df], ignore_index=True)

# Save to CSV
full_df.to_csv(output_csv, index=False)
print(f"\n✅ Feature extraction complete. Saved to {output_csv}")
