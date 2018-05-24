import json
import os
import time

import sox
from tqdm import tqdm

os.chdir('..')

splice_settings_file = os.path.join('settings', 'data_settings.json')

settings = json.load(open(splice_settings_file))
input_data_suffix = settings['input_data_suffix']
input_dir_name_base = settings['input_dir_name_base']
input_dir_name_dirs = settings['input_dir_name_dirs']
splice_duration = settings['splice_duration']
try:
    start_offset = int(settings['start_time'])
    end_offset = int(settings['end_time'])
except ValueError:
    print("{} malformed, enter integer start and end offsets. Using 0 and -0 for now.".format(splice_settings_file))
    start_offset = 0
    end_offset = 0
downsample_rate = settings['downsample_rate']
output_dir_name_base = settings['output_dir_name_base']

output_dir_name = os.path.join(output_dir_name_base, 'splices')
ds_output_dir_name = os.path.join(output_dir_name_base, 'downsampled_splices')
output_data_info_file_name = os.path.join(output_dir_name_base, 'data_info.json')

if not os.path.exists(output_dir_name):
    os.makedirs(output_dir_name)
if not os.path.exists(ds_output_dir_name):
    os.makedirs(ds_output_dir_name)

print('Will send spliced audio to {}'.format(output_dir_name))
print('Will send spliced and downsampled audio to {}'.format(ds_output_dir_name))
print('Will write data info to {}'.format(output_data_info_file_name))

processed_data_info = settings
processed_data_info['original_bitrate'] = None

for input_dir_name_dir in input_dir_name_dirs:
    input_dir_name = os.path.join(input_dir_name_base, input_dir_name_dir)

    time.sleep(0.5)
    if not os.path.exists(input_dir_name) or os.path.isfile(input_dir_name):
        print("Path '{}' does not exist. Skipping...".format(input_dir_name))
        continue
    print("Processing path '{}'.".format(input_dir_name))
    time.sleep(0.5)

    # Loop over all files within the input directory
    for filename in tqdm(os.listdir(input_dir_name)):
        input_filename = os.path.join(input_dir_name, filename)
        if not os.path.isfile(input_filename) or input_data_suffix not in filename:
            continue
        filename_base = os.path.splitext(filename)[0]

        # This is the total audio track duration minus the start and end times
        duration = sox.file_info.duration(input_filename) - start_offset + end_offset
        if processed_data_info['original_bitrate'] is None:
            processed_data_info['original_bitrate'] = sox.file_info.bitrate(input_filename)
            if 'kb' in processed_data_info['sampling_rate_units']:
                processed_data_info['original_bitrate'] *= 1000


        def filename_template(original_filename, begin, end):
            return "{}_{}-{}.wav".format(original_filename, str(int(begin)).zfill(2), str(int(end)).zfill(2))


        splice_start_time = start_offset
        file_end_time = start_offset + duration
        SPLICES_SHOULD_BE_EQUAL_IN_LENGTH = True
        equal_length_check = splice_duration if SPLICES_SHOULD_BE_EQUAL_IN_LENGTH else 0
        while splice_start_time + equal_length_check < file_end_time:
            splice = sox.Transformer()
            splice_and_downsample = sox.Transformer()

            begin = start_offset + splice_start_time
            end = min(file_end_time, splice_start_time + splice_duration)

            output_filename = filename_template(filename_base, begin, end)
            output_filename = os.path.join(output_dir_name, output_filename)
            ds_output_filename = filename_template(filename_base, begin, end)
            ds_output_filename = os.path.join(ds_output_dir_name, ds_output_filename)

            splice.trim(begin, end)
            splice.build(input_filename, output_filename)

            splice_and_downsample.trim(begin, end)
            splice_and_downsample.convert(samplerate=downsample_rate)
            splice_and_downsample.build(input_filename, ds_output_filename)

            splice_start_time = end

with open(output_data_info_file_name, 'w') as outfile:
    json.dump(processed_data_info, outfile)
