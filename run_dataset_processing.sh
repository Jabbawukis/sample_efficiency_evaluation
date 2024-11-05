#!/bin/bash

# Configuration
NUM_SLICES=4
DATASET_PATH="PatrickHaller/pile-10M-words"
DATASET_NAME=""
BEAR_DATA_PATH="BEAR"
REL_INFO_OUTPUT_DIR="output"
MATCHER_TYPE="simple"
ENTITY_LINKER_MODEL="en_core_web_trf"
SAVE_FILE_CONTENT="True"          # Pass as string
READ_EXISTING_INDEX="False"       # Pass as string
REQUIRE_GPU="False"               # Pass as string
GPU_IDS=(0 1 2 3)

# Create output directory if it doesn't exist
mkdir -p "$REL_INFO_OUTPUT_DIR"

# Calculate dataset slice range and launch processing scripts
DATASET_SIZE=$(python -c "import datasets; print(len(datasets.load_dataset('${DATASET_PATH}', '${DATASET_NAME}', split='train')))")

SLICE_SIZE=$((DATASET_SIZE / NUM_SLICES))

# Loop through each slice and assign a Python processing job
for (( i=0; i<NUM_SLICES; i++ )); do
    START_IDX=$((i * SLICE_SIZE))
    END_IDX=$((START_IDX + SLICE_SIZE))
    GPU_ID=${GPU_IDS[i]}
    FILE_INDEX_DIR=".index_dir_$((i + 1))"   # Unique index directory per slice

    # Handle last slice to cover any remaining samples
    if [ $i -eq $((NUM_SLICES - 1)) ]; then
        END_IDX=$DATASET_SIZE
    fi

    # Ensure index directory exists
    mkdir -p "$FILE_INDEX_DIR"

    # Run the slice processor in the background with the specified GPU
    CUDA_VISIBLE_DEVICES=$GPU_ID python3 slice_processor.py \
        --start_idx "$START_IDX" \
        --end_idx "$END_IDX" \
        --dataset_path "$DATASET_PATH" \
        --dataset_name "$DATASET_NAME" \
        --bear_data_path "$BEAR_DATA_PATH" \
        --rel_info_output_dir "$REL_INFO_OUTPUT_DIR" \
        --matcher_type "$MATCHER_TYPE" \
        --entity_linker_model "$ENTITY_LINKER_MODEL" \
        --gpu_id "$GPU_ID" \
        --slice_num $((i + 1)) \
        --file_index_dir "$FILE_INDEX_DIR" \
        --save_file_content "$SAVE_FILE_CONTENT" \
        --read_existing_index "$READ_EXISTING_INDEX" \
        --require_gpu "$REQUIRE_GPU" &

done

# Wait for all background processes to finish
wait
echo "All slices processed."
