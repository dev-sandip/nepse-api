from nepse import dump_to_std_file_descriptor, show_status

dump_to_std_file_descriptor(
    output_destination=None, output_content=show_status(), convert_to_csv=False
)